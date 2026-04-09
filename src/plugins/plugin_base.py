"""插件抽象基类

定义所有插件必须遵循的接口规范，提供通用的生命周期管理方法。
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from src.clients.dual_client import DualClient
    from src.core.config import Config
    from src.core.event_bus import EventBus
    from src.database.engine import DatabaseManager


class PluginBase(ABC):
    """所有插件的抽象基类

    每个插件必须实现以下接口:
    - name: 插件唯一标识名称（如 "message.sender"）
    - description: 插件功能描述
    - setup(): 初始化插件，注册事件处理器和定时任务
    - teardown(): 清理资源，取消所有已注册的处理器
    """

    def __init__(
        self,
        client: "DualClient",
        config: "Config",
        event_bus: "EventBus",
        db: "DatabaseManager",
    ) -> None:
        """初始化插件基类

        Args:
            client: Telegram 双客户端实例（userbot + bot）
            config: 全局配置对象
            event_bus: 事件总线，用于插件间通信
            db: 数据库管理器，用于数据持久化
        """
        self.client = client
        self.config = config
        self.event_bus = event_bus
        self.db = db
        self._handlers: list[Callable[..., Any]] = []
        self.logger = logging.getLogger(f"plugin.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """插件唯一标识名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """插件功能描述"""
        ...

    @abstractmethod
    async def setup(self) -> None:
        """初始化插件，注册事件处理器和定时任务

        子类必须实现此方法，在其中完成:
        - 事件处理器注册
        - 定时任务注册
        - 所需资源的初始化
        """
        ...

    @abstractmethod
    async def teardown(self) -> None:
        """清理资源，取消所有已注册的处理器

        子类必须实现此方法，在其中完成:
        - 取消事件订阅
        - 停止定时任务
        - 释放占用的资源
        """
        ...

    def get_plugin_config(self) -> dict[str, Any]:
        """获取本插件的专属配置

        从全局配置中提取当前插件名称对应的配置段。
        若未配置则返回空字典。

        Returns:
            本插件的配置字典
        """
        return self.config.plugin_config.get(self.name, {})

    def _register_handler(self, handler: Callable[..., Any]) -> None:
        """记录已注册的处理器，便于 teardown 时统一清理

        Args:
            handler: 已注册到事件总线的处理器函数
        """
        self._handlers.append(handler)
        self.logger.debug("已注册处理器: %s", getattr(handler, "__name__", repr(handler)))
