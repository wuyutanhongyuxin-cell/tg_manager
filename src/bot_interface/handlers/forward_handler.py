"""转发规则命令处理器

通过 /forward 子命令管理 forward_rules 表。直接读写 DB（消费插件无内存缓存）。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.bot_interface.middlewares.throttle import throttle
from src.database.repositories.forward_rule_repo import ForwardRuleRepository

logger = logging.getLogger(__name__)

VALID_MODES = {"forward", "copy", "copy_clean"}
VALID_FILTER_TYPES = {"keyword", "regex", "none"}
EDITABLE_FIELDS = {"src", "dst", "mode", "filter", "ftype", "note"}


class ForwardHandler:
    """Handle `/forward` 子命令: list/add/remove/toggle/edit。"""

    def __init__(self, config: Any, db: Any) -> None:
        self._config = config
        self._db = db
        self._admin_id = int(config.telegram.admin_user_id)

    async def _check_admin(self, event: Any) -> bool:
        if event.sender_id != self._admin_id:
            await event.reply("⛔ 无权限执行此操作")
            return False
        return True

    async def handle_forward(self, event: Any) -> None:
        if not await self._check_admin(event):
            return
        parts = event.raw_text.split()
        sub = parts[1].lower() if len(parts) > 1 else "list"
        args = parts[2:]
        try:
            if sub == "list":
                await self._list(event, args)
            elif sub == "add":
                await self._add(event, args)
            elif sub in ("remove", "rm", "del"):
                await self._remove(event, args)
            elif sub == "toggle":
                await self._toggle(event, args)
            elif sub == "edit":
                await self._edit(event, args)
            else:
                await self._usage(event, args)
        except Exception as e:
            logger.error("forward 命令失败: %s", e, exc_info=True)
            await event.reply(f"❌ 操作失败: {e}")

    async def _list(self, event: Any, args: list[str]) -> None:
        async with self._db.get_session() as session:
            rules = await ForwardRuleRepository(session).get_all(limit=200)
        if not rules:
            await event.reply(
                "📭 当前未配置任何转发规则。\n\n"
                "添加: `/forward add <name> <src> <dst> [mode]`"
            )
            return
        lines = [f"📤 **转发规则 ({len(rules)})**\n"]
        for r in rules:
            status = "✅" if r.is_enabled else "❌"
            f_info = f"{r.filter_type}:{r.filter_pattern}" if r.filter_pattern else "无"
            lines.append(
                f"{status} `{r.name}`\n"
                f"   {r.source_chat_id} → {r.target_chat_id}  [{r.forward_type}]\n"
                f"   过滤: {f_info}"
            )
        await event.reply("\n".join(lines))

    async def _add(self, event: Any, args: list[str]) -> None:
        if len(args) < 3:
            await event.reply(
                "用法: `/forward add <name> <src_id> <dst_id> [mode]`\n"
                "mode: forward (默认) / copy / copy_clean"
            )
            return
        name = args[0]
        try:
            src_id, dst_id = int(args[1]), int(args[2])
        except ValueError:
            await event.reply("❌ src_id 和 dst_id 必须是整数（频道通常 -100 开头）")
            return
        mode = args[3] if len(args) > 3 else "forward"
        if mode not in VALID_MODES:
            await event.reply(f"❌ 无效 mode: {mode}\n可选: {', '.join(VALID_MODES)}")
            return
        async with self._db.get_session() as session:
            repo = ForwardRuleRepository(session)
            if await repo.get_by_name(name):
                await event.reply(f"⚠️ 规则名已存在: `{name}`")
                return
            await repo.create(
                name=name, source_chat_id=src_id, target_chat_id=dst_id,
                forward_type=mode, filter_type="none",
            )
            await session.commit()
        await event.reply(
            f"✅ 已添加规则 `{name}`\n{src_id} → {dst_id}  [{mode}]\n过滤: 无（全转发）"
        )

    async def _remove(self, event: Any, args: list[str]) -> None:
        if not args:
            await event.reply("用法: `/forward remove <name>`")
            return
        async with self._db.get_session() as session:
            repo = ForwardRuleRepository(session)
            rule = await repo.get_by_name(args[0])
            if not rule:
                await event.reply(f"⚠️ 未找到规则: `{args[0]}`")
                return
            await repo.delete(rule)
            await session.commit()
        await event.reply(f"✅ 已删除规则: `{args[0]}`")

    async def _toggle(self, event: Any, args: list[str]) -> None:
        if not args:
            await event.reply("用法: `/forward toggle <name>`")
            return
        async with self._db.get_session() as session:
            repo = ForwardRuleRepository(session)
            rule = await repo.get_by_name(args[0])
            if not rule:
                await event.reply(f"⚠️ 未找到规则: `{args[0]}`")
                return
            new_state = not rule.is_enabled
            await repo.update(rule, is_enabled=new_state)
            await session.commit()
        await event.reply(f"{'✅ 已启用' if new_state else '❌ 已禁用'}规则: `{args[0]}`")

    async def _edit(self, event: Any, args: list[str]) -> None:
        if len(args) < 3:
            await event.reply(
                "用法: `/forward edit <name> <field> <value>`\n"
                "字段: src / dst / mode / filter / ftype / note"
            )
            return
        name, field, value = args[0], args[1].lower(), " ".join(args[2:])
        kw = self._build_kw(field, value)
        if kw is None:
            await event.reply(
                f"❌ 无效字段或值: `{field}={value}`\n字段: {', '.join(sorted(EDITABLE_FIELDS))}"
            )
            return
        async with self._db.get_session() as session:
            repo = ForwardRuleRepository(session)
            rule = await repo.get_by_name(name)
            if not rule:
                await event.reply(f"⚠️ 未找到规则: `{name}`")
                return
            await repo.update(rule, **kw)
            await session.commit()
        await event.reply(f"✅ 已更新 `{name}`.{field} → `{value}`")

    def _build_kw(self, field: str, value: str) -> Optional[dict]:
        """field=value 翻译成 ORM 字段 dict，无效返回 None"""
        try:
            if field == "src": return {"source_chat_id": int(value)}
            if field == "dst": return {"target_chat_id": int(value)}
            if field == "mode": return {"forward_type": value} if value in VALID_MODES else None
            if field == "filter": return {"filter_pattern": value}
            if field == "ftype": return {"filter_type": value} if value in VALID_FILTER_TYPES else None
            if field == "note": return {"note": value}
        except ValueError:
            return None
        return None

    async def _usage(self, event: Any, args: list[str]) -> None:
        await event.reply(
            "📤 **转发规则管理**\n\n"
            "`/forward list` — 列出规则\n"
            "`/forward add <name> <src> <dst> [mode]` — 添加\n"
            "`/forward remove <name>` — 删除\n"
            "`/forward toggle <name>` — 启用/禁用\n"
            "`/forward edit <name> <field> <value>` — 修改\n\n"
            "**mode**: forward / copy / copy_clean\n"
            "**field**: src / dst / mode / filter / ftype / note\n"
            "**ftype**: keyword / regex / none\n\n"
            "提示: 用 `/whereami` 在目标聊天获取 chat_id"
        )

    def register(self, command_router: Any) -> None:
        command_router.register("forward", throttle()(self.handle_forward), "转发规则管理")
