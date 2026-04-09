"""
TG Manager 核心模块。

导出配置、事件总线、速率限制器和所有自定义异常。
"""

from .config import Config, load_config
from .event_bus import EventBus
from .exceptions import (
    AuthError,
    ClientError,
    ConfigError,
    DatabaseError,
    FloodWaitError,
    LLMError,
    PluginError,
    RateLimitError,
    TGManagerError,
)
from .rate_limiter import RateLimiter

__all__ = [
    "Config",
    "load_config",
    "EventBus",
    "RateLimiter",
    "TGManagerError",
    "ConfigError",
    "ClientError",
    "RateLimitError",
    "PluginError",
    "LLMError",
    "DatabaseError",
    "AuthError",
    "FloodWaitError",
]
