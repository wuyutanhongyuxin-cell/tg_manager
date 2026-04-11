"""关键词监控告警插件 — 关键词存 DB，由 /keyword 命令管理。"""

import re
from typing import Any

from telethon import events

from src.database.repositories.keyword_repo import KeywordRepository
from src.plugins.plugin_base import PluginBase


class KeywordAlertPlugin(PluginBase):
    """关键词告警插件 — DB 持久化 + 事件总线管理"""

    @property
    def name(self) -> str:
        return "monitor.keyword_alert"

    @property
    def description(self) -> str:
        return "关键词监控，匹配时向管理员发送告警"

    async def setup(self) -> None:
        cfg = self.get_plugin_config()
        self._regex_patterns: list[str] = cfg.get("regex_patterns", [])
        self._monitored_chats: list[int] = cfg.get("monitored_chats", [])
        self._compiled_regex: list = []

        # 关键词从 DB 加载（非 YAML）
        self._keywords: list[str] = await self._load_keywords_from_db()

        # 兼容旧版：DB 为空时把 YAML 中残留的关键词迁移一次
        if not self._keywords:
            yaml_keywords = cfg.get("keywords", []) or []
            if yaml_keywords:
                await self._migrate_yaml_keywords(yaml_keywords)
                self._keywords = await self._load_keywords_from_db()

        for pattern in self._regex_patterns:
            try:
                self._compiled_regex.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                self.logger.warning("无效正则 '%s': %s", pattern, e)

        # 订阅 /keyword 命令事件
        await self.event_bus.subscribe("keyword_add", self._handle_add)
        await self.event_bus.subscribe("keyword_remove", self._handle_remove)
        await self.event_bus.subscribe("keyword_list", self._handle_list)

        # Userbot 监听所有新消息
        self.client.userbot.client.add_event_handler(
            self._on_new_message, events.NewMessage()
        )
        self._register_handler(self._on_new_message)
        self.logger.info(
            "关键词监控已启动，关键词: %d 个，正则: %d 个",
            len(self._keywords), len(self._compiled_regex),
        )

    async def teardown(self) -> None:
        for handler in self._handlers:
            self.client.userbot.client.remove_event_handler(handler)
        self._handlers.clear()
        await self.event_bus.unsubscribe("keyword_add", self._handle_add)
        await self.event_bus.unsubscribe("keyword_remove", self._handle_remove)
        await self.event_bus.unsubscribe("keyword_list", self._handle_list)

    # ---------- DB 辅助 ----------

    async def _load_keywords_from_db(self) -> list[str]:
        """从数据库加载所有启用的关键词"""
        async with self.db.get_session() as session:
            repo = KeywordRepository(session)
            rows = await repo.get_enabled()
            return [r.keyword for r in rows]

    async def _migrate_yaml_keywords(self, yaml_keywords: list[str]) -> None:
        """首次运行时把 YAML 关键词导入数据库（一次性兼容）"""
        async with self.db.get_session() as session:
            repo = KeywordRepository(session)
            for kw in yaml_keywords:
                kw = (kw or "").strip()
                if kw and not await repo.get_by_keyword(kw):
                    await repo.create(keyword=kw)
            await session.commit()
        self.logger.info("已迁移 %d 个 YAML 关键词", len(yaml_keywords))

    # ---------- /keyword 命令事件 ----------

    async def _handle_add(self, **kwargs: Any) -> None:
        keyword = (kwargs.get("keyword") or "").strip()
        reply_to = kwargs.get("reply_to_chat")
        created_by = kwargs.get("created_by")
        if not keyword or reply_to is None:
            return
        async with self.db.get_session() as session:
            repo = KeywordRepository(session)
            if await repo.get_by_keyword(keyword):
                await self.client.send_message(
                    reply_to, f"⚠️ 关键词已存在: `{keyword}`"
                )
                return
            await repo.create(keyword=keyword, created_by=created_by)
            await session.commit()
        self._keywords = await self._load_keywords_from_db()
        await self.client.send_message(
            reply_to,
            f"✅ 已添加关键词: `{keyword}`\n当前共 {len(self._keywords)} 个",
        )

    async def _handle_remove(self, **kwargs: Any) -> None:
        keyword = (kwargs.get("keyword") or "").strip()
        reply_to = kwargs.get("reply_to_chat")
        if not keyword or reply_to is None:
            return
        async with self.db.get_session() as session:
            repo = KeywordRepository(session)
            existing = await repo.get_by_keyword(keyword)
            if not existing:
                await self.client.send_message(
                    reply_to, f"⚠️ 未找到关键词: `{keyword}`"
                )
                return
            await repo.delete(existing)
            await session.commit()
        self._keywords = await self._load_keywords_from_db()
        await self.client.send_message(
            reply_to,
            f"✅ 已移除关键词: `{keyword}`\n当前共 {len(self._keywords)} 个",
        )

    async def _handle_list(self, **kwargs: Any) -> None:
        reply_to = kwargs.get("reply_to_chat")
        if reply_to is None:
            return
        # 直接查 DB，避免内存与持久层不同步
        self._keywords = await self._load_keywords_from_db()
        if not self._keywords:
            text = (
                "🔔 当前未配置任何监控关键词。\n\n"
                "添加: `/keyword add <关键词>`"
            )
        else:
            kw_list = "\n".join(f"  • `{k}`" for k in self._keywords)
            text = (
                f"🔔 监控关键词共 {len(self._keywords)} 个：\n\n"
                f"{kw_list}\n\n"
                "管理: `/keyword add <词>` / `/keyword remove <词>`"
            )
        await self.client.send_message(reply_to, text)

    # ---------- 消息匹配 ----------

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        try:
            if self._monitored_chats and event.chat_id not in self._monitored_chats:
                return
            if event.out:
                return
            text = event.raw_text
            if not text:
                return
            matched = self._check_match(text)
            if matched:
                await self._send_alert(event, matched)
        except Exception as e:
            self.logger.error("关键词检查失败: %s", e)

    def _check_match(self, text: str) -> str:
        text_lower = text.lower()
        for keyword in self._keywords:
            if keyword.lower() in text_lower:
                return keyword
        for pattern in self._compiled_regex:
            if pattern.search(text):
                return pattern.pattern
        return ""

    async def _send_alert(self, event: events.NewMessage.Event, matched: str) -> None:
        sender = await event.get_sender()
        sender_name = getattr(sender, "first_name", "未知") if sender else "未知"
        alert_text = (
            f"🔔 关键词告警\n\n"
            f"匹配: {matched}\n"
            f"聊天: {event.chat_id}\n"
            f"发送者: {sender_name} (ID: {event.sender_id})\n"
            f"内容: {event.raw_text[:200]}"
        )
        try:
            await self.client.notify_admin(alert_text)
            self.logger.info(
                "已发送关键词告警: '%s' in chat %d", matched, event.chat_id
            )
        except Exception as e:
            self.logger.error("发送告警失败: %s", e)
