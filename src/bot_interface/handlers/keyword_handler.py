"""关键词监控命令处理器

通过 /keyword 子命令在 TG 内管理监控关键词，无需编辑 config.yaml。
事件总线把请求派发给 KeywordAlertPlugin，由插件回写 DB 并刷新内存。
"""

from __future__ import annotations

import logging
from typing import Any

from src.bot_interface.middlewares.throttle import throttle

logger = logging.getLogger(__name__)


class KeywordHandler:
    """Handle `/keyword` 子命令: list/add/remove。"""

    def __init__(self, config: Any, event_bus: Any) -> None:
        self._config = config
        self._event_bus = event_bus
        self._admin_id = int(config.telegram.admin_user_id)

    async def _check_admin(self, event: Any) -> bool:
        if event.sender_id != self._admin_id:
            await event.reply("⛔ 无权限执行此操作")
            return False
        return True

    async def handle_keyword(self, event: Any) -> None:
        """分发 /keyword 子命令到 add/remove/list"""
        if not await self._check_admin(event):
            return

        parts = event.raw_text.split(maxsplit=2)
        sub_cmd = parts[1].strip().lower() if len(parts) > 1 else "list"
        arg = parts[2].strip() if len(parts) > 2 else ""

        if sub_cmd == "list":
            await self._event_bus.emit(
                "keyword_list", reply_to_chat=event.chat_id
            )
            return

        if sub_cmd == "add":
            if not arg:
                await event.reply("用法: /keyword add <关键词>")
                return
            await self._event_bus.emit(
                "keyword_add",
                keyword=arg,
                created_by=event.sender_id,
                reply_to_chat=event.chat_id,
            )
            return

        if sub_cmd in ("remove", "del", "rm"):
            if not arg:
                await event.reply("用法: /keyword remove <关键词>")
                return
            await self._event_bus.emit(
                "keyword_remove",
                keyword=arg,
                reply_to_chat=event.chat_id,
            )
            return

        await event.reply(
            "用法:\n"
            "/keyword list — 列出所有关键词\n"
            "/keyword add <关键词> — 添加关键词\n"
            "/keyword remove <关键词> — 移除关键词"
        )

    def register(self, command_router: Any) -> None:
        command_router.register(
            "keyword", throttle()(self.handle_keyword), "关键词监控管理"
        )
