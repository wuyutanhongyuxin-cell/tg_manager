"""消息转发插件

监控新消息，根据数据库中的转发规则自动转发。
支持三种模式：标准转发、复制、去标签复制。
"""

import re
from typing import Optional

from telethon import events

from src.database.repositories.forward_rule_repo import ForwardRuleRepository
from src.database.models.forward_rule import ForwardRule
from src.plugins.plugin_base import PluginBase


class ForwarderPlugin(PluginBase):
    """消息转发插件 — 基于规则自动转发消息"""

    @property
    def name(self) -> str:
        return "message.forwarder"

    @property
    def description(self) -> str:
        return "基于规则的消息自动转发（支持转发/复制/去标签）"

    async def setup(self) -> None:
        """注册 Userbot 新消息事件处理器"""
        self.client.userbot.client.add_event_handler(
            self._on_new_message, events.NewMessage()
        )
        self._register_handler(self._on_new_message)
        self.logger.info("消息转发插件已启动")

    async def teardown(self) -> None:
        """移除事件处理器"""
        for handler in self._handlers:
            self.client.userbot.client.remove_event_handler(handler)
        self._handlers.clear()

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        """处理新消息，检查是否匹配转发规则"""
        try:
            chat_id = event.chat_id
            # 查询该聊天的转发规则
            session = self.db.get_session()
            async with session:
                repo = ForwardRuleRepository(session)
                rules = await repo.get_by_source(chat_id)
                if not rules:
                    return
                for rule in rules:
                    await self._apply_rule(event, rule)
        except Exception as e:
            self.logger.error("处理转发规则失败: %s", e)

    async def _apply_rule(
        self, event: events.NewMessage.Event, rule: ForwardRule
    ) -> None:
        """对单条消息应用一条转发规则"""
        # 检查过滤条件
        if not self._matches_filter(event.raw_text, rule):
            return

        target = rule.target_chat_id
        try:
            if rule.forward_type == "forward":
                await self._forward(event, target)
            elif rule.forward_type == "copy":
                await self._copy(event, target)
            elif rule.forward_type == "copy_clean":
                await self._copy_clean(event, target)

            await self.event_bus.emit(
                "message_forwarded",
                source_chat=event.chat_id,
                target_chat=target,
                message_id=event.message.id,
                forward_type=rule.forward_type,
            )
        except Exception as e:
            self.logger.error(
                "转发消息 %d 到 %d 失败: %s", event.message.id, target, e
            )

    def _matches_filter(self, text: str, rule: ForwardRule) -> bool:
        """检查消息是否匹配规则的过滤条件"""
        if not rule.filter_pattern or rule.filter_type == "none":
            return True
        if not text:
            return False
        if rule.filter_type == "keyword":
            return rule.filter_pattern.lower() in text.lower()
        if rule.filter_type == "regex":
            return bool(re.search(rule.filter_pattern, text))
        return True

    async def _forward(self, event: events.NewMessage.Event, target: int) -> None:
        """标准转发（保留"转发自"标签）"""
        await self.client.userbot.forward_message(
            event.chat_id, event.message.id, target
        )

    async def _copy(self, event: events.NewMessage.Event, target: int) -> None:
        """复制消息（无转发标签，保留媒体）"""
        msg = event.message
        kwargs: dict = {}
        if msg.media:
            kwargs["file"] = msg.media
        if msg.entities:
            kwargs["formatting_entities"] = msg.entities
        await self.client.userbot.send_message(
            target, msg.message or "", **kwargs
        )

    async def _copy_clean(self, event: events.NewMessage.Event, target: int) -> None:
        """去标签复制（移除所有来源标记）"""
        # 与 copy 相同，Telethon send_message 不会带转发标签
        await self._copy(event, target)
