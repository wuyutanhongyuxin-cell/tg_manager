"""Bot 接口层

提供命令路由、回调路由和菜单构建等核心组件。
"""

from .command_router import CommandRouter
from .callback_router import CallbackRouter
from .menu_builder import MenuBuilder

__all__ = ["CommandRouter", "CallbackRouter", "MenuBuilder"]
