"""插件管理命令处理器

提供 /plugins 和 /reload 命令，通过 Bot 管理插件状态。
"""

import logging
from typing import Any

from src.bot_interface.menu_builder import MenuBuilder

logger = logging.getLogger(__name__)


class PluginHandler:
    """插件管理命令处理器"""

    def __init__(self, config: Any, plugin_manager: Any) -> None:
        """初始化处理器

        Args:
            config: 应用配置实例
            plugin_manager: 插件管理器实例
        """
        self._config = config
        self._pm = plugin_manager
        self._admin_id = int(config.telegram.admin_user_id)

    async def _check_admin(self, event: Any) -> bool:
        """检查发送者是否为管理员"""
        if event.sender_id != self._admin_id:
            await event.reply("⛔ 无权限执行此操作")
            return False
        return True

    async def handle_plugins(self, event: Any) -> None:
        """处理 /plugins 命令 — 列出所有已加载插件"""
        if not await self._check_admin(event):
            return

        plugins = self._pm.list_plugins()
        if not plugins:
            await event.reply("📦 当前无已加载插件")
            return

        text = "📦 **已加载插件**\n\n"
        for i, p in enumerate(plugins, 1):
            text += f"{i}. **{p['name']}**\n   {p['description']}\n"

        buttons = MenuBuilder.plugin_list(plugins)
        await event.reply(text, buttons=buttons)

    async def handle_reload(self, event: Any) -> None:
        """处理 /reload <plugin_name> 命令 — 重载插件"""
        if not await self._check_admin(event):
            return

        parts = event.raw_text.split()
        if len(parts) < 2:
            await event.reply("用法: /reload <插件名>\n例: /reload message.sender")
            return

        plugin_name = parts[1]
        try:
            await self._pm.reload_plugin(plugin_name)
            await event.reply(f"✅ 插件 {plugin_name} 已重载")
        except Exception as e:
            logger.error("插件重载失败: %s - %s", plugin_name, e, exc_info=True)
            await event.reply(f"❌ 重载失败，请查看日志")

    async def handle_plugin_callback(self, event: Any, data: str) -> None:
        """处理插件按钮回调（需管理员权限）"""
        if event.sender_id != self._admin_id:
            await event.answer("⛔ 无权限")
            return
        plugin_name = data.removeprefix("plugin_")
        plugin = self._pm.get_plugin(plugin_name)
        if plugin:
            info = f"📦 **{plugin.name}**\n\n{plugin.description}"
            await event.edit(info, buttons=MenuBuilder.back_button("settings"))
        else:
            await event.answer(f"插件 {plugin_name} 未找到")

    def register(self, command_router: Any, callback_router: Any = None) -> None:
        """注册命令和回调处理器"""
        command_router.register("plugins", self.handle_plugins, "插件列表")
        command_router.register("reload", self.handle_reload, "重载插件")
        if callback_router:
            callback_router.register("plugin_", self.handle_plugin_callback)
