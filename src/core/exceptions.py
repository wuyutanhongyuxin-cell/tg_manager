"""
TG Manager 统一异常定义模块。

所有自定义异常均继承自 TGManagerError，便于统一捕获和处理。
"""


class TGManagerError(Exception):
    """TG Manager 基础异常，所有自定义异常的父类。"""

    def __init__(self, message: str = "", *args: object) -> None:
        """初始化基础异常。

        Args:
            message: 错误描述信息。
        """
        self.message = message
        super().__init__(message, *args)


class ConfigError(TGManagerError):
    """配置错误，如缺少必填字段或格式不正确。"""


class ClientError(TGManagerError):
    """Telegram 客户端相关错误。"""


class RateLimitError(TGManagerError):
    """速率限制错误，当操作频率超出阈值时抛出。"""


class PluginError(TGManagerError):
    """插件加载或执行错误。"""


class LLMError(TGManagerError):
    """LLM 调用错误，如 API 请求失败或响应解析异常。"""


class DatabaseError(TGManagerError):
    """数据库操作错误，如连接失败或查询异常。"""


class AuthError(TGManagerError):
    """权限错误，当用户无权执行某操作时抛出。"""


class FloodWaitError(ClientError):
    """Telegram FloodWait 异常，需要等待指定秒数后重试。"""

    def __init__(self, wait_seconds: int, message: str = "") -> None:
        """初始化 FloodWait 异常。

        Args:
            wait_seconds: 需要等待的秒数。
            message: 错误描述信息。
        """
        self.wait_seconds = wait_seconds
        if not message:
            message = f"FloodWait: 需要等待 {wait_seconds} 秒"
        super().__init__(message)
