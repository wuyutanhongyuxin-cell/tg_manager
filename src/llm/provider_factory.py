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
    """注册一个 LLM Provider 类到全局注册表"""
    _registry[name] = cls
    logger.debug("已注册 LLM Provider: %s -> %s", name, cls.__name__)


def create_provider(name: str, config: dict[str, Any]) -> BaseLLMProvider:
    """根据名称创建 Provider 实例；未注册或构造失败时抛 LLMError"""
    cls = _registry.get(name)
    if cls is None:
        available = ", ".join(_registry.keys()) or "（无）"
        raise LLMError(f"未知的 LLM Provider: '{name}'，可用: {available}")
    try:
        return cls(config)
    except Exception as e:
        raise LLMError(f"创建 Provider '{name}' 失败: {e}") from e


class LLMManager:
    """LLM 管理器 — 根据全局配置创建和缓存 Provider 实例

    启动时自动探测哪些 Provider 配好了 api_key（Ollama 例外，无需 key），
    并把"不可用"的 Provider 从候选列表剔除。若配置指定的 default_provider
    不可用，自动 fallback 到第一个可用的。
    """

    def __init__(self, config: Any) -> None:
        self._config = config
        self._providers: dict[str, BaseLLMProvider] = {}
        self._default_name: str = ""
        # 启动时探测到的可用 provider 列表（按配置顺序）
        self._available: list[str] = []

    def init(self) -> None:
        """注册内置 Provider + 探测可用 Provider + 选定默认 Provider"""
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
        providers_cfg = llm_cfg.get("providers", {}) or {}

        # 探测哪些 provider 配置可用
        self._available = [
            name for name, cfg in providers_cfg.items()
            if self._is_configured(name, cfg or {})
        ]

        # 选定默认 provider：优先使用配置的，不可用则 fallback 到第一个可用的
        configured_default = llm_cfg.get("default_provider", "")
        if configured_default in self._available:
            self._default_name = configured_default
        elif self._available:
            self._default_name = self._available[0]
            if configured_default:
                logger.warning(
                    "默认 Provider '%s' 未配置 api_key，自动切换到 '%s'",
                    configured_default, self._default_name,
                )
        else:
            self._default_name = ""
            logger.warning(
                "未发现任何已配置的 LLM Provider，AI 功能将不可用。"
                "请在 .env 中设置至少一个 *_API_KEY 后重启"
            )

        logger.info(
            "LLM 管理器初始化完成，可用 Provider: %s，默认: %s",
            self._available or "（无）", self._default_name or "（无）",
        )

    @staticmethod
    def _is_configured(name: str, cfg: dict[str, Any]) -> bool:
        """判断某个 provider 的配置是否可用

        规则：
        - ollama: 只要配置了 base_url 就算可用（本地推理，无 api_key）
        - 其他: api_key 非空且不是未展开的 ${...} 占位符
        """
        if name == "ollama":
            return bool((cfg.get("base_url") or "").strip())
        api_key = (cfg.get("api_key") or "").strip()
        if not api_key:
            return False
        # 环境变量未展开的情况（例如 .env 中没有定义该变量）
        if api_key.startswith("${") and api_key.endswith("}"):
            return False
        return True

    def list_available(self) -> list[str]:
        """返回所有已配置可用的 provider 名称列表"""
        return list(self._available)

    def get_current_name(self) -> str:
        """返回当前默认 provider 名称（可能为空字符串）"""
        return self._default_name

    def switch_default(self, name: str) -> None:
        """运行时切换默认 provider；目标未配置/不可用时抛 LLMError"""
        if name not in self._available:
            available = ", ".join(self._available) or "（无）"
            raise LLMError(
                f"Provider '{name}' 未配置或不可用。可用: {available}"
            )
        self._default_name = name
        logger.info("默认 LLM Provider 已切换为: %s", name)

    def get_provider(self, name: str = "") -> BaseLLMProvider:
        """获取指定名称的 Provider 实例（带缓存）；name 为空时使用默认"""
        provider_name = name or self._default_name
        if not provider_name:
            raise LLMError(
                "未配置任何可用的 LLM Provider，"
                "请在 .env 中设置至少一个 *_API_KEY 后重启"
            )
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
