"""Ollama 本地 LLM Provider

通过 httpx 异步调用 Ollama REST API（本地部署）。
Ollama 使用 /api/chat 端点，格式与 OpenAI 类似但有差异。
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from src.core.exceptions import LLMError

from ..base_provider import BaseLLMProvider, ChatMessage, LLMResponse

# Ollama 默认本地端点
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_TIMEOUT = 120  # 本地模型可能较慢


class OllamaProvider(BaseLLMProvider):
    """Ollama Provider — 本地 LLM 推理"""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        base_url = config.get("base_url", DEFAULT_OLLAMA_URL) or DEFAULT_OLLAMA_URL
        self._base_url = base_url.rstrip("/")
        timeout = config.get("timeout", DEFAULT_TIMEOUT)
        self._client = httpx.AsyncClient(
            base_url=self._base_url, timeout=timeout
        )

    @property
    def name(self) -> str:
        return "ollama"

    async def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """调用 Ollama /api/chat（非流式）"""
        payload = self._build_payload(messages, stream=False, **kwargs)
        try:
            resp = await self._client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_response(data)
        except httpx.HTTPStatusError as e:
            raise LLMError(
                f"Ollama API 错误 {e.response.status_code}: "
                f"{e.response.text[:200]}"
            ) from e
        except httpx.ConnectError as e:
            raise LLMError(
                f"无法连接 Ollama ({self._base_url})，请确认 Ollama 已启动"
            ) from e
        except httpx.RequestError as e:
            raise LLMError(f"Ollama 请求失败: {e}") from e

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """流式调用 Ollama /api/chat"""
        import json

        payload = self._build_payload(messages, stream=True, **kwargs)
        try:
            async with self._client.stream(
                "POST", "/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
        except httpx.HTTPStatusError as e:
            raise LLMError(f"Ollama 流式错误: {e}") from e

    def _build_payload(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """构建 Ollama 请求体"""
        return {
            "model": kwargs.get("model", self._model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "options": {
                "num_predict": kwargs.get("max_tokens", self._max_tokens),
                "temperature": kwargs.get("temperature", self._temperature),
            },
        }

    @staticmethod
    def _parse_response(data: dict) -> LLMResponse:
        """解析 Ollama 非流式响应"""
        message = data.get("message", {})
        # Ollama 返回的 token 统计字段
        return LLMResponse(
            content=message.get("content", ""),
            model=data.get("model", ""),
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": (
                    data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                ),
            },
            raw=data,
        )

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        await self._client.aclose()
