"""双客户端协调器模块。

协调 Userbot 和 Bot 客户端，实现智能客户端选择。
Userbot 负责执行高权限操作，Bot 负责用户交互和通知。
"""

import logging
from typing import Any, Union

from telethon.tl.types import Message

from src.core.config import Config
from src.core.event_bus import EventBus
from src.core.exceptions import ClientError
from src.core.rate_limiter import RateLimiter

from .bot import BotClient
from .userbot import UserbotClient

logger = logging.getLogger(__name__)


class DualClient:
    """双客户端协调器 -- Userbot 负责执行，Bot 负责交互。

    根据操作类型和风险级别自动选择合适的客户端。
    """

    def __init__(
        self, config: Config, rate_limiter: RateLimiter, event_bus: EventBus
    ) -> None:
        """初始化双客户端协调器。

        Args:
            config: 全局配置对象
            rate_limiter: 速率限制器
            event_bus: 事件总线
        """
        self.userbot = UserbotClient(config, rate_limiter, event_bus)
        self.bot = BotClient(config, rate_limiter, event_bus)
        self._config = config
        self._event_bus = event_bus

    async def start(self) -> None:
        """启动双客户端。

        同时启动 Userbot 和 Bot 客户端。

        Raises:
            ClientError: 任一客户端启动失败时抛出
        """
        logger.info("正在启动双客户端...")

        try:
            await self.userbot.start()
        except ClientError:
            logger.error("Userbot 客户端启动失败")
            raise

        try:
            await self.bot.start()
        except ClientError:
            # Bot 启动失败时，先停止已启动的 Userbot
            logger.error("Bot 客户端启动失败，正在停止 Userbot...")
            await self.userbot.stop()
            raise

        logger.info("双客户端启动完成")
        await self._event_bus.emit("dual_client_started")

    async def stop(self) -> None:
        """停止双客户端。

        先发送停止事件（让订阅者有机会在客户端断连前执行清理），
        再依次断开 Bot 和 Userbot 的连接。
        """
        logger.info("正在停止双客户端...")

        # 先通知订阅者，此时客户端仍然可用
        await self._event_bus.emit("dual_client_stopping")

        try:
            await self.bot.stop()
        except Exception as e:
            logger.warning("停止 Bot 客户端时出错: %s", e)

        try:
            await self.userbot.stop()
        except Exception as e:
            logger.warning("停止 Userbot 客户端时出错: %s", e)

        logger.info("双客户端已停止")

    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        prefer_bot: bool = True,
        **kwargs: Any,
    ) -> Message:
        """智能选择客户端发送消息。

        Args:
            chat_id: 目标聊天 ID 或用户名
            text: 消息文本
            prefer_bot: 是否优先使用 Bot（低风险），默认 True
            **kwargs: 传递给 send_message 的额外参数

        Returns:
            发送成功的消息对象

        Raises:
            ClientError: 两个客户端均发送失败时抛出
        """
        # 选择主要和备用客户端
        primary = self.bot if prefer_bot else self.userbot
        fallback = self.userbot if prefer_bot else self.bot
        primary_name = "Bot" if prefer_bot else "Userbot"
        fallback_name = "Userbot" if prefer_bot else "Bot"

        try:
            return await primary.send_message(chat_id, text, **kwargs)
        except Exception as e:
            logger.warning(
                "%s 发送消息失败，尝试使用 %s: %s",
                primary_name, fallback_name, e,
            )

        # 主客户端失败，尝试备用客户端
        try:
            return await fallback.send_message(chat_id, text, **kwargs)
        except Exception as e:
            raise ClientError(
                f"双客户端均无法向 {chat_id} 发送消息: {e}"
            ) from e

    async def notify_admin(self, text: str) -> Message:
        """向管理员发送通知（始终使用 Bot）。

        Args:
            text: 通知文本

        Returns:
            发送成功的消息对象

        Raises:
            ClientError: 发送失败时抛出
        """
        admin_id = self._config.telegram.admin_user_id
        if not admin_id:
            raise ClientError("未配置管理员用户 ID (admin_user_id)")

        logger.debug("向管理员 %s 发送通知", admin_id)
        return await self.bot.send_message(admin_id, text)
