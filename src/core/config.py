"""配置加载与验证 — .env 环境变量 + YAML 配置解析。"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .constants import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_ENV_PATH,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_SESSION_DIR,
)
from .exceptions import ConfigError

logger = logging.getLogger(__name__)

# 匹配 ${ENV_VAR} 格式的环境变量引用
_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


class AttrDict(dict):
    """支持属性访问的字典，用于配置数据。

    支持 config.telegram.api_id 这样的链式属性访问。
    """

    def __getattr__(self, key: str) -> Any:
        """通过属性名获取值，嵌套字典自动转换为 AttrDict。"""
        try:
            value = self[key]
            if isinstance(value, dict) and not isinstance(value, AttrDict):
                value = AttrDict(value)
                self[key] = value
            return value
        except KeyError:
            raise AttributeError(f"配置中不存在键: {key}")

    def __setattr__(self, key: str, value: Any) -> None:
        """通过属性名设置值。"""
        self[key] = value


def _substitute_env_vars(value: Any) -> Any:
    """递归替换配置值中的 ${ENV_VAR} 为环境变量实际值。

    Args:
        value: 待替换的配置值，支持字符串、字典和列表的递归处理。

    Returns:
        替换后的配置值。
    """
    if isinstance(value, str):
        return _ENV_VAR_PATTERN.sub(
            lambda m: os.environ.get(m.group(1), m.group(0)), value
        )
    if isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]
    return value


@dataclass
class Config:
    """应用配置数据类，提供对各配置节的类型化访问。"""

    # Telegram 配置
    telegram: AttrDict = field(default_factory=AttrDict)
    # 数据库配置
    database: AttrDict = field(default_factory=AttrDict)
    # 速率限制配置
    rate_limit: AttrDict = field(default_factory=AttrDict)
    # LLM 配置
    llm: AttrDict = field(default_factory=AttrDict)
    # 插件配置
    plugins: AttrDict = field(default_factory=AttrDict)
    # 插件专属配置
    plugin_config: AttrDict = field(default_factory=AttrDict)
    # 日志配置
    logging: AttrDict = field(default_factory=AttrDict)
    # 原始配置数据
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def get(self, key: str, default: Any = None) -> Any:
        """从原始配置中获取顶层键的值。"""
        return self._raw.get(key, default)

    @property
    def session_dir(self) -> str:
        """获取 session 文件目录路径。"""
        return self.telegram.get("session_dir", DEFAULT_SESSION_DIR)

    @property
    def log_level(self) -> str:
        """获取日志级别。"""
        return self.logging.get("level", DEFAULT_LOG_LEVEL)

    @property
    def log_format(self) -> str:
        """获取日志格式字符串。"""
        return self.logging.get("format", DEFAULT_LOG_FORMAT)


def _validate_config(config: Config) -> None:
    """验证必填配置字段是否存在。

    Args:
        config: 待验证的配置对象。

    Raises:
        ConfigError: 当必填字段缺失或为空时抛出。
    """
    required_fields = {
        "api_id": config.telegram.get("api_id"),
        "api_hash": config.telegram.get("api_hash"),
        "bot_token": config.telegram.get("bot_token"),
        "admin_user_id": config.telegram.get("admin_user_id"),
    }
    missing = [name for name, val in required_fields.items()
               if not val or str(val).startswith("${")]
    if missing:
        raise ConfigError(f"缺少必填配置字段: {', '.join(missing)}")

    # 验证数值字段类型（避免运行时 ValueError）
    for field_name in ("api_id", "admin_user_id"):
        try:
            int(config.telegram.get(field_name))
        except (ValueError, TypeError):
            raise ConfigError(f"配置字段 {field_name} 必须为整数")


def load_config(
    config_path: str = DEFAULT_CONFIG_PATH,
    env_path: str = DEFAULT_ENV_PATH,
) -> Config:
    """加载并解析配置文件。

    先加载 .env 环境变量，再读取 YAML 配置并替换其中的变量引用。

    Args:
        config_path: YAML 配置文件路径。
        env_path: .env 文件路径。

    Returns:
        解析并验证后的 Config 对象。

    Raises:
        ConfigError: 当配置文件不存在或解析失败时抛出。
    """
    # 加载 .env 文件
    env_file = Path(env_path)
    if env_file.exists():
        load_dotenv(env_file)
        logger.info("已加载环境变量文件: %s", env_path)

    # 读取 YAML 配置
    config_file = Path(config_path)
    if not config_file.exists():
        raise ConfigError(f"配置文件不存在: {config_path}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            raw_data: dict[str, Any] = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML 解析失败: {e}") from e
    except OSError as e:
        raise ConfigError(f"配置文件读取失败: {e}") from e

    # 替换环境变量
    data = _substitute_env_vars(raw_data)

    config = Config(
        telegram=AttrDict(data.get("telegram", {})),
        database=AttrDict(data.get("database", {})),
        rate_limit=AttrDict(data.get("rate_limit", {})),
        llm=AttrDict(data.get("llm", {})),
        plugins=AttrDict(data.get("plugins", {})),
        plugin_config=AttrDict(data.get("plugin_config", {})),
        logging=AttrDict(data.get("logging", {})),
        _raw=data,
    )

    _validate_config(config)
    logger.info("配置加载完成: %s", config_path)
    return config
