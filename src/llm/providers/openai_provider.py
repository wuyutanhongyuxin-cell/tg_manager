"""OpenAI LLM Provider

通过 httpx 异步调用 OpenAI Chat Completions API。
支持自定义 base_url，兼容所有 OpenAI 兼容的 API 端点。
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from src.core.exceptions import LLMError

from ..base_provider import BaseLLMProvider, ChatMessage, LLMResponse

# 默认 OpenAI API 端点
DEFAULT_BASE_URL = "https://api.openai.com/v1"
# HTTP 超时（秒）
DEFAULT_TIMEOUT = 60


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider — 支持 GPT 系列及所有 OpenAI 兼容 API"""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        api_key = config.get("api_key", "")
        base_url = config.get("base_url", DEFAULT_BASE_URL) or DEFAULT_BASE_URL
        self._base_url = base_url.rstrip("/")
        timeout = config.get("timeout", DEFAULT_TIMEOUT)
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    @property
    def name(self) -> str:
        return "openai"

    async def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """调用 OpenAI Chat Completions API"""
        payload = self._build_payload(messages, **kwargs)
        try:
            resp = await self._client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_response(data)
        except httpx.HTTPStatusError as e:
            raise LLMError(
                f"OpenAI API 错误 {e.response.status_code}: {e.response.text[:200]}"
            ) from e
        except httpx.RequestError as e:
            raise LLMError(f"OpenAI 请求失败: {e}") from e

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """流式调用 OpenAI API（SSE）"""
        payload = self._build_payload(messages, stream=True, **kwargs)
        try:
            async with self._client.stream(
                "POST", "/chat/completions", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    text = self._parse_sse_line(line)
                    if text:
                        yield text
        except httpx.HTTPStatusError as e:
            raise LLMError(f"OpenAI 流式错误: {e}") from e
        except httpx.RequestError as e:
            raise LLMError(f"OpenAI 流式请求失败: {e}") from e

    def _build_payload(
        self, messages: list[ChatMessage], stream: bool = False, **kwargs: Any
    ) -> dict[str, Any]:
        """构建请求体"""
        return {
            "model": kwargs.get("model", self._model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "temperature": kwargs.get("temperature", self._temperature),
            "stream": stream,
        }

    @staticmethod
    def _parse_response(data: dict) -> LLMResponse:
        """解析 OpenAI 标准响应"""
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage", {})
        return LLMResponse(
            content=message.get("content", ""),
            model=data.get("model", ""),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            raw=data,
        )

    @staticmethod
    def _parse_sse_line(line: str) -> str:
        """解析 SSE 行，提取文本增量"""
        import json

        if not line.startswith("data: ") or line.strip() == "data: [DONE]":
            return ""
        try:
            data = json.loads(line[6:])
            delta = data.get("choices", [{}])[0].get("delta", {})
            return delta.get("content", "")
        except (json.JSONDecodeError, IndexError):
            return ""

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        await self._client.aclose()
