"""AI 问答插件

订阅 ask_ai 事件，通过 LLM 回答用户问题。
由 /ask 命令触发。
"""

from __future__ import annotations

from typing import Any

from src.core.exceptions import LLMError
from src.llm.base_provider import ChatMessage
from src.plugins.plugin_base import PluginBase


class AskHandlerPlugin(PluginBase):
    """AI 问答插件 — 接收问题，调用 LLM 返回回答"""

    @property
    def name(self) -> str:
        return "ai_summary.ask_handler"

    @property
    def description(self) -> str:
        return "AI 问答，通过 LLM 回答用户提出的问题"

    async def setup(self) -> None:
        """订阅 ask_ai 事件"""
        cfg = self.get_plugin_config()
        self._language = cfg.get("language", "zh-CN")
        await self.event_bus.subscribe("ask_ai", self._handle_ask)
        self.logger.info("AI 问答插件已启动")

    async def teardown(self) -> None:
        """取消事件订阅"""
        await self.event_bus.unsubscribe("ask_ai", self._handle_ask)

    async def _handle_ask(self, **kwargs: Any) -> None:
        """处理 AI 问答请求

        事件参数:
            question: 用户问题（必需）
            reply_to_chat: 回复发送到哪个聊天（必需）
        """
        question = kwargs.get("question", "")
        reply_to = kwargs.get("reply_to_chat")
        if not question or not reply_to:
            return

        try:
            answer = await self._generate_answer(question)
            header = "🤖 AI 回答：\n\n"
            await self.client.send_message(reply_to, header + answer)
            self.logger.info("已回答问题: %s", question[:50])
        except LLMError as e:
            await self.client.send_message(reply_to, f"回答生成失败: {e}")
            self.logger.error("LLM 调用失败: %s", e)
        except Exception as e:
            await self.client.send_message(reply_to, "AI 问答失败，请稍后重试。")
            self.logger.error("AI 问答异常: %s", e)

    async def _generate_answer(self, question: str) -> str:
        """调用 LLM 生成回答"""
        if not self.llm:
            raise LLMError("LLM 管理器未配置，无法回答问题")

        provider = self.llm.get_provider()
        system_msg = (
            f"你是一个有帮助的 AI 助手。请用 {self._language} 回答问题。"
            "回答应简洁、准确、有用。"
        )
        response = await provider.chat([
            ChatMessage(role="system", content=system_msg),
            ChatMessage(role="user", content=question),
        ])
        return response.content
