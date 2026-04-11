"""LLM provider 查看与切换命令处理器

支持 /llm 查看当前状态，/llm <name> 切换默认 provider。
"""

from __future__ import annotations

import logging
from typing import Any

from src.bot_interface.middlewares.throttle import throttle
from src.core.exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMHandler:
    """查看/切换 LLM 默认 provider（仅管理员可用）"""

    def __init__(self, config: Any, llm_manager: Any) -> None:
        self._config = config
        self._llm = llm_manager
        self._admin_id = int(config.telegram.admin_user_id)

    async def _check_admin(self, event: Any) -> bool:
        if event.sender_id != self._admin_id:
            await event.reply("⛔ 无权限执行此操作")
            return False
        return True

    async def handle_llm(self, event: Any) -> None:
        """分发 /llm 命令到查看或切换逻辑"""
        if not await self._check_admin(event):
            return

        parts = event.raw_text.split(maxsplit=1)
        target = parts[1].strip() if len(parts) > 1 else ""

        if not target:
            await self._show_status(event)
            return

        await self._switch(event, target)

    async def _show_status(self, event: Any) -> None:
        """显示当前默认 provider 和所有可用 provider 列表"""
        current = self._llm.get_current_name() or "（未配置）"
        available = self._llm.list_available()

        if not available:
            text = (
                "🤖 **LLM Provider 状态**\n\n"
                "⚠️ 当前未配置任何可用的 Provider。\n\n"
                "请在 .env 中设置以下任一变量后重启服务：\n"
                "`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / "
                "`GEMINI_API_KEY` / `DEEPSEEK_API_KEY` / `OLLAMA_BASE_URL`"
            )
        else:
            avail_str = ", ".join(f"`{n}`" for n in available)
            text = (
                "🤖 **LLM Provider 状态**\n\n"
                f"当前默认: `{current}`\n"
                f"可用 Provider: {avail_str}\n\n"
                "切换默认: `/llm <name>`（例如 `/llm deepseek`）"
            )
        await event.reply(text)

    async def _switch(self, event: Any, target: str) -> None:
        """切换默认 provider，失败时返回原因"""
        try:
            self._llm.switch_default(target)
        except LLMError as e:
            await event.reply(f"⚠️ 切换失败: {e}")
            return
        await event.reply(f"✅ 默认 LLM Provider 已切换为: `{target}`")

    def register(self, command_router: Any) -> None:
        command_router.register(
            "llm", throttle()(self.handle_llm), "查看/切换 LLM Provider"
        )
