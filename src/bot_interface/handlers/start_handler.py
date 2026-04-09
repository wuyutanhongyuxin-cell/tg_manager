"""启动和帮助命令处理器

处理 /start、/help、/status 等基础命令，
提供 Bot 的入口菜单和帮助信息。
"""

import logging
from typing import Any

from src.bot_interface.menu_builder import MenuBuilder
from src.core.constants import APP_NAME, VERSION

logger = logging.getLogger(__name__)


class StartHandler:
    """处理 /start 和 /help 命令

    提供 Bot 的基础交互入口，包括欢迎消息、
    帮助文档和系统状态查询。
    """

    def __init__(self, config: Any, plugin_manager: Any = None) -> None:
        """初始化处理器

        Args:
            config: 应用配置实例
            plugin_manager: 插件管理器实例，可选
        """
        self._config = config
        self._plugin_manager = plugin_manager

    async def handle_start(self, event: Any) -> None:
        """处理 /start 命令

        向用户发送欢迎消息和主菜单按钮。

        Args:
            event: Telethon 消息事件
        """
        welcome = (
            f"🤖 **{APP_NAME} v{VERSION}**\n\n"
            f"全功能 Telegram 管理工具\n\n"
            f"点击下方按钮开始使用，或输入 /help 查看帮助。"
        )
        buttons = MenuBuilder.main_menu()
        await event.reply(welcome, buttons=buttons)
        logger.info(f"用户 {event.sender_id} 启动了 Bot")

    async def handle_help(self, event: Any) -> None:
        """处理 /help 命令

        向用户发送命令列表和使用说明。

        Args:
            event: Telethon 消息事件
        """
        help_text = (
            f"📖 **{APP_NAME} 帮助**\n\n"
            "**可用命令：**\n"
            "/start - 打开主菜单\n"
            "/help - 显示此帮助\n"
            "/status - 查看系统状态\n"
            "/plugins - 查看插件列表\n"
            "\n**使用方式：**\n"
            "通过主菜单的按钮导航各功能模块。"
        )
        await event.reply(help_text)

    async def handle_status(self, event: Any) -> None:
        """处理 /status 命令 - 显示系统状态

        展示当前版本、已加载插件数量和运行状态。

        Args:
            event: Telethon 消息事件
        """
        plugin_count = (
            len(self._plugin_manager.list_plugins())
            if self._plugin_manager
            else 0
        )
        status = (
            f"📊 **系统状态**\n\n"
            f"版本: v{VERSION}\n"
            f"已加载插件: {plugin_count}\n"
            f"状态: ✅ 运行中"
        )
        await event.reply(status)

    def register(self, command_router: Any) -> None:
        """将命令注册到路由器

        Args:
            command_router: CommandRouter 实例
        """
        command_router.register("start", self.handle_start, "打开主菜单")
        command_router.register("help", self.handle_help, "显示帮助")
        command_router.register("status", self.handle_status, "系统状态")
