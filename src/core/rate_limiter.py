"""
TG Manager 速率限制器模块。

实现防封禁策略，包括全局/单聊天限速、每日配额、随机抖动和 FloodWait 处理。
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import defaultdict
from typing import Any

from .constants import (
    DEFAULT_ADD_MEMBER_INTERVAL,
    DEFAULT_ADD_MEMBER_PER_DAY,
    DEFAULT_DOWNLOAD_CONCURRENT,
    DEFAULT_FLOOD_WAIT_MULTIPLIER,
    DEFAULT_FLOOD_WAIT_PAUSE_DURATION,
    DEFAULT_FLOOD_WAIT_PAUSE_THRESHOLD,
    DEFAULT_GLOBAL_PER_MINUTE,
    DEFAULT_JITTER_MAX,
    DEFAULT_JITTER_MIN,
    DEFAULT_JOIN_PER_DAY,
    DEFAULT_PER_CHAT_INTERVAL,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器，通过多维度限速实现 Telegram 防封禁策略。"""

    def __init__(self, config: Any = None) -> None:
        """初始化速率限制器。

        Args:
            config: 速率限制配置（dict 或 AttrDict），缺省时使用常量默认值。
        """
        cfg = dict(config) if config else {}
        # 从配置读取参数，回退到默认常量
        self._global_per_minute: int = cfg.get("global_per_minute", DEFAULT_GLOBAL_PER_MINUTE)
        self._per_chat_interval: float = cfg.get("per_chat_interval", DEFAULT_PER_CHAT_INTERVAL)
        self._join_per_day: int = cfg.get("join_per_day", DEFAULT_JOIN_PER_DAY)
        self._add_member_per_day: int = cfg.get("add_member_per_day", DEFAULT_ADD_MEMBER_PER_DAY)
        self._add_member_interval: float = cfg.get("add_member_interval", DEFAULT_ADD_MEMBER_INTERVAL)
        self._flood_multiplier: float = cfg.get("flood_wait_multiplier", DEFAULT_FLOOD_WAIT_MULTIPLIER)
        self._flood_pause_threshold: int = cfg.get("flood_wait_pause_threshold", DEFAULT_FLOOD_WAIT_PAUSE_THRESHOLD)
        self._flood_pause_duration: int = cfg.get("flood_wait_pause_duration", DEFAULT_FLOOD_WAIT_PAUSE_DURATION)
        self._jitter_min: float = cfg.get("jitter_min", DEFAULT_JITTER_MIN)
        self._jitter_max: float = cfg.get("jitter_max", DEFAULT_JITTER_MAX)

        # 全局每分钟消息时间戳列表
        self._global_timestamps: list[float] = []
        # 每个聊天的最后发送时间
        self._chat_last_send: dict[int, float] = defaultdict(float)
        # 每日计数器：加入群组、添加成员
        self._daily_join_count: int = 0
        self._daily_add_count: int = 0
        self._daily_reset_date: str = self._today()
        # FloodWait 连续计数
        self._consecutive_floods: int = 0
        # 全局暂停截止时间
        self._pause_until: float = 0.0
        # 下载并发信号量
        self._download_semaphore = asyncio.Semaphore(
            cfg.get("download_concurrent", DEFAULT_DOWNLOAD_CONCURRENT)
        )
        # 线程安全锁
        self._lock = asyncio.Lock()

    @staticmethod
    def _today() -> str:
        """获取当前日期字符串，用于每日计数器重置。"""
        return time.strftime("%Y-%m-%d")

    def _reset_daily_if_needed(self) -> None:
        """检查日期变更，必要时重置每日计数器。"""
        today = self._today()
        if today != self._daily_reset_date:
            self._daily_join_count = 0
            self._daily_add_count = 0
            self._daily_reset_date = today
            logger.info("每日计数器已重置")

    def _add_jitter(self) -> float:
        """生成随机抖动延迟时间。

        Returns:
            随机抖动秒数。
        """
        return random.uniform(self._jitter_min, self._jitter_max)

    async def acquire(self, operation: str, chat_id: int | None = None) -> None:
        """获取操作许可，必要时等待直到满足限速条件。

        Args:
            operation: 操作类型，支持 "message"、"join_group"、"add_member"、"download"。
            chat_id: 聊天 ID，仅 "message" 操作使用。

        Raises:
            RateLimitError: 当每日配额耗尽时抛出（通过导入延迟避免循环引用）。
        """
        from .exceptions import RateLimitError

        # 下载操作使用信号量控制并发
        if operation == "download":
            await self._download_semaphore.acquire()
            await asyncio.sleep(self._add_jitter())
            return

        async with self._lock:
            self._reset_daily_if_needed()

            # 检查全局暂停
            now = time.monotonic()
            if now < self._pause_until:
                wait = self._pause_until - now
                logger.warning("全局暂停中，等待 %.1f 秒", wait)
                await asyncio.sleep(wait)

            if operation == "message":
                await self._acquire_message(chat_id)
            elif operation == "join_group":
                if self._daily_join_count >= self._join_per_day:
                    raise RateLimitError(f"每日加入群组已达上限: {self._join_per_day}")
                self._daily_join_count += 1
                await asyncio.sleep(self._add_jitter())
            elif operation == "add_member":
                if self._daily_add_count >= self._add_member_per_day:
                    raise RateLimitError(f"每日添加成员已达上限: {self._add_member_per_day}")
                self._daily_add_count += 1
                await asyncio.sleep(max(self._add_member_interval, self._add_jitter()))
            else:
                await asyncio.sleep(self._add_jitter())

    async def _acquire_message(self, chat_id: int | None) -> None:
        """处理消息类型的限速逻辑。

        Args:
            chat_id: 聊天 ID。
        """
        now = time.time()
        # 清理超过一分钟的时间戳
        self._global_timestamps = [ts for ts in self._global_timestamps if now - ts < 60]
        # 全局每分钟限速
        if len(self._global_timestamps) >= self._global_per_minute:
            wait = 60 - (now - self._global_timestamps[0]) + self._add_jitter()
            logger.info("全局消息限速，等待 %.1f 秒", wait)
            await asyncio.sleep(wait)
        # 单聊天间隔限速
        if chat_id is not None:
            elapsed = now - self._chat_last_send[chat_id]
            if elapsed < self._per_chat_interval:
                wait = self._per_chat_interval - elapsed + self._add_jitter()
                logger.debug("聊天 %d 限速，等待 %.1f 秒", chat_id, wait)
                await asyncio.sleep(wait)
            self._chat_last_send[chat_id] = time.time()
        self._global_timestamps.append(time.time())

    async def handle_flood_wait(self, seconds: int) -> None:
        """处理 Telegram FloodWait，按乘数放大等待时间。

        连续触发达到阈值时，暂停所有操作。

        Args:
            seconds: Telegram 要求的等待秒数。
        """
        async with self._lock:
            self._consecutive_floods += 1
            actual_wait = seconds * self._flood_multiplier + self._add_jitter()
            logger.warning(
                "FloodWait: 原始 %d 秒，实际等待 %.1f 秒（连续第 %d 次）",
                seconds, actual_wait, self._consecutive_floods,
            )
            if self._consecutive_floods >= self._flood_pause_threshold:
                self._pause_until = time.monotonic() + self._flood_pause_duration
                logger.error(
                    "连续 FloodWait 达 %d 次，全局暂停 %d 秒",
                    self._consecutive_floods, self._flood_pause_duration,
                )
                self._consecutive_floods = 0

        await asyncio.sleep(actual_wait)

    def release_download(self) -> None:
        """释放下载信号量，在下载完成后调用。"""
        self._download_semaphore.release()

    def reset_flood_counter(self) -> None:
        """重置连续 FloodWait 计数器，在操作成功后调用。"""
        self._consecutive_floods = 0
