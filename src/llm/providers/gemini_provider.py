"""Google Gemini LLM Provider

通过 httpx 异步调用 Gemini REST API（generativelanguage.googleapis.com）。
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import httpx

from src.core.exceptions import LLMError

from ..base_provider import BaseLLMProvider, ChatMessage, LLMResponse

# Gemini API 基础 URL
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_TIMEOUT = 60


class GeminiProvider(BaseLLMProvider):
    """Gemini Provider — 通过 REST API 调用 Google Gemini"""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._api_key = config.get("api_key", "")
        timeout = config.get("timeout", DEFAULT_TIMEOUT)
        self._client = httpx.AsyncClient(timeout=timeout)

    @property
    def name(self) -> str:
        return "gemini"

    async def chat(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> LLMResponse:
        """调用 Gemini generateContent API"""
        model = kwargs.get("model", self._model)
        url = f"{GEMINI_BASE_URL}/models/{model}:generateContent"
        payload = self._build_payload(messages, **kwargs)
        try:
            resp = await self._client.post(
                url, json=payload, params={"key": self._api_key}
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_response(data, model)
        except httpx.HTTPStatusError as e:
            raise LLMError(
                f"Gemini API 错误 {e.response.status_code}: "
                f"{e.response.text[:200]}"
            ) from e
        except httpx.RequestError as e:
            raise LLMError(f"Gemini 请求失败: {e}") from e

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """流式调用 Gemini API"""
        model = kwargs.get("model", self._model)
        url = f"{GEMINI_BASE_URL}/models/{model}:streamGenerateContent"
        payload = self._build_payload(messages, **kwargs)
        try:
            async with self._client.stream(
                "POST", url, json=payload, params={"key": self._api_key, "alt": "sse"}
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    text = self._parse_sse_chunk(line)
                    if text:
                        yield text
        except httpx.HTTPStatusError as e:
            raise LLMError(f"Gemini 流式错误: {e}") from e

    def _build_payload(
        self, messages: list[ChatMessage], **kwargs: Any
    ) -> dict[str, Any]:
        """构建 Gemini API 请求体

        Gemini 格式：contents[{role, parts[{text}]}]
        system 消息需通过 systemInstruction 传递。
        """
        system_text = ""
        contents: list[dict[str, Any]] = []
        for msg in messages:
            if msg.role == "system":
                system_text += msg.content + "\n"
            else:
                # Gemini 角色映射: user -> user, assistant -> model
                role = "model" if msg.role == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        payload: dict[str, Any] = {"contents": contents}
        if system_text.strip():
            payload["systemInstruction"] = {
                "parts": [{"text": system_text.strip()}]
            }
        # 生成配置
        payload["generationConfig"] = {
            "maxOutputTokens": kwargs.get("max_tokens", self._max_tokens),
            "temperature": kwargs.get("temperature", self._temperature),
        }
        return payload

    @staticmethod
    def _parse_response(data: dict, model: str) -> LLMResponse:
        """解析 Gemini 响应"""
        candidates = data.get("candidates", [{}])
        content_parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in content_parts)
        # Gemini 的 token 统计
        usage_meta = data.get("usageMetadata", {})
        return LLMResponse(
            content=text,
            model=model,
            usage={
                "prompt_tokens": usage_meta.get("promptTokenCount", 0),
                "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
                "total_tokens": usage_meta.get("totalTokenCount", 0),
            },
            raw=data,
        )

    @staticmethod
    def _parse_sse_chunk(line: str) -> str:
        """解析 Gemini SSE 流式响应"""
        import json

        if not line.startswith("data: "):
            return ""
        try:
            data = json.loads(line[6:])
            parts = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [])
            )
            return "".join(p.get("text", "") for p in parts)
        except (json.JSONDecodeError, IndexError):
            return ""

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        await self._client.aclose()
