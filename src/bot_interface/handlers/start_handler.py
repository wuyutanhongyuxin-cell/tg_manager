"""Handlers for public bot entry commands."""

from __future__ import annotations

import logging
from typing import Any

from src.bot_interface.menu_builder import MenuBuilder
from src.bot_interface.middlewares.auth import admin_only
from src.bot_interface.middlewares.throttle import throttle
from src.core.constants import APP_NAME, VERSION

logger = logging.getLogger(__name__)


class StartHandler:
    """Handle `/start`, `/help`, and `/status`."""

    def __init__(self, config: Any, plugin_manager: Any = None) -> None:
        self._config = config
        self._plugin_manager = plugin_manager

    async def handle_start(self, event: Any) -> None:
        welcome = (
            f"🤖 **{APP_NAME} v{VERSION}**\n\n"
            "Telegram 管理工具入口。\n\n"
            "可通过下方菜单查看已接通的模块，或使用 /help 查看命令。"
        )
        await event.reply(welcome, buttons=MenuBuilder.main_menu())
        logger.info("user %s opened the main menu", event.sender_id)

    async def handle_help(self, event: Any) -> None:
        help_text = (
            f"📘 **{APP_NAME} 帮助**\n\n"
            "/start - 打开主菜单\n"
            "/help - 查看帮助\n"
            "/status - 查看系统状态（管理员）\n"
            "/plugins - 查看已加载插件（管理员）\n"
            "/config - 查看配置摘要（管理员）\n"
            "/llm [name] - 查看/切换 LLM Provider（管理员）\n"
            "/summarize [N] [chat_id] - 总结指定/当前聊天的最近 N 条（管理员）\n"
            "/ask <问题> - 向 AI 提问（管理员）\n"
            "/url <链接> - 提取并总结网页内容（管理员）\n"
            "/schedule ... - 管理定时任务（管理员）\n"
            "/keyword list|add|remove - 关键词监控管理（管理员）"
        )
        await event.reply(help_text)

    async def handle_status(self, event: Any) -> None:
        plugin_count = len(self._plugin_manager.list_plugins()) if self._plugin_manager else 0
        status = (
            "📊 **系统状态**\n\n"
            f"版本: v{VERSION}\n"
            f"已加载插件: {plugin_count}\n"
            "状态: 运行中"
        )
        await event.reply(status)

    def register(self, command_router: Any) -> None:
        command_router.register("start", throttle()(self.handle_start), "打开主菜单")
        command_router.register("help", throttle()(self.handle_help), "显示帮助")
        command_router.register(
            "status",
            admin_only(self._config)(throttle()(self.handle_status)),
            "系统状态",
        )
