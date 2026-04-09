"""
TG Manager 全局常量定义模块。

包含应用信息、默认路径、速率限制默认值和日志格式等。
"""

# === 应用信息 ===
APP_NAME: str = "TG Manager"
VERSION: str = "0.1.0"

# === 默认路径 ===
DEFAULT_CONFIG_PATH: str = "config/config.yaml"
DEFAULT_ENV_PATH: str = ".env"
DEFAULT_SESSION_DIR: str = "sessions"

# === 速率限制默认值（与 config.example.yaml 保持一致） ===
DEFAULT_GLOBAL_PER_MINUTE: int = 30
DEFAULT_PER_CHAT_INTERVAL: float = 3.0
DEFAULT_JOIN_PER_DAY: int = 20
DEFAULT_ADD_MEMBER_PER_DAY: int = 50
DEFAULT_ADD_MEMBER_INTERVAL: float = 30.0
DEFAULT_DOWNLOAD_CONCURRENT: int = 3
DEFAULT_FLOOD_WAIT_MULTIPLIER: float = 1.5
DEFAULT_FLOOD_WAIT_PAUSE_THRESHOLD: int = 3
DEFAULT_FLOOD_WAIT_PAUSE_DURATION: int = 300
DEFAULT_JITTER_MIN: float = 0.5
DEFAULT_JITTER_MAX: float = 2.0

# === 日志格式 ===
DEFAULT_LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_LOG_LEVEL: str = "INFO"

# === 内置事件名称 ===
EVENT_MESSAGE_RECEIVED: str = "message_received"
EVENT_MESSAGE_SENT: str = "message_sent"
EVENT_PLUGIN_LOADED: str = "plugin_loaded"
EVENT_ERROR: str = "error"
