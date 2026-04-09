"""LLM Provider 抽象基类

定义所有 LLM Provider 必须实现的统一接口。
支持同步对话、流式输出和便捷总结方法。
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM 响应数据类

    Attributes:
        content: 模型生成的文本内容
        model: 实际使用的模型名称
        usage: token 用量统计（prompt_tokens, completion_tokens, total_tokens）
        raw: 原始响应数据（用于调试）
    """

    content: str
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def prompt_tokens(self) -> int:
        """输入 token 数"""
        return self.usage.get("prompt_tokens", 0)

    @property
    def completion_tokens(self) -> int:
        """输出 token 数"""
        return self.usage.get("completion_tokens", 0)

    @property
    def total_tokens(self) -> int:
        """总 token 数"""
        return self.usage.get("total_tokens", 0)


@dataclass
class ChatMessage:
    """聊天消息，用于构建对话上下文

    Attributes:
        role: 消息角色（system / user / assistant）
        content: 消息文本内容
    """

    role: str
    content: str


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类

    所有 Provider 必须实现 chat() 方法。
    chat_stream() 和 summarize() 提供默认实现，子类可按需覆盖。
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """初始化 Provider

        Args:
            config: Provider 配置字典，包含 api_key、model 等参数
        """
        self._config = config
        self._model = config.get("model", "")
        self._max_tokens = config.get("max_tokens", 4096)
        self._temperature = config.get("temperature", 0.7)
        self.logger = logging.getLogger(f"llm.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider 唯一标识名称"""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """发送对话请求并返回完整响应

        Args:
            messages: 对话消息列表
            **kwargs: 覆盖默认参数（model, max_tokens, temperature 等）

        Returns:
            LLMResponse 对象

        Raises:
            LLMError: API 调用失败时抛出
        """
        ...

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """流式对话（逐 token 返回）

        默认实现：调用 chat() 一次性返回全部内容。
        支持流式的 Provider 应覆盖此方法。

        Args:
            messages: 对话消息列表
            **kwargs: 覆盖默认参数

        Yields:
            文本片段
        """
        response = await self.chat(messages, **kwargs)
        yield response.content

    async def summarize(self, text: str, instruction: str = "") -> str:
        """便捷总结方法

        Args:
            text: 需要总结的文本
            instruction: 额外指令（如"用中文总结"）

        Returns:
            总结文本
        """
        system_msg = instruction or "请简洁地总结以下内容，保留关键信息。"
        messages = [
            ChatMessage(role="system", content=system_msg),
            ChatMessage(role="user", content=text),
        ]
        response = await self.chat(messages)
        return response.content

    async def close(self) -> None:
        """关闭 Provider，释放资源（如 HTTP 连接池）

        子类持有 httpx.AsyncClient 等资源时应覆盖此方法。
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(model={self._model})>"
