"""群聊消息总结插件

通过 LLM 总结群聊的最近消息，帮助用户快速了解讨论内容。
通过事件总线接收总结请求，结果通过 Bot 发送给请求者。
"""

from __future__ import annotations

from typing import Any

from src.core.exceptions import LLMError
from src.database.repositories.message_repo import MessageRepository
from src.llm.base_provider import ChatMessage
from src.llm.prompt_templates import CHAT_SUMMARY
from src.plugins.plugin_base import PluginBase


class ChatSummarizerPlugin(PluginBase):
    """群聊总结插件 — 使用 LLM 总结最近的群聊消息"""

    @property
    def name(self) -> str:
        return "ai_summary.chat_summarizer"

    @property
    def description(self) -> str:
        return "群聊消息 AI 总结，快速了解讨论内容"

    async def setup(self) -> None:
        """订阅总结请求事件"""
        cfg = self.get_plugin_config()
        self._language = cfg.get("language", "zh-CN")
        self._default_limit = cfg.get("chat_summary_limit", 200)

        await self.event_bus.subscribe("summarize_chat", self._handle_summarize)
        self.logger.info("群聊总结插件已启动")

    async def teardown(self) -> None:
        """取消事件订阅"""
        await self.event_bus.unsubscribe("summarize_chat", self._handle_summarize)

    async def _handle_summarize(self, **kwargs: Any) -> None:
        """处理总结请求

        事件参数:
            chat_id: 目标聊天 ID（必需）
            reply_to_chat: 回复发送到哪个聊天（必需）
            limit: 回溯消息条数（可选，默认使用配置值）
            chat_title: 聊天标题（可选）
        """
        chat_id = kwargs.get("chat_id")
        reply_to = kwargs.get("reply_to_chat")
        if not chat_id or not reply_to:
            return

        limit = kwargs.get("limit", self._default_limit)
        chat_title = kwargs.get("chat_title", str(chat_id))

        try:
            # 1. 从数据库获取最近消息
            messages_text = await self._fetch_messages(chat_id, limit)
            if not messages_text:
                await self.client.send_message(
                    reply_to, "该聊天暂无已记录的消息，无法生成总结。"
                )
                return

            # 2. 调用 LLM 生成总结
            summary = await self._generate_summary(messages_text, chat_title, limit)

            # 3. 发送总结结果
            header = f"📝 「{chat_title}」最近 {limit} 条消息总结：\n\n"
            await self.client.send_message(reply_to, header + summary)
            self.logger.info("已发送聊天总结: %s (%d 条消息)", chat_title, limit)

        except LLMError as e:
            await self.client.send_message(reply_to, f"总结生成失败: {e}")
            self.logger.error("LLM 调用失败: %s", e)
        except Exception as e:
            await self.client.send_message(reply_to, "总结生成时发生错误，请稍后重试。")
            self.logger.error("总结处理异常: %s", e)

    async def _fetch_messages(self, chat_id: int, limit: int) -> str:
        """从数据库获取消息并格式化为文本"""
        session = self.db.get_session()
        async with session:
            repo = MessageRepository(session)
            messages = await repo.get_by_chat(chat_id, limit=limit)

        if not messages:
            messages = await self.client.userbot.get_messages(chat_id, limit=limit)

        if not messages:
            return ""

        # 按时间正序排列，格式化为 "发送者: 内容"
        lines: list[str] = []
        for msg in reversed(messages):
            sender = msg.sender_id or "匿名"
            text = (msg.text or "").strip()
            if text:
                lines.append(f"[{sender}]: {text}")
        return "\n".join(lines)

    async def _generate_summary(
        self, messages_text: str, chat_title: str, count: int
    ) -> str:
        """调用 LLM 生成总结"""
        if not self.llm:
            raise LLMError("LLM 管理器未配置，无法生成总结")

        provider = self.llm.get_provider()
        # 使用模板构建 prompt
        system_msg = CHAT_SUMMARY.system.format(language=self._language)
        user_msg = CHAT_SUMMARY.user.format(
            chat_title=chat_title, count=count, messages=messages_text
        )
        response = await provider.chat([
            ChatMessage(role="system", content=system_msg),
            ChatMessage(role="user", content=user_msg),
        ])
        self.logger.debug("LLM 用量: %s", response.usage)
        return response.content
