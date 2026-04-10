"""AI summary and scheduler command handlers."""

from __future__ import annotations

import logging
from typing import Any

from src.bot_interface.middlewares.throttle import throttle

logger = logging.getLogger(__name__)


class SummaryHandler:
    """Handle `/summarize`, `/ask`, `/url`, and `/schedule`."""

    def __init__(self, config: Any, event_bus: Any) -> None:
        self._config = config
        self._event_bus = event_bus
        self._admin_id = int(config.telegram.admin_user_id)

    async def _check_admin(self, event: Any) -> bool:
        if event.sender_id != self._admin_id:
            await event.reply("⛔ 无权限执行此操作")
            return False
        return True

    async def handle_summarize(self, event: Any) -> None:
        if not await self._check_admin(event):
            return

        parts = event.raw_text.split()
        limit = 200
        if len(parts) > 1:
            try:
                limit = min(int(parts[1]), 1000)
            except ValueError:
                await event.reply("用法: /summarize [消息数量]\n默认 200 条")
                return

        chat = await event.get_chat()
        chat_title = getattr(chat, "title", str(event.chat_id))

        await event.reply(f"正在总结《{chat_title}》最近 {limit} 条消息...")
        await self._event_bus.emit(
            "summarize_chat",
            chat_id=event.chat_id,
            reply_to_chat=event.chat_id,
            limit=limit,
            chat_title=chat_title,
        )

    async def handle_ask(self, event: Any) -> None:
        if not await self._check_admin(event):
            return

        parts = event.raw_text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await event.reply("用法: /ask <你的问题>")
            return

        await self._event_bus.emit(
            "ask_ai",
            question=parts[1].strip(),
            reply_to_chat=event.chat_id,
        )

    async def handle_url_summary(self, event: Any) -> None:
        if not await self._check_admin(event):
            return

        parts = event.raw_text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await event.reply("用法: /url <链接>")
            return

        await event.reply("正在提取并总结内容...")
        await self._event_bus.emit(
            "summarize_content",
            url=parts[1].strip(),
            reply_to_chat=event.chat_id,
        )

    async def handle_schedule(self, event: Any) -> None:
        if not await self._check_admin(event):
            return

        parts = event.raw_text.split(maxsplit=1)
        sub_cmd = parts[1].strip() if len(parts) > 1 else "list"

        if sub_cmd == "list" or not sub_cmd:
            await self._event_bus.emit("schedule_list", reply_to_chat=event.chat_id)
            return

        if sub_cmd.startswith("add "):
            await self._parse_schedule_add(event, sub_cmd[4:])
            return

        if sub_cmd.startswith("remove "):
            await self._parse_schedule_remove(event, sub_cmd[7:])
            return

        await event.reply(
            "用法:\n"
            "/schedule list\n"
            "/schedule add <名称> <cron(5段)> <消息>\n"
            "/schedule remove <ID>"
        )

    async def _parse_schedule_add(self, event: Any, args: str) -> None:
        tokens = args.split()
        if len(tokens) < 7:
            await event.reply(
                "格式: /schedule add <名称> <分> <时> <日> <月> <周> <消息>"
            )
            return

        name = tokens[0]
        cron_expr = " ".join(tokens[1:6])
        message_text = " ".join(tokens[6:])

        await self._event_bus.emit(
            "schedule_add",
            name=name,
            cron_expr=cron_expr,
            chat_id=event.chat_id,
            text=message_text,
            reply_to_chat=event.chat_id,
            created_by=event.sender_id,
        )

    async def _parse_schedule_remove(self, event: Any, args: str) -> None:
        try:
            job_id = int(args.strip())
        except ValueError:
            await event.reply("用法: /schedule remove <任务ID>")
            return

        await self._event_bus.emit(
            "schedule_remove",
            job_id=job_id,
            reply_to_chat=event.chat_id,
        )

    def register(self, command_router: Any) -> None:
        command_router.register("summarize", throttle()(self.handle_summarize), "AI 总结群聊消息")
        command_router.register("ask", throttle()(self.handle_ask), "AI 问答")
        command_router.register("url", throttle()(self.handle_url_summary), "总结 URL 内容")
        command_router.register("schedule", throttle()(self.handle_schedule), "定时任务管理")
