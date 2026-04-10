"""Plugin management command handlers."""

from __future__ import annotations

import logging
from typing import Any

from src.bot_interface.menu_builder import MenuBuilder
from src.bot_interface.middlewares.throttle import throttle

logger = logging.getLogger(__name__)


class PluginHandler:
    """Handle plugin inspection and reload commands."""

    def __init__(self, config: Any, plugin_manager: Any) -> None:
        self._config = config
        self._pm = plugin_manager
        self._admin_id = int(config.telegram.admin_user_id)

    async def _check_admin(self, event: Any) -> bool:
        if event.sender_id != self._admin_id:
            await event.reply("⛔ 无权限执行此操作")
            return False
        return True

    async def handle_plugins(self, event: Any) -> None:
        if not await self._check_admin(event):
            return

        plugins = self._pm.list_plugins()
        if not plugins:
            await event.reply("📦 当前没有已加载插件")
            return

        lines = ["📦 **已加载插件**", ""]
        for index, plugin in enumerate(plugins, start=1):
            lines.append(f"{index}. **{plugin['name']}**")
            lines.append(plugin["description"])
            lines.append("")

        await event.reply(
            "\n".join(lines).strip(),
            buttons=MenuBuilder.plugin_list(plugins),
        )

    async def handle_reload(self, event: Any) -> None:
        if not await self._check_admin(event):
            return

        parts = event.raw_text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await event.reply("用法: /reload <插件名>\n例如: /reload message.sender")
            return

        plugin_name = parts[1].strip()
        try:
            await self._pm.reload_plugin(plugin_name)
            await event.reply(f"✅ 插件 {plugin_name} 已重载")
        except Exception as exc:
            logger.error("failed to reload plugin %s: %s", plugin_name, exc, exc_info=True)
            await event.reply("❌ 重载失败，请查看日志")

    async def handle_plugin_callback(self, event: Any, data: str) -> None:
        if event.sender_id != self._admin_id:
            await event.answer("⛔ 无权限")
            return

        plugin_name = data.removeprefix("plugin_")
        plugin = self._pm.get_plugin(plugin_name)
        if not plugin:
            await event.answer(f"插件 {plugin_name} 未找到")
            return

        text = f"📦 **{plugin.name}**\n\n{plugin.description}"
        await event.edit(text, buttons=[MenuBuilder.back_button("main")])

    def register(self, command_router: Any, callback_router: Any = None) -> None:
        command_router.register("plugins", throttle()(self.handle_plugins), "插件列表")
        command_router.register("reload", throttle()(self.handle_reload), "重载插件")
        if callback_router:
            callback_router.register("plugin_", self.handle_plugin_callback)
