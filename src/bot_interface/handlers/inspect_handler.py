"""聊天信息检查命令处理器

提供管理员排查 chat_id 的工具：
- /whereami            打印当前 chat 信息
- /whereami (回复转发) 解析转发源 chat_id（适合源频道）
- /dialogs [关键词]    通过 userbot 列出/搜索最近会话（适合受限频道）
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from telethon.utils import get_peer_id

from src.bot_interface.middlewares.throttle import throttle

logger = logging.getLogger(__name__)


class InspectHandler:
    """Handle `/whereami` 与 `/dialogs`，帮助管理员获取目标 chat_id。"""

    def __init__(self, config: Any, client: Any) -> None:
        self._config = config
        self._client = client
        self._admin_id = int(config.telegram.admin_user_id)

    async def _check_admin(self, event: Any) -> bool:
        if event.sender_id != self._admin_id:
            await event.reply("⛔ 无权限执行此操作")
            return False
        return True

    # ---------- /whereami ----------

    async def handle_whereami(self, event: Any) -> None:
        if not await self._check_admin(event):
            return
        # 优先级 1: 回复了一条转发消息 → 解析转发源
        replied = await event.get_reply_message()
        if replied is not None and getattr(replied, "fwd_from", None) is not None:
            await self._reply_forward_source(event, replied)
            return
        # 优先级 2: 命令本身就是转发的 → 解析转发源
        if getattr(event.message, "fwd_from", None) is not None:
            await self._reply_forward_source(event, event.message)
            return
        # 默认：打印当前 chat
        await self._reply_current_chat(event)

    async def _reply_current_chat(self, event: Any) -> None:
        chat = await event.get_chat()
        chat_type = type(chat).__name__
        title = (
            getattr(chat, "title", None)
            or getattr(chat, "first_name", None)
            or "私聊"
        )
        await event.reply(
            "📍 **当前位置**\n\n"
            f"`chat_id = {event.chat_id}`\n"
            f"`sender_id = {event.sender_id}`\n"
            f"类型: {chat_type}\n"
            f"名称: {title}\n\n"
            "💡 想拿源频道 chat_id？把它的消息转发到这里，再回复 /whereami；\n"
            "或者用 `/dialogs <关键词>` 在最近会话里搜。"
        )

    async def _reply_forward_source(self, event: Any, message: Any) -> None:
        """从转发消息提取原始 chat_id（用 telethon.utils.get_peer_id 标准化）"""
        fwd = message.fwd_from
        src_id: Optional[int] = None
        src_type = "未知"
        if fwd.from_id is not None:
            try:
                src_id = get_peer_id(fwd.from_id)
            except Exception as e:
                logger.debug("get_peer_id 失败: %s", e)
            peer_cls = type(fwd.from_id).__name__
            if peer_cls == "PeerChannel":
                src_type = "频道/超级群"
            elif peer_cls == "PeerChat":
                src_type = "群组"
            elif peer_cls == "PeerUser":
                src_type = "用户"
        name = fwd.from_name or "?"
        if src_id is None:
            await event.reply(
                "⚠️ 该转发消息未携带源 chat_id（可能匿名/隐藏发送者）\n"
                f"显示名: {name}"
            )
            return
        await event.reply(
            "📍 **转发来源**\n\n"
            f"`chat_id = {src_id}`\n"
            f"类型: {src_type}\n"
            f"名称: {name}\n\n"
            f"💡 用作 `/forward add <name> {src_id} <dst>` 的 src 参数"
        )

    # ---------- /dialogs ----------

    async def handle_dialogs(self, event: Any) -> None:
        if not await self._check_admin(event):
            return
        parts = event.raw_text.split(maxsplit=1)
        keyword = parts[1].strip().lower() if len(parts) > 1 else ""
        try:
            dialogs = await self._client.userbot.get_dialogs(limit=200)
        except Exception as e:
            logger.error("拉取 dialogs 失败: %s", e, exc_info=True)
            await event.reply(f"❌ 拉取对话列表失败: {e}")
            return

        matched: list[str] = []
        for d in dialogs:
            title = (getattr(d, "name", None) or "").strip()
            if keyword and keyword not in title.lower():
                continue
            if getattr(d, "is_channel", False):
                icon = "📢"
            elif getattr(d, "is_group", False):
                icon = "👥"
            else:
                icon = "👤"
            matched.append(f"{icon} `{d.id}`  {title}")

        if not matched:
            await event.reply(
                f"🔍 未匹配到对话: `{keyword}`\n\n"
                "提示: `/dialogs` 不带参数列出全部，"
                "`/dialogs <关键词>` 模糊搜索标题"
            )
            return

        shown = matched[:30]
        header = f"🔍 **匹配 {len(matched)} 个对话**"
        if len(matched) > len(shown):
            header += f" (显示前 {len(shown)})"
        body = "\n".join(shown)
        tip = ""
        if not keyword and len(matched) > len(shown):
            tip = "\n\n💡 试试 `/dialogs <更具体的词>` 缩小范围"
        await event.reply(f"{header}\n\n{body}{tip}")

    # ---------- register ----------

    def register(self, command_router: Any) -> None:
        command_router.register(
            "whereami", throttle()(self.handle_whereami), "查看当前/转发源 chat_id"
        )
        command_router.register(
            "dialogs", throttle()(self.handle_dialogs), "列出/搜索最近会话"
        )
