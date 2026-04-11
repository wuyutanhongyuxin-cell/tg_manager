"""Application entrypoint."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys

from src.bot_interface import CallbackRouter, CommandRouter
from src.bot_interface.handlers.admin_handler import AdminHandler
from src.bot_interface.handlers.config_handler import ConfigHandler
from src.bot_interface.handlers.llm_handler import LLMHandler
from src.bot_interface.handlers.plugin_handler import PluginHandler
from src.bot_interface.handlers.start_handler import StartHandler
from src.bot_interface.handlers.summary_handler import SummaryHandler
from src.bot_interface.menu_builder import MenuBuilder
from src.clients import DualClient
from src.core import Config, EventBus, RateLimiter, load_config
from src.core.constants import APP_NAME, DEFAULT_CONFIG_PATH, DEFAULT_ENV_PATH, VERSION
from src.database import DatabaseManager
from src.llm import LLMManager
from src.plugins import PluginManager

logger = logging.getLogger(__name__)


def setup_logging(config: Config) -> None:
    log_cfg = config.logging
    level = log_cfg.get("level", "INFO")
    fmt = log_cfg.get("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format=fmt,
    )

    if log_cfg.get("file_enabled", False):
        file_path = log_cfg.get("file_path", "logs/tg_manager.log")
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        handler = logging.FileHandler(file_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(fmt))
        logging.getLogger().addHandler(handler)


def _build_menu_pages() -> dict[str, str]:
    return {
        "message": "📨 **消息管理**\n\n已接通消息转发、去标记复制、消息入库与搜索/总结数据源。",
        "channel": "📢 **频道管理**\n\n已接通频道镜像与去标记复制链路，可通过转发规则控制同步目标。",
        "group": "👥 **群组管理**\n\n已接通 ban / mute / warn / kick 与欢迎消息能力，管理命令仅管理员可用。",
        "auto_reply": "🤖 **自动回复**\n\n已接通规则引擎与模板回复，适合关键词触发类场景。",
        "scheduler": "⏰ **定时任务**\n\n已接通 `/schedule list|add|remove`，底层由调度插件处理。",
        "ai_summary": "🧠 **AI 总结**\n\n已接通 `/summarize`、`/url`、`/ask`，聊天总结会优先使用数据库消息，缺失时回退实时拉取。",
        "monitor": "🚨 **监控告警**\n\n已接通关键词告警插件，可将命中结果推送给管理员。",
        "settings": "⚙️ **系统设置**\n\n可使用 `/plugins` 查看插件，`/reload <name>` 热重载插件，`/config` 查看配置摘要。",
    }


async def main() -> None:
    config = load_config(DEFAULT_CONFIG_PATH, DEFAULT_ENV_PATH)
    setup_logging(config)

    logger.info("=" * 40)
    logger.info("%s v%s starting", APP_NAME, VERSION)
    logger.info("=" * 40)

    db = DatabaseManager(config)
    await db.init()

    event_bus = EventBus()
    rate_limiter = RateLimiter(config.rate_limit)

    llm_manager = LLMManager(config)
    llm_manager.init()

    client = DualClient(config, rate_limiter, event_bus)
    await client.start()

    command_router = CommandRouter(client.bot)
    callback_router = CallbackRouter(client.bot)

    plugin_manager = PluginManager(client, config, event_bus, db, llm=llm_manager)
    await plugin_manager.load_all()

    StartHandler(config, plugin_manager).register(command_router)
    AdminHandler(config, event_bus).register(command_router)
    PluginHandler(config, plugin_manager).register(command_router, callback_router)
    ConfigHandler(config).register(command_router)
    SummaryHandler(config, event_bus).register(command_router)
    LLMHandler(config, llm_manager).register(command_router)

    menu_pages = _build_menu_pages()

    async def _menu_callback(event, data):
        menu_key = data.removeprefix("menu_")

        if menu_key == "main":
            await event.edit(
                f"🤖 **{APP_NAME} v{VERSION}**\n\n请选择一个已接通的功能模块。",
                buttons=MenuBuilder.main_menu(),
            )
            await event.answer()
            return

        content = menu_pages.get(menu_key)
        if not content:
            await event.answer("未识别的菜单项")
            return

        await event.edit(content, buttons=[MenuBuilder.back_button("main")])
        await event.answer()

    callback_router.register("menu_", _menu_callback)

    command_router.setup()
    callback_router.setup()

    logger.info("%s ready", APP_NAME)

    stop_event = asyncio.Event()
    try:
        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop_event.set)

        await stop_event.wait()
    except KeyboardInterrupt:
        logger.info("shutdown signal received")
    finally:
        logger.info("shutting down")
        await plugin_manager.unload_all()
        await client.stop()
        await llm_manager.close()
        await db.close()


def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
