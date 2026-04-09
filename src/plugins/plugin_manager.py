"""插件生命周期管理

负责插件的完整生命周期：发现 -> 过滤 -> 实例化 -> 启动 -> 停止。
"""

import logging
from typing import TYPE_CHECKING, Any, Optional

from src.core.exceptions import PluginError

from .plugin_base import PluginBase
from .plugin_loader import PluginLoader

if TYPE_CHECKING:
    from src.clients.dual_client import DualClient
    from src.core.config import Config
    from src.core.event_bus import EventBus
    from src.database.engine import DatabaseManager

logger = logging.getLogger(__name__)


class PluginManager:
    """管理插件的完整生命周期

    统一管理插件的发现、过滤、实例化、启动和停止流程，
    确保插件按正确顺序加载和卸载。
    """

    def __init__(
        self,
        client: "DualClient",
        config: "Config",
        event_bus: "EventBus",
        db: "DatabaseManager",
    ) -> None:
        """初始化插件管理器

        Args:
            client: Telegram 双客户端实例
            config: 全局配置对象
            event_bus: 事件总线
            db: 数据库管理器
        """
        self._client = client
        self._config = config
        self._event_bus = event_bus
        self._db = db
        self._loader = PluginLoader()
        self._plugins: dict[str, PluginBase] = {}

    async def load_all(self) -> None:
        """发现、过滤、实例化并启动所有启用的插件

        执行完整的插件加载流程：
        1. 扫描发现所有插件类
        2. 根据配置过滤启用的插件
        3. 实例化每个插件
        4. 调用 setup() 初始化
        5. 发送 plugin_loaded 事件通知

        Raises:
            PluginError: 单个插件加载失败时记录错误并继续加载其他插件
        """
        # 发现所有插件类
        all_classes = self._loader.discover()

        # 根据配置过滤（从 config.plugins.enabled 读取启用模式）
        enabled_patterns: list[str] = self._config.plugins.get("enabled", [])
        enabled_classes = self._loader.filter_enabled(all_classes, enabled_patterns)

        # 逐一实例化并启动
        for plugin_cls in enabled_classes:
            try:
                instance: PluginBase = plugin_cls(
                    client=self._client,
                    config=self._config,
                    event_bus=self._event_bus,
                    db=self._db,
                )
                await instance.setup()
                self._plugins[instance.name] = instance

                # 通知其他组件插件已加载
                await self._event_bus.emit("plugin_loaded", plugin_name=instance.name)
                logger.info("插件已加载: %s - %s", instance.name, instance.description)

            except Exception as e:
                logger.error("加载插件 %s 失败: %s", plugin_cls.__name__, e, exc_info=True)

        logger.info("插件加载完成，共加载 %d 个插件", len(self._plugins))

    async def unload_all(self) -> None:
        """停止并清理所有已加载的插件

        按加载的逆序依次调用每个插件的 teardown() 方法，
        确保后加载的插件先被卸载，避免依赖问题。
        """
        plugin_names = list(reversed(self._plugins.keys()))
        for name in plugin_names:
            try:
                await self._plugins[name].teardown()
                logger.info("插件已卸载: %s", name)
            except Exception as e:
                logger.error("卸载插件 %s 失败: %s", name, e, exc_info=True)

        self._plugins.clear()
        logger.info("所有插件已卸载")

    async def reload_plugin(self, name: str) -> None:
        """重载单个插件

        先卸载指定插件，再重新发现并加载同名插件。

        Args:
            name: 要重载的插件名称

        Raises:
            PluginError: 插件不存在或重载失败时抛出
        """
        # 卸载现有实例
        if name in self._plugins:
            try:
                await self._plugins[name].teardown()
            except Exception as e:
                logger.error("卸载插件 %s 失败: %s", name, e, exc_info=True)
            del self._plugins[name]

        # 重新发现并加载（清除 Python 模块缓存以确保热重载）
        import sys
        stale_keys = [k for k in sys.modules if k.startswith("src.plugins.") and k != "src.plugins.plugin_base"]
        for k in stale_keys:
            del sys.modules[k]

        all_classes = self._loader.discover()
        matched = self._loader.filter_enabled(all_classes, [name])

        if not matched:
            raise PluginError(f"未找到名为 '{name}' 的插件")

        plugin_cls = matched[0]
        instance = plugin_cls(
            client=self._client,
            config=self._config,
            event_bus=self._event_bus,
            db=self._db,
        )
        await instance.setup()
        self._plugins[instance.name] = instance

        await self._event_bus.emit("plugin_reloaded", plugin_name=instance.name)
        logger.info("插件已重载: %s", instance.name)

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """按名称获取已加载的插件实例

        Args:
            name: 插件名称

        Returns:
            插件实例，若未找到则返回 None
        """
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict[str, Any]]:
        """返回所有已加载插件的信息列表

        Returns:
            包含每个插件名称和描述的字典列表
        """
        return [
            {"name": plugin.name, "description": plugin.description}
            for plugin in self._plugins.values()
        ]
