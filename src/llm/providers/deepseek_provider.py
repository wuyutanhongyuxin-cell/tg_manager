"""DeepSeek LLM Provider

DeepSeek 提供 OpenAI 兼容 API，复用 OpenAI Provider 的逻辑。
仅需覆盖 name 和默认 base_url。
"""

from __future__ import annotations

from typing import Any

from .openai_provider import OpenAIProvider

# DeepSeek API 默认端点
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek Provider — OpenAI 兼容 API

    继承 OpenAIProvider，仅修改默认 base_url 和 name。
    """

    def __init__(self, config: dict[str, Any]) -> None:
        # 如果用户未指定 base_url，使用 DeepSeek 默认端点
        if not config.get("base_url"):
            config = {**config, "base_url": DEFAULT_DEEPSEEK_BASE_URL}
        super().__init__(config)

    @property
    def name(self) -> str:
        return "deepseek"
