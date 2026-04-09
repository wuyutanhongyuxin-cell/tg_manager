"""管理员命令处理器

提供 /ban、/mute、/warn、/kick 群管命令。
通过事件总线触发 admin_actions 插件执行实际操作。
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AdminHandler:
    """管理员命令处理器 — ban/mute/warn/kick"""

    def __init__(self, config: Any, event_bus: Any) -> None:
        """初始化处理器

        Args:
            config: 应用配置实例
            event_bus: 事件总线（用于触发群管操作）
        """
        self._config = config
        self._event_bus = event_bus
        self._admin_id = int(config.telegram.admin_user_id)

    async def _check_admin(self, event: Any) -> bool:
        """检查发送者是否为管理员"""
        if event.sender_id != self._admin_id:
            await event.reply("⛔ 无权限执行此操作")
            return False
        return True

    async def _parse_user_id(self, event: Any) -> Optional[int]:
        """解析目标用户 ID（优先从回复消息获取）"""
        # 回复消息优先
        replied = await event.get_reply_message()
        if replied and replied.sender_id:
            return replied.sender_id
        # 从命令参数解析
        parts = event.raw_text.split()
        if len(parts) >= 2:
            try:
                return int(parts[1])
            except ValueError:
                return None
        return None

    async def handle_ban(self, event: Any) -> None:
        """处理 /ban 命令"""
        if not await self._check_admin(event):
            return
        user_id = await self._parse_user_id(event)
        if not user_id:
            await event.reply("用法: /ban <user_id> [原因]\n或回复目标消息使用 /ban")
            return

        parts = event.raw_text.split(maxsplit=2)
        reason = parts[2] if len(parts) > 2 else ""
        await self._event_bus.emit(
            "ban_user", chat_id=event.chat_id, user_id=user_id, reason=reason
        )
        await event.reply(f"✅ 已提交封禁: 用户 {user_id}")

    async def handle_mute(self, event: Any) -> None:
        """处理 /mute 命令（默认禁言 1 小时）"""
        if not await self._check_admin(event):
            return
        user_id = await self._parse_user_id(event)
        if not user_id:
            await event.reply("用法: /mute <user_id> [分钟数]\n或回复目标消息使用 /mute")
            return

        parts = event.raw_text.split()
        duration = 3600  # 默认 1 小时
        if len(parts) > 2:
            try:
                duration = int(parts[2]) * 60  # 分钟转秒
            except ValueError:
                pass
        await self._event_bus.emit(
            "mute_user", chat_id=event.chat_id, user_id=user_id, duration=duration
        )
        await event.reply(f"✅ 已提交禁言: 用户 {user_id} ({duration // 60} 分钟)")

    async def handle_warn(self, event: Any) -> None:
        """处理 /warn 命令"""
        if not await self._check_admin(event):
            return
        user_id = await self._parse_user_id(event)
        if not user_id:
            await event.reply("用法: /warn <user_id> [原因]\n或回复目标消息使用 /warn")
            return

        parts = event.raw_text.split(maxsplit=2)
        reason = parts[2] if len(parts) > 2 else ""
        await self._event_bus.emit(
            "warn_user", chat_id=event.chat_id, user_id=user_id, reason=reason
        )
        await event.reply(f"⚠️ 已提交警告: 用户 {user_id}")

    async def handle_kick(self, event: Any) -> None:
        """处理 /kick 命令"""
        if not await self._check_admin(event):
            return
        user_id = await self._parse_user_id(event)
        if not user_id:
            await event.reply("用法: /kick <user_id>\n或回复目标消息使用 /kick")
            return

        await self._event_bus.emit(
            "kick_user", chat_id=event.chat_id, user_id=user_id
        )
        await event.reply(f"✅ 已提交踢出: 用户 {user_id}")

    def register(self, command_router: Any) -> None:
        """注册管理命令到路由器"""
        command_router.register("ban", self.handle_ban, "封禁用户")
        command_router.register("mute", self.handle_mute, "禁言用户")
        command_router.register("warn", self.handle_warn, "警告用户")
        command_router.register("kick", self.handle_kick, "踢出用户")
