"""Userbot 客户端封装模块。

基于 Telethon 的 Userbot 客户端，用于执行需要用户权限的操作。
"""

import asyncio
import logging
import os
from typing import Any, List, Optional, Union

from telethon import TelegramClient
from telethon.errors import (
    ChatAdminRequiredError,
    FloodWaitError as TelethonFloodWaitError,
    UserBannedInChannelError,
)
from telethon.tl.types import Message

from src.core.config import Config
from src.core.constants import DEFAULT_SESSION_DIR
from src.core.event_bus import EventBus
from src.core.exceptions import ClientError, FloodWaitError
from src.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class UserbotClient:
    """Telethon Userbot 客户端封装，提供速率限制和错误处理。"""

    def __init__(
        self, config: Config, rate_limiter: RateLimiter, event_bus: EventBus
    ) -> None:
        """初始化 Userbot 客户端。"""
        self._config = config
        self._rate_limiter = rate_limiter
        self._event_bus = event_bus
        self._client: Optional[TelegramClient] = None

    async def start(self) -> None:
        """启动 Userbot 客户端，使用已有 session。

        Raises:
            ClientError: 未授权或连接失败时抛出
        """
        session_dir = self._config.telegram.session_dir or DEFAULT_SESSION_DIR
        session_path = os.path.join(session_dir, self._config.telegram.userbot_session)
        self._client = TelegramClient(
            session_path,
            self._config.telegram.api_id,
            self._config.telegram.api_hash,
        )
        await self._client.connect()
        if not await self._client.is_user_authorized():
            await self._client.disconnect()
            raise ClientError("Userbot 未授权，请先运行 setup_session.py 完成登录")
        me = await self._client.get_me()
        logger.info("Userbot 已启动，账号: %s (ID: %s)", me.first_name, me.id)
        await self._event_bus.emit("userbot_started", user_id=me.id)

    async def stop(self) -> None:
        """断开连接并释放资源。"""
        if self._client and self._client.is_connected():
            await self._client.disconnect()
            logger.info("Userbot 客户端已断开连接")

    async def send_message(
        self, chat_id: Union[int, str], text: str, **kwargs: Any
    ) -> Message:
        """发送消息（经过速率限制）。

        Args:
            chat_id: 目标聊天 ID 或用户名
            text: 消息文本
            **kwargs: 传递给 Telethon 的额外参数
        """
        cid = chat_id if isinstance(chat_id, int) else None
        await self._rate_limiter.acquire("message", chat_id=cid)
        try:
            return await self._client.send_message(chat_id, text, **kwargs)
        except TelethonFloodWaitError as e:
            await self._handle_flood_wait(e)
            return await self._client.send_message(chat_id, text, **kwargs)
        except ChatAdminRequiredError:
            raise ClientError(f"在聊天 {chat_id} 中缺少管理员权限")
        except UserBannedInChannelError:
            raise ClientError(f"用户在频道 {chat_id} 中被封禁")

    async def forward_message(
        self, from_chat: Union[int, str], msg_id: int, to_chat: Union[int, str]
    ) -> Message:
        """转发消息。

        Args:
            from_chat: 源聊天 ID
            msg_id: 消息 ID
            to_chat: 目标聊天 ID
        """
        await self._rate_limiter.acquire("message")
        try:
            return await self._client.forward_messages(to_chat, msg_id, from_chat)
        except TelethonFloodWaitError as e:
            await self._handle_flood_wait(e)
            return await self._client.forward_messages(to_chat, msg_id, from_chat)

    async def get_messages(
        self, chat_id: Union[int, str], limit: int = 100, **kwargs: Any
    ) -> List[Message]:
        """获取消息历史。

        Args:
            chat_id: 聊天 ID
            limit: 获取数量上限
        """
        cid = chat_id if isinstance(chat_id, int) else None
        await self._rate_limiter.acquire("message", chat_id=cid)
        return await self._client.get_messages(chat_id, limit=limit, **kwargs)

    async def get_dialogs(self, limit: Optional[int] = None) -> list:
        """获取对话列表。"""
        await self._rate_limiter.acquire("message")
        return await self._client.get_dialogs(limit=limit)

    async def get_participants(
        self, chat_id: Union[int, str], limit: Optional[int] = None
    ) -> list:
        """获取群成员列表。

        Raises:
            ClientError: 缺少管理员权限时抛出
        """
        await self._rate_limiter.acquire("message")
        try:
            params: dict[str, Any] = {}
            if limit is not None:
                params["limit"] = limit
            return await self._client.get_participants(chat_id, **params)
        except ChatAdminRequiredError:
            raise ClientError(f"获取 {chat_id} 的成员列表需要管理员权限")

    @property
    def client(self) -> TelegramClient:
        """获取底层 Telethon 客户端（用于注册事件处理器）。"""
        if self._client is None:
            raise ClientError("Userbot 客户端尚未初始化，请先调用 start()")
        return self._client

    async def _handle_flood_wait(self, e: TelethonFloodWaitError) -> None:
        """处理 Telegram 限流，委托给 RateLimiter 统一管理连续触发暂停机制。"""
        wait_seconds: int = e.seconds
        logger.warning("Userbot 触发限流，委托 RateLimiter 处理 %d 秒", wait_seconds)
        await self._event_bus.emit("flood_wait", seconds=wait_seconds, client="userbot")
        if wait_seconds > 60:
            raise FloodWaitError(wait_seconds, f"限流等待时间过长: {wait_seconds}秒")
        # 委托 RateLimiter 处理（更新连续计数器 + 全局暂停逻辑）
        await self._rate_limiter.handle_flood_wait(wait_seconds)
