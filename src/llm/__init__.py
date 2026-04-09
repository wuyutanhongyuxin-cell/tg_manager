"""统一 LLM 接口层

提供多模型支持（OpenAI/Claude/Gemini/DeepSeek/Ollama），
通过 LLMManager 管理 Provider 实例的创建和缓存。
"""

from .base_provider import BaseLLMProvider, ChatMessage, LLMResponse
from .prompt_templates import PromptTemplate, get_template
from .provider_factory import LLMManager, create_provider, register_provider

__all__ = [
    "BaseLLMProvider",
    "ChatMessage",
    "LLMResponse",
    "LLMManager",
    "PromptTemplate",
    "create_provider",
    "get_template",
    "register_provider",
]
