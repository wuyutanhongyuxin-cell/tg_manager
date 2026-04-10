"""Config summary command handler."""

from __future__ import annotations

import logging
from typing import Any

from src.bot_interface.middlewares.throttle import throttle

logger = logging.getLogger(__name__)


class ConfigHandler:
    """Expose a safe configuration summary to the admin."""

    def __init__(self, config: Any) -> None:
        self._config = config
        self._admin_id = int(config.telegram.admin_user_id)

    async def _check_admin(self, event: Any) -> bool:
        if event.sender_id != self._admin_id:
            await event.reply("⛔ 无权限执行此操作")
            return False
        return True

    async def handle_config(self, event: Any) -> None:
        if not await self._check_admin(event):
            return

        cfg = self._config
        text = (
            "⚙️ **当前配置摘要**\n\n"
            f"数据库: {self._get_db_type(cfg)}\n"
            f"全局速率限制: {cfg.rate_limit.get('global_per_minute', 30)}/分钟\n"
            f"单聊天间隔: {cfg.rate_limit.get('per_chat_interval', 3)} 秒\n"
            f"每日加群: {cfg.rate_limit.get('join_per_day', 20)}\n"
            f"每日加人: {cfg.rate_limit.get('add_member_per_day', 50)}\n"
            f"默认 LLM Provider: {cfg.llm.get('default_provider', '未配置')}\n"
            f"启用插件模式: {cfg.plugins.get('enabled', ['*'])}\n"
            f"日志级别: {cfg.logging.get('level', 'INFO')}\n"
            f"文件日志: {'开启' if cfg.logging.get('file_enabled') else '关闭'}"
        )
        await event.reply(text)

    @staticmethod
    def _get_db_type(config: Any) -> str:
        url = config.database.get("url", "")
        if "sqlite" in url:
            return "SQLite"
        if "postgresql" in url:
            return "PostgreSQL"
        return "未知"

    def register(self, command_router: Any) -> None:
        command_router.register("config", throttle()(self.handle_config), "查看配置")
