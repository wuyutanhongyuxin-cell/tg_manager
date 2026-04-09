"""群组管理操作插件

提供 ban/mute/warn/kick 群管功能。
通过事件总线接收命令，使用 Userbot 执行管理操作。
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights

from src.plugins.plugin_base import PluginBase


class AdminActionsPlugin(PluginBase):
    """群管操作插件 — ban/mute/warn/kick"""

    @property
    def name(self) -> str:
        return "group.admin_actions"

    @property
    def description(self) -> str:
        return "群组管理操作（封禁/禁言/警告/踢出）"

    async def setup(self) -> None:
        """订阅管理操作事件"""
        await self.event_bus.subscribe("ban_user", self._handle_ban)
        await self.event_bus.subscribe("mute_user", self._handle_mute)
        await self.event_bus.subscribe("warn_user", self._handle_warn)
        await self.event_bus.subscribe("kick_user", self._handle_kick)

        # 从配置获取警告阈值
        cfg = self.get_plugin_config()
        self._max_warns: int = cfg.get("max_warns", 3)
        self.logger.info("群管插件已启动，最大警告次数: %d", self._max_warns)

    async def teardown(self) -> None:
        """取消所有事件订阅"""
        # 显式映射，避免脆弱的字符串拼接
        event_handler_map = {
            "ban_user": self._handle_ban,
            "mute_user": self._handle_mute,
            "warn_user": self._handle_warn,
            "kick_user": self._handle_kick,
        }
        for event_name, handler in event_handler_map.items():
            await self.event_bus.unsubscribe(event_name, handler)

    async def _handle_ban(self, **kwargs: Any) -> None:
        """封禁用户（禁止查看消息）

        kwargs: chat_id, user_id, reason(可选)
        """
        chat_id = kwargs["chat_id"]
        user_id = kwargs["user_id"]
        reason = kwargs.get("reason", "")

        rights = ChatBannedRights(
            until_date=None, view_messages=True  # 永久封禁
        )
        try:
            await self.client.userbot.client(
                EditBannedRequest(chat_id, user_id, rights)
            )
            await self._update_user_status(user_id, is_banned=True, ban_reason=reason)
            self.logger.info("已封禁用户 %d (chat: %d)", user_id, chat_id)
            await self.event_bus.emit(
                "user_banned", chat_id=chat_id, user_id=user_id, reason=reason
            )
        except Exception as e:
            self.logger.error("封禁用户 %d 失败: %s", user_id, e)

    async def _handle_mute(self, **kwargs: Any) -> None:
        """禁言用户

        kwargs: chat_id, user_id, duration(秒，可选，默认1小时)
        """
        chat_id = kwargs["chat_id"]
        user_id = kwargs["user_id"]
        duration = kwargs.get("duration", 3600)

        until = datetime.now(timezone.utc) + timedelta(seconds=duration)
        # 完整的禁言权限：禁止发送文字、媒体、贴纸、GIF、链接、投票等
        rights = ChatBannedRights(
            until_date=until,
            send_messages=True,
            send_media=True,
            send_stickers=True,
            send_gifs=True,
            send_games=True,
            send_inline=True,
            send_polls=True,
        )

        try:
            await self.client.userbot.client(
                EditBannedRequest(chat_id, user_id, rights)
            )
            self.logger.info("已禁言用户 %d %d秒 (chat: %d)", user_id, duration, chat_id)
            await self.event_bus.emit(
                "user_muted", chat_id=chat_id, user_id=user_id, duration=duration
            )
        except Exception as e:
            self.logger.error("禁言用户 %d 失败: %s", user_id, e)

    async def _handle_warn(self, **kwargs: Any) -> None:
        """警告用户，达到阈值自动封禁

        kwargs: chat_id, user_id, reason(可选)
        """
        chat_id = kwargs["chat_id"]
        user_id = kwargs["user_id"]
        reason = kwargs.get("reason", "")

        warn_count = await self._increment_warn(user_id)

        if warn_count >= self._max_warns:
            # 达到阈值，自动封禁
            self.logger.info("用户 %d 警告达到 %d 次，自动封禁", user_id, warn_count)
            await self._handle_ban(chat_id=chat_id, user_id=user_id, reason="警告次数超限")
        else:
            await self.event_bus.emit(
                "user_warned",
                chat_id=chat_id, user_id=user_id,
                warn_count=warn_count, max_warns=self._max_warns,
            )

    async def _handle_kick(self, **kwargs: Any) -> None:
        """踢出用户（可重新加入）

        kwargs: chat_id, user_id
        """
        chat_id = kwargs["chat_id"]
        user_id = kwargs["user_id"]
        try:
            await self.client.userbot.client.kick_participant(chat_id, user_id)
            self.logger.info("已踢出用户 %d (chat: %d)", user_id, chat_id)
            await self.event_bus.emit(
                "user_kicked", chat_id=chat_id, user_id=user_id
            )
        except Exception as e:
            self.logger.error("踢出用户 %d 失败: %s", user_id, e)

    async def _increment_warn(self, user_id: int) -> int:
        """增加用户警告计数并返回当前计数（通过 UserRepository）"""
        from src.database.repositories.user_repo import UserRepository
        session = self.db.get_session()
        async with session:
            async with session.begin():
                repo = UserRepository(session)
                return await repo.increment_warn(user_id)

    async def _update_user_status(
        self, user_id: int, is_banned: bool = False, ban_reason: str = ""
    ) -> None:
        """更新用户封禁状态（通过 UserRepository）"""
        from src.database.repositories.user_repo import UserRepository
        session = self.db.get_session()
        async with session:
            async with session.begin():
                repo = UserRepository(session)
                await repo.update_ban_status(user_id, is_banned, ban_reason)
