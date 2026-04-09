"""配置查看命令处理器

提供 /config 命令查看当前系统配置摘要。
仅管理员可查看，且只显示非敏感信息。
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConfigHandler:
    """配置查看命令处理器（只读）"""

    def __init__(self, config: Any) -> None:
        """初始化处理器

        Args:
            config: 应用配置实例
        """
        self._config = config
        self._admin_id = int(config.telegram.admin_user_id)

    async def _check_admin(self, event: Any) -> bool:
        """检查发送者是否为管理员"""
        if event.sender_id != self._admin_id:
            await event.reply("⛔ 无权限执行此操作")
            return False
        return True

    async def handle_config(self, event: Any) -> None:
        """处理 /config 命令 — 显示配置摘要（隐藏敏感信息）"""
        if not await self._check_admin(event):
            return

        cfg = self._config
        # 构建安全的配置摘要（不展示 token、密钥、手机号）
        text = (
            "⚙️ **当前配置摘要**\n\n"
            f"**数据库:**\n"
            f"  类型: {self._get_db_type(cfg)}\n\n"
            f"**速率限制:**\n"
            f"  全局: {cfg.rate_limit.get('global_per_minute', 30)}/分钟\n"
            f"  单聊天间隔: {cfg.rate_limit.get('per_chat_interval', 3)}秒\n"
            f"  每日加群: {cfg.rate_limit.get('join_per_day', 20)}\n"
            f"  每日加人: {cfg.rate_limit.get('add_member_per_day', 50)}\n\n"
            f"**LLM:**\n"
            f"  默认模型: {cfg.llm.get('default_provider', '未配置')}\n\n"
            f"**插件:**\n"
            f"  启用模式: {cfg.plugins.get('enabled', ['*'])}\n\n"
            f"**日志:**\n"
            f"  级别: {cfg.logging.get('level', 'INFO')}\n"
            f"  文件输出: {'是' if cfg.logging.get('file_enabled') else '否'}"
        )
        await event.reply(text)

    @staticmethod
    def _get_db_type(config: Any) -> str:
        """从数据库 URL 推断类型（不暴露完整 URL）"""
        url = config.database.get("url", "")
        if "sqlite" in url:
            return "SQLite"
        if "postgresql" in url:
            return "PostgreSQL"
        return "未知"

    def register(self, command_router: Any) -> None:
        """注册命令到路由器"""
        command_router.register("config", self.handle_config, "查看配置")
