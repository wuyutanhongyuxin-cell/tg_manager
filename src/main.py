"""TG Manager 主入口

启动流程：
1. 加载配置（.env + config.yaml）
2. 初始化数据库
3. 创建事件总线和速率限制器
4. 启动双客户端（Userbot + Bot）
5. 注册 Bot 命令路由
6. 加载并启动所有插件
7. 运行直到收到停止信号
"""

import asyncio
import logging
import os
import signal
import sys

from src.core import Config, EventBus, RateLimiter, load_config
from src.core.constants import (
    APP_NAME,
    DEFAULT_CONFIG_PATH,
    DEFAULT_ENV_PATH,
    VERSION,
)
from src.database import DatabaseManager
from src.clients import DualClient
from src.llm import LLMManager
from src.plugins import PluginManager
from src.bot_interface import CommandRouter, CallbackRouter
from src.bot_interface.handlers.admin_handler import AdminHandler
from src.bot_interface.handlers.config_handler import ConfigHandler
from src.bot_interface.handlers.plugin_handler import PluginHandler
from src.bot_interface.handlers.start_handler import StartHandler
from src.bot_interface.handlers.summary_handler import SummaryHandler

logger = logging.getLogger(__name__)


def setup_logging(config: Config) -> None:
    """配置日志系统

    根据配置设置日志级别、格式，以及可选的文件输出。

    Args:
        config: 全局配置对象
    """
    log_cfg = config.logging
    level = log_cfg.get("level", "INFO")
    fmt = log_cfg.get("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format=fmt,
    )
    # 如果启用了文件日志，添加文件处理器
    if log_cfg.get("file_enabled", False):
        file_path = log_cfg.get("file_path", "logs/tg_manager.log")
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        fh = logging.FileHandler(file_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter(fmt))
        logging.getLogger().addHandler(fh)


async def main() -> None:
    """主函数，按顺序初始化所有组件并运行"""
    logger.info("=" * 40)
    logger.info(f"{APP_NAME} v{VERSION} 启动中...")
    logger.info("=" * 40)

    # 1. 加载配置
    config = load_config(DEFAULT_CONFIG_PATH, DEFAULT_ENV_PATH)
    setup_logging(config)
    logger.info("配置加载完成")

    # 2. 初始化数据库
    db = DatabaseManager(config)
    await db.init()
    logger.info("数据库初始化完成")

    # 3. 创建核心组件
    event_bus = EventBus()
    rate_limiter = RateLimiter(config.rate_limit)

    # 4. 初始化 LLM 管理器
    llm_manager = LLMManager(config)
    llm_manager.init()
    logger.info("LLM 管理器初始化完成")

    # 5. 启动双客户端
    client = DualClient(config, rate_limiter, event_bus)
    await client.start()
    logger.info("双客户端启动完成")

    # 6. 注册 Bot 命令路由
    command_router = CommandRouter(client.bot)
    callback_router = CallbackRouter(client.bot)

    # 7. 加载插件（传入 LLM 管理器供 AI 插件使用）
    plugin_manager = PluginManager(client, config, event_bus, db, llm=llm_manager)
    await plugin_manager.load_all()
    logger.info("插件加载完成")

    # 8. 注册所有命令处理器
    start_handler = StartHandler(config, plugin_manager)
    start_handler.register(command_router)

    admin_handler = AdminHandler(config, event_bus)
    admin_handler.register(command_router)

    plugin_handler = PluginHandler(config, plugin_manager)
    plugin_handler.register(command_router, callback_router)

    config_handler = ConfigHandler(config)
    config_handler.register(command_router)

    summary_handler = SummaryHandler(config, event_bus)
    summary_handler.register(command_router)

    # 注册菜单按钮 catch-all（功能模块尚在开发中）
    async def _menu_callback(event, data):
        await event.answer("该功能模块开发中，敬请期待")

    callback_router.register("menu_", _menu_callback)

    command_router.setup()
    callback_router.setup()

    logger.info(f"{APP_NAME} 已就绪，等待事件...")

    # 8. 保持运行，直到收到停止信号
    try:
        stop_event = asyncio.Event()

        # 在 Unix 系统上通过信号处理优雅关闭
        # Windows 上信号处理受限，依赖 KeyboardInterrupt
        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop_event.set)

        await stop_event.wait()
    except KeyboardInterrupt:
        logger.info("收到停止信号")
    finally:
        # 按逆序清理资源
        logger.info("正在关闭...")
        await plugin_manager.unload_all()
        await client.stop()
        await llm_manager.close()
        await db.close()
        logger.info(f"{APP_NAME} 已关闭")


def run() -> None:
    """程序入口点，启动异步主函数"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
