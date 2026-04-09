"""关键词监控告警插件

监控指定聊天中的消息，当匹配到关键词时向管理员发送告警。
"""

import re
from typing import Any

from telethon import events

from src.plugins.plugin_base import PluginBase


class KeywordAlertPlugin(PluginBase):
    """关键词告警插件 — 监控消息中的关键词并通知管理员"""

    @property
    def name(self) -> str:
        return "monitor.keyword_alert"

    @property
    def description(self) -> str:
        return "关键词监控，匹配时向管理员发送告警"

    async def setup(self) -> None:
        """注册消息监听和加载关键词配置"""
        cfg = self.get_plugin_config()
        # 加载关键词列表和正则模式
        self._keywords: list[str] = cfg.get("keywords", [])
        self._regex_patterns: list[str] = cfg.get("regex_patterns", [])
        self._monitored_chats: list[int] = cfg.get("monitored_chats", [])

        if not self._keywords and not self._regex_patterns:
            self.logger.warning("未配置关键词或正则，插件将不会触发告警")
            return

        # 编译正则表达式
        self._compiled_regex = []
        for pattern in self._regex_patterns:
            try:
                self._compiled_regex.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                self.logger.warning("无效正则 '%s': %s", pattern, e)

        # 注册 Userbot 新消息处理器（Userbot 能监控所有聊天）
        self.client.userbot.client.add_event_handler(
            self._on_new_message, events.NewMessage()
        )
        self._register_handler(self._on_new_message)
        self.logger.info(
            "关键词监控已启动，关键词: %d 个，正则: %d 个",
            len(self._keywords), len(self._compiled_regex),
        )

    async def teardown(self) -> None:
        """移除事件处理器"""
        for handler in self._handlers:
            self.client.userbot.client.remove_event_handler(handler)
        self._handlers.clear()

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        """检查新消息是否匹配关键词"""
        try:
            # 过滤：仅监控指定聊天（空列表=监控全部）
            if self._monitored_chats and event.chat_id not in self._monitored_chats:
                return
            # 忽略自己发的消息
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
        """检查文本是否匹配任何关键词或正则

        Returns:
            匹配到的关键词/模式，未匹配返回空字符串
        """
        text_lower = text.lower()
        # 关键词匹配（大小写不敏感）
        for keyword in self._keywords:
            if keyword.lower() in text_lower:
                return keyword
        # 正则匹配
        for pattern in self._compiled_regex:
            if pattern.search(text):
                return pattern.pattern
        return ""

    async def _send_alert(self, event: events.NewMessage.Event, matched: str) -> None:
        """向管理员发送告警通知"""
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
            self.logger.info("已发送关键词告警: '%s' in chat %d", matched, event.chat_id)
        except Exception as e:
            self.logger.error("发送告警失败: %s", e)
