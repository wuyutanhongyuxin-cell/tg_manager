"""插件系统模块

提供插件抽象基类、自动发现加载器和生命周期管理器。
"""

from .plugin_base import PluginBase
from .plugin_loader import PluginLoader
from .plugin_manager import PluginManager

__all__ = ["PluginBase", "PluginLoader", "PluginManager"]
