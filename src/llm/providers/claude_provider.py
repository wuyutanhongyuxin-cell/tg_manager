"""Anthropic Claude LLM Provider

使用官方 anthropic SDK 异步调用 Claude API。
"""

from __future__ import annotations

from typing import Any, AsyncIterator

from src.core.exceptions import LLMError

from ..base_provider import BaseLLMProvider, ChatMessage, LLMResponse

# 默认超时（秒）
DEFAULT_TIMEOUT = 60


class ClaudeProvider(BaseLLMProvider):
    """Claude Provider — 使用 anthropic.AsyncAnthropic"""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        try:
            import anthropic
        except ImportError as e:
            raise LLMError("anthropic 包未安装，请运行: pip install anthropic") from e

        api_key = config.get("api_key", "")
        timeout = config.get("timeout", DEFAULT_TIMEOUT)
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=timeout,
        )

    @property
    def name(self) -> str:
        return "claude"

    async def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """调用 Claude Messages API"""
        system_text, api_messages = self._split_system(messages)
        try:
            params: dict[str, Any] = {
                "model": kwargs.get("model", self._model),
                "max_tokens": kwargs.get("max_tokens", self._max_tokens),
                "temperature": kwargs.get("temperature", self._temperature),
                "messages": api_messages,
            }
            if system_text:
                params["system"] = system_text

            response = await self._client.messages.create(**params)
            return self._parse_response(response)
        except Exception as e:
            # anthropic 库会抛出多种异常，统一包装
            if "anthropic" in type(e).__module__:
                raise LLMError(f"Claude API 错误: {e}") from e
            raise

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """流式调用 Claude API"""
        system_text, api_messages = self._split_system(messages)
        try:
            params: dict[str, Any] = {
                "model": kwargs.get("model", self._model),
                "max_tokens": kwargs.get("max_tokens", self._max_tokens),
                "temperature": kwargs.get("temperature", self._temperature),
                "messages": api_messages,
            }
            if system_text:
                params["system"] = system_text

            async with self._client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            if "anthropic" in type(e).__module__:
                raise LLMError(f"Claude 流式错误: {e}") from e
            raise

    @staticmethod
    def _split_system(
        messages: list[ChatMessage],
    ) -> tuple[str, list[dict[str, str]]]:
        """将 system 消息从对话列表中分离（Claude API 要求 system 单独传）

        Returns:
            (system_text, api_messages) 元组
        """
        system_parts: list[str] = []
        api_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            else:
                api_messages.append({"role": msg.role, "content": msg.content})
        return "\n".join(system_parts), api_messages

    @staticmethod
    def _parse_response(response: Any) -> LLMResponse:
        """解析 Claude Messages API 响应"""
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text
        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": (
                    response.usage.input_tokens + response.usage.output_tokens
                ),
            },
        )

    async def close(self) -> None:
        """关闭 anthropic 客户端"""
        await self._client.close()
