"""Bot 客户端封装模块。

基于 Telethon 的 Bot 客户端，用于用户交互和通知。
"""

import asyncio
import logging
import os
from typing import Any, List, Optional, Union

from telethon import Button, TelegramClient, events
from telethon.errors import (
    ChatAdminRequiredError,
    FloodWaitError as TelethonFloodWaitError,
    MessageNotModifiedError,
    UserBannedInChannelError,
)
from telethon.tl.types import Message

from src.core.config import Config
from src.core.constants import DEFAULT_SESSION_DIR
from src.core.event_bus import EventBus
from src.core.exceptions import ClientError, FloodWaitError
from src.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class BotClient:
    """Telethon Bot 客户端封装，提供速率限制和错误处理。"""

    def __init__(
        self, config: Config, rate_limiter: RateLimiter, event_bus: EventBus
    ) -> None:
        """初始化 Bot 客户端。"""
        self._config = config
        self._rate_limiter = rate_limiter
        self._event_bus = event_bus
        self._client: Optional[TelegramClient] = None

    async def start(self) -> None:
        """启动 Bot 客户端，使用 bot_token 认证。

        Raises:
            ClientError: 连接或认证失败时抛出
        """
        session_dir = self._config.telegram.session_dir or DEFAULT_SESSION_DIR
        session_path = os.path.join(session_dir, self._config.telegram.bot_session)
        self._client = TelegramClient(
            session_path,
            self._config.telegram.api_id,
            self._config.telegram.api_hash,
        )
        try:
            await self._client.start(bot_token=self._config.telegram.bot_token)
        except Exception as e:
            raise ClientError(f"Bot 客户端启动失败: {e}") from e
        me = await self._client.get_me()
        logger.info("Bot 已启动，@%s (ID: %s)", me.username, me.id)
        await self._event_bus.emit("bot_started", bot_id=me.id)

    async def stop(self) -> None:
        """断开连接并释放资源。"""
        if self._client and self._client.is_connected():
            await self._client.disconnect()
            logger.info("Bot 客户端已断开连接")

    async def send_message(
        self, chat_id: Union[int, str], text: str, **kwargs: Any
    ) -> Message:
        """发送消息（Bot 风险低，但仍限速）。

        Args:
            chat_id: 目标聊天 ID 或用户名
            text: 消息文本
            **kwargs: 传递给 Telethon 的额外参数
        """
        cid = chat_id if isinstance(chat_id, int) else None
        await self._rate_limiter.acquire("message", chat_id=cid)
        try:
            result = await self._client.send_message(chat_id, text, **kwargs)
            self._rate_limiter.reset_flood_counter()
            return result
        except TelethonFloodWaitError as e:
            await self._handle_flood_wait(e)
            return await self._client.send_message(chat_id, text, **kwargs)
        except ChatAdminRequiredError:
            raise ClientError(f"Bot 在聊天 {chat_id} 中缺少管理员权限")
        except UserBannedInChannelError:
            raise ClientError(f"Bot 在频道 {chat_id} 中被封禁")

    async def reply(
        self, event: events.NewMessage.Event, text: str, **kwargs: Any
    ) -> Message:
        """回复收到的消息。"""
        await self._rate_limiter.acquire("message")
        try:
            return await event.reply(text, **kwargs)
        except TelethonFloodWaitError as e:
            await self._handle_flood_wait(e)
            return await event.reply(text, **kwargs)

    async def send_inline_keyboard(
        self, chat_id: Union[int, str], text: str, buttons: List[List[Button]]
    ) -> Message:
        """发送带 InlineKeyboard 的消息。

        Args:
            chat_id: 目标聊天 ID
            text: 消息文本
            buttons: 按钮矩阵，每个子列表代表一行按钮
        """
        cid = chat_id if isinstance(chat_id, int) else None
        await self._rate_limiter.acquire("message", chat_id=cid)
        try:
            return await self._client.send_message(chat_id, text, buttons=buttons)
        except TelethonFloodWaitError as e:
            await self._handle_flood_wait(e)
            return await self._client.send_message(chat_id, text, buttons=buttons)

    async def edit_message(
        self, chat_id: Union[int, str], msg_id: int, text: str, **kwargs: Any
    ) -> Message:
        """编辑消息。

        Raises:
            ClientError: 消息内容未变更时抛出
        """
        await self._rate_limiter.acquire("message")
        try:
            return await self._client.edit_message(chat_id, msg_id, text, **kwargs)
        except MessageNotModifiedError:
            logger.debug("消息 %d 内容未变更，跳过编辑", msg_id)
            raise ClientError(f"消息 {msg_id} 内容未变更")
        except TelethonFloodWaitError as e:
            await self._handle_flood_wait(e)
            return await self._client.edit_message(chat_id, msg_id, text, **kwargs)

    async def answer_callback(
        self, event: events.CallbackQuery.Event, text: Optional[str] = None
    ) -> None:
        """响应回调查询。"""
        try:
            await event.answer(text)
        except Exception as e:
            logger.warning("响应回调查询失败: %s", e)

    @property
    def client(self) -> TelegramClient:
        """获取底层 Telethon 客户端（用于注册事件处理器）。"""
        if self._client is None:
            raise ClientError("Bot 客户端尚未初始化，请先调用 start()")
        return self._client

    async def _handle_flood_wait(self, e: TelethonFloodWaitError) -> None:
        """处理 Telegram 限流，委托给 RateLimiter 统一管理连续触发暂停机制。"""
        wait_seconds: int = e.seconds
        logger.warning("Bot 触发限流，委托 RateLimiter 处理 %d 秒", wait_seconds)
        await self._event_bus.emit("flood_wait", seconds=wait_seconds, client="bot")
        if wait_seconds > 60:
            raise FloodWaitError(wait_seconds, f"限流等待时间过长: {wait_seconds}秒")
        await self._rate_limiter.handle_flood_wait(wait_seconds)
