"""Admin command handlers."""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.bot_interface.middlewares.throttle import throttle

logger = logging.getLogger(__name__)


class AdminHandler:
    """Handle `/ban`, `/mute`, `/warn`, and `/kick`."""

    def __init__(self, config: Any, event_bus: Any) -> None:
        self._config = config
        self._event_bus = event_bus
        self._admin_id = int(config.telegram.admin_user_id)

    async def _check_admin(self, event: Any) -> bool:
        if event.sender_id != self._admin_id:
            await event.reply("⛔ 无权限执行此操作")
            return False
        return True

    async def _parse_user_id(self, event: Any) -> Optional[int]:
        replied = await event.get_reply_message()
        if replied and replied.sender_id:
            return replied.sender_id

        parts = event.raw_text.split()
        if len(parts) >= 2:
            try:
                return int(parts[1])
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_mute_duration(raw_text: str, replied: bool) -> int:
        """Return mute duration in minutes."""
        parts = raw_text.split()
        arg_index = 1 if replied else 2
        if len(parts) <= arg_index:
            return 60

        try:
            minutes = int(parts[arg_index])
        except ValueError:
            return 60

        return max(minutes, 1)

    async def handle_ban(self, event: Any) -> None:
        if not await self._check_admin(event):
            return

        user_id = await self._parse_user_id(event)
        if not user_id:
            await event.reply("用法: /ban <user_id> [原因]\n或回复目标消息使用 /ban")
            return

        replied = await event.get_reply_message()
        parts = event.raw_text.split(maxsplit=2)
        if replied and replied.sender_id:
            reason = event.raw_text.split(maxsplit=1)[1] if len(parts) > 1 else ""
        else:
            reason = parts[2] if len(parts) > 2 else ""

        await self._event_bus.emit(
            "ban_user",
            chat_id=event.chat_id,
            user_id=user_id,
            reason=reason,
        )
        await event.reply(f"✅ 已提交封禁: 用户 {user_id}")

    async def handle_mute(self, event: Any) -> None:
        if not await self._check_admin(event):
            return

        user_id = await self._parse_user_id(event)
        if not user_id:
            await event.reply("用法: /mute <user_id> [分钟]\n或回复目标消息使用 /mute [分钟]")
            return

        replied = await event.get_reply_message()
        duration_minutes = self._parse_mute_duration(
            event.raw_text,
            replied=bool(replied and replied.sender_id),
        )
        duration = duration_minutes * 60

        await self._event_bus.emit(
            "mute_user",
            chat_id=event.chat_id,
            user_id=user_id,
            duration=duration,
        )
        await event.reply(f"✅ 已提交禁言: 用户 {user_id} ({duration_minutes} 分钟)")

    async def handle_warn(self, event: Any) -> None:
        if not await self._check_admin(event):
            return

        user_id = await self._parse_user_id(event)
        if not user_id:
            await event.reply("用法: /warn <user_id> [原因]\n或回复目标消息使用 /warn")
            return

        replied = await event.get_reply_message()
        parts = event.raw_text.split(maxsplit=2)
        if replied and replied.sender_id:
            reason = event.raw_text.split(maxsplit=1)[1] if len(parts) > 1 else ""
        else:
            reason = parts[2] if len(parts) > 2 else ""

        await self._event_bus.emit(
            "warn_user",
            chat_id=event.chat_id,
            user_id=user_id,
            reason=reason,
        )
        await event.reply(f"⚠️ 已提交警告: 用户 {user_id}")

    async def handle_kick(self, event: Any) -> None:
        if not await self._check_admin(event):
            return

        user_id = await self._parse_user_id(event)
        if not user_id:
            await event.reply("用法: /kick <user_id>\n或回复目标消息使用 /kick")
            return

        await self._event_bus.emit(
            "kick_user",
            chat_id=event.chat_id,
            user_id=user_id,
        )
        await event.reply(f"✅ 已提交移出: 用户 {user_id}")

    def register(self, command_router: Any) -> None:
        command_router.register("ban", throttle()(self.handle_ban), "封禁用户")
        command_router.register("mute", throttle()(self.handle_mute), "禁言用户")
        command_router.register("warn", throttle()(self.handle_warn), "警告用户")
        command_router.register("kick", throttle()(self.handle_kick), "移出用户")
