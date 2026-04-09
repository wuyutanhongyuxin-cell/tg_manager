"""LLM Provider 工厂 + 注册表

负责注册、创建和管理 LLM Provider 实例。
通过配置中的 provider 名称自动选择对应实现。
"""

from __future__ import annotations

import logging
from typing import Any

from src.core.exceptions import LLMError

from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

# 全局 Provider 注册表
_registry: dict[str, type[BaseLLMProvider]] = {}


def register_provider(name: str, cls: type[BaseLLMProvider]) -> None:
    """注册一个 LLM Provider 类

    Args:
        name: Provider 标识名称（如 "openai"、"claude"）
        cls: Provider 类（必须继承 BaseLLMProvider）
    """
    _registry[name] = cls
    logger.debug("已注册 LLM Provider: %s -> %s", name, cls.__name__)


def create_provider(name: str, config: dict[str, Any]) -> BaseLLMProvider:
    """根据名称创建 Provider 实例

    Args:
        name: Provider 标识名称
        config: Provider 配置字典

    Returns:
        已初始化的 Provider 实例

    Raises:
        LLMError: Provider 未注册或创建失败
    """
    cls = _registry.get(name)
    if cls is None:
        available = ", ".join(_registry.keys()) or "（无）"
        raise LLMError(f"未知的 LLM Provider: '{name}'，可用: {available}")
    try:
        return cls(config)
    except Exception as e:
        raise LLMError(f"创建 Provider '{name}' 失败: {e}") from e


def get_available_providers() -> list[str]:
    """获取所有已注册的 Provider 名称列表"""
    return list(_registry.keys())


class LLMManager:
    """LLM 管理器 — 根据全局配置创建和缓存 Provider 实例

    在应用启动时初始化，提供统一的 Provider 获取入口。
    """

    def __init__(self, config: Any) -> None:
        """初始化 LLM 管理器

        Args:
            config: 全局配置对象，需包含 config.llm 段
        """
        self._config = config
        self._providers: dict[str, BaseLLMProvider] = {}
        self._default_name: str = ""

    def init(self) -> None:
        """从配置中读取 LLM 设置，注册内置 Provider

        在调用 get_provider() 之前必须先调用此方法。
        """
        # 延迟导入，避免循环引用 + 按需注册
        from .providers.claude_provider import ClaudeProvider
        from .providers.deepseek_provider import DeepSeekProvider
        from .providers.gemini_provider import GeminiProvider
        from .providers.ollama_provider import OllamaProvider
        from .providers.openai_provider import OpenAIProvider

        register_provider("openai", OpenAIProvider)
        register_provider("claude", ClaudeProvider)
        register_provider("gemini", GeminiProvider)
        register_provider("deepseek", DeepSeekProvider)
        register_provider("ollama", OllamaProvider)

        llm_cfg = self._config.llm if hasattr(self._config, "llm") else {}
        self._default_name = llm_cfg.get("default_provider", "openai")
        logger.info(
            "LLM 管理器初始化完成，默认 Provider: %s", self._default_name
        )

    def get_provider(self, name: str = "") -> BaseLLMProvider:
        """获取指定名称的 Provider 实例（带缓存）

        Args:
            name: Provider 名称，空字符串使用默认 Provider

        Returns:
            Provider 实例

        Raises:
            LLMError: Provider 未配置或创建失败
        """
        provider_name = name or self._default_name
        # 命中缓存直接返回
        if provider_name in self._providers:
            return self._providers[provider_name]

        # 从配置中获取该 Provider 的参数
        llm_cfg = self._config.llm if hasattr(self._config, "llm") else {}
        providers_cfg = llm_cfg.get("providers", {})
        provider_cfg = providers_cfg.get(provider_name, {})
        if not provider_cfg:
            raise LLMError(f"未找到 Provider '{provider_name}' 的配置")

        provider = create_provider(provider_name, dict(provider_cfg))
        self._providers[provider_name] = provider
        logger.info("已创建 LLM Provider: %s (%s)", provider_name, provider)
        return provider

    async def close(self) -> None:
        """关闭所有已创建的 Provider，释放资源"""
        for name, provider in self._providers.items():
            try:
                await provider.close()
            except Exception as e:
                logger.warning("关闭 Provider '%s' 失败: %s", name, e)
        self._providers.clear()
        logger.info("LLM 管理器已关闭")
