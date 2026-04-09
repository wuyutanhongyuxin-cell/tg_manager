"""插件发现与加载

自动扫描 plugins 子目录，发现并加载所有 PluginBase 子类。
支持根据通配符模式过滤启用的插件。
"""

import importlib
import inspect
import logging
import pkgutil
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional

from src.core.exceptions import PluginError

from .plugin_base import PluginBase

logger = logging.getLogger(__name__)

# 插件子目录所在的包路径
_PLUGINS_PACKAGE = "src.plugins"


class PluginLoader:
    """从 plugins 子目录中自动发现和加载插件类

    扫描 src/plugins 下的所有子包，查找继承自 PluginBase 的具体类，
    并支持根据通配符模式筛选需要启用的插件。
    """

    def discover(self) -> list[type[PluginBase]]:
        """扫描所有插件子目录，返回 PluginBase 子类列表

        遍历 src/plugins 下的每个子包，导入其中的所有模块，
        收集继承自 PluginBase 且非抽象的类。

        Returns:
            发现的插件类列表

        Raises:
            PluginError: 模块导入失败时记录警告并跳过
        """
        discovered: list[type[PluginBase]] = []
        plugins_path = Path(__file__).parent

        # 遍历 plugins 目录下的子包
        for sub_info in pkgutil.iter_modules([str(plugins_path)]):
            if not sub_info.ispkg:
                continue

            sub_package_name = f"{_PLUGINS_PACKAGE}.{sub_info.name}"

            # 遍历子包中的所有模块
            sub_path = plugins_path / sub_info.name
            for module_info in pkgutil.iter_modules([str(sub_path)]):
                module_name = f"{sub_package_name}.{module_info.name}"
                try:
                    module = importlib.import_module(module_name)
                except Exception as e:
                    logger.warning("导入模块 %s 失败: %s", module_name, e)
                    continue

                # 查找模块中所有 PluginBase 的非抽象子类
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, PluginBase)
                        and obj is not PluginBase
                        and not inspect.isabstract(obj)
                    ):
                        discovered.append(obj)
                        logger.debug("发现插件类: %s (来自 %s)", obj.__name__, module_name)

        logger.info("共发现 %d 个插件类", len(discovered))
        return discovered

    def filter_enabled(
        self,
        plugins: list[type[PluginBase]],
        enabled_patterns: Optional[list[str]] = None,
    ) -> list[type[PluginBase]]:
        """根据配置的通配符模式过滤插件

        使用 fnmatch 将插件名称与模式列表进行匹配。
        若未提供模式列表或列表为空，则返回所有插件。

        Args:
            plugins: 待过滤的插件类列表
            enabled_patterns: 启用模式列表，如 ["message.*", "channel.mirror"]

        Returns:
            匹配模式的插件类列表

        Examples:
            >>> loader.filter_enabled(plugins, ["message.*"])
            # 返回 name 以 "message." 开头的所有插件
        """
        if not enabled_patterns:
            logger.debug("未设置启用模式，返回所有插件")
            return list(plugins)

        filtered: list[type[PluginBase]] = []
        for plugin_cls in plugins:
            # 通过临时访问类属性获取插件名称（name 是抽象属性，需在实例上访问）
            # 但作为约定，插件类应定义类级别的 name 属性或通过属性方法返回固定值
            try:
                plugin_name = self._get_plugin_name(plugin_cls)
            except Exception:
                logger.warning("无法获取插件 %s 的名称，跳过过滤", plugin_cls.__name__)
                continue

            if any(fnmatch(plugin_name, pattern) for pattern in enabled_patterns):
                filtered.append(plugin_cls)
                logger.debug("插件 %s 匹配启用模式", plugin_name)
            else:
                logger.debug("插件 %s 不匹配任何启用模式，已跳过", plugin_name)

        logger.info("过滤后保留 %d / %d 个插件", len(filtered), len(plugins))
        return filtered

    @staticmethod
    def _get_plugin_name(plugin_cls: type[PluginBase]) -> str:
        """尝试获取插件类的名称

        优先检查类上是否定义了 'name' 类属性，
        若未定义则回退使用类名的小写形式。

        Args:
            plugin_cls: 插件类

        Returns:
            插件名称字符串
        """
        # 检查类字典中是否有直接定义的 name 属性（非实例属性）
        for cls in plugin_cls.__mro__:
            if "name" in cls.__dict__ and isinstance(cls.__dict__["name"], property):
                # 无法在不实例化的情况下调用 property，回退使用类名
                break
            if "name" in cls.__dict__ and isinstance(cls.__dict__["name"], str):
                return cls.__dict__["name"]

        # 回退：使用类名转为小写并以点号分隔模块路径
        module = plugin_cls.__module__
        parts = module.split(".")
        # 从 src.plugins.message.sender 提取 message.sender
        if len(parts) >= 4 and parts[0] == "src" and parts[1] == "plugins":
            return ".".join(parts[2:])
        return plugin_cls.__name__.lower()
