"""自动回复规则匹配引擎

监控新消息，按优先级匹配数据库中的自动回复规则。
匹配成功后通过事件总线通知 template_reply 插件发送回复。
"""

import re
from typing import Optional

from telethon import events

from src.database.repositories.rule_repo import RuleRepository
from src.database.models.rule import AutoReplyRule
from src.plugins.plugin_base import PluginBase


class RuleEnginePlugin(PluginBase):
    """规则匹配引擎 — 监控消息并匹配自动回复规则"""

    @property
    def name(self) -> str:
        return "auto_reply.rule_engine"

    @property
    def description(self) -> str:
        return "自动回复规则匹配引擎（关键词/正则/精确匹配）"

    async def setup(self) -> None:
        """注册消息处理器"""
        # 使用 Userbot 监控所有聊天
        self.client.userbot.client.add_event_handler(
            self._on_new_message, events.NewMessage()
        )
        self._register_handler(self._on_new_message)
        self.logger.info("自动回复规则引擎已启动")

    async def teardown(self) -> None:
        """移除事件处理器"""
        for handler in self._handlers:
            self.client.userbot.client.remove_event_handler(handler)
        self._handlers.clear()

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        """处理新消息，尝试匹配规则"""
        try:
            # 忽略自己发的消息和 Bot 命令
            if event.out:
                return
            text = event.raw_text
            if not text or text.startswith("/"):
                return

            # 从数据库查询适用规则
            matched_rule = await self._find_matching_rule(text, event.chat_id)
            if matched_rule:
                # 通过事件总线通知 template_reply 发送回复
                await self.event_bus.emit(
                    "auto_reply_matched",
                    event=event,
                    response=matched_rule.response,
                    chat_id=event.chat_id,
                    rule_name=matched_rule.name,
                )
                self.logger.info(
                    "规则 '%s' 匹配成功 (chat: %d)",
                    matched_rule.name, event.chat_id,
                )
        except Exception as e:
            self.logger.error("规则匹配处理失败: %s", e)

    async def _find_matching_rule(
        self, text: str, chat_id: int
    ) -> Optional[AutoReplyRule]:
        """在数据库中查找第一条匹配的规则（按优先级降序）

        Args:
            text: 消息文本
            chat_id: 聊天 ID

        Returns:
            匹配的规则，未匹配返回 None
        """
        session = self.db.get_session()
        async with session:
            repo = RuleRepository(session)
            rules = await repo.get_enabled_rules(chat_id)

            for rule in rules:
                if self._match_rule(text, rule):
                    return rule
        return None

    @staticmethod
    def _match_rule(text: str, rule: AutoReplyRule) -> bool:
        """检查文本是否匹配单条规则

        Args:
            text: 消息文本
            rule: 自动回复规则

        Returns:
            是否匹配
        """
        pattern = rule.pattern

        if rule.rule_type == "keyword":
            # 关键词包含匹配（大小写不敏感）
            return pattern.lower() in text.lower()

        if rule.rule_type == "regex":
            # 正则表达式匹配
            try:
                return bool(re.search(pattern, text, re.IGNORECASE))
            except re.error:
                return False

        if rule.rule_type == "exact":
            # 精确匹配（大小写不敏感）
            return text.strip().lower() == pattern.strip().lower()

        return False
