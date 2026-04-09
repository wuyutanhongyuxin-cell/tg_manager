"""首次登录获取 Telethon session

使用方式: python scripts/setup_session.py

交互式引导用户输入手机号和验证码，
分别生成 Userbot 和 Bot 的 session 文件。
"""

import asyncio
import os
import sys

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient

from src.core import load_config
from src.core.constants import DEFAULT_CONFIG_PATH, DEFAULT_ENV_PATH


async def setup_userbot(config) -> None:
    """设置 Userbot session

    通过交互式登录获取用户账号的 session 文件。

    Args:
        config: 全局配置对象
    """
    print("--- Userbot 登录 ---")
    session_path = os.path.join(
        config.telegram.session_dir,
        config.telegram.userbot_session,
    )

    client = TelegramClient(
        session_path,
        int(config.telegram.api_id),
        config.telegram.api_hash,
    )

    await client.start()
    me = await client.get_me()
    print(f"Userbot 登录成功: {me.first_name} (ID: {me.id})")
    await client.disconnect()


async def setup_bot(config) -> None:
    """设置 Bot session

    使用 Bot Token 登录并生成 session 文件。

    Args:
        config: 全局配置对象
    """
    print("\n--- Bot 登录 ---")
    session_path = os.path.join(
        config.telegram.session_dir,
        config.telegram.bot_session,
    )

    bot = TelegramClient(
        session_path,
        int(config.telegram.api_id),
        config.telegram.api_hash,
    )

    await bot.start(bot_token=config.telegram.bot_token)
    bot_me = await bot.get_me()
    print(f"Bot 登录成功: @{bot_me.username} (ID: {bot_me.id})")
    await bot.disconnect()


async def main() -> None:
    """主流程：加载配置并依次设置 Userbot 和 Bot session"""
    config = load_config(DEFAULT_CONFIG_PATH, DEFAULT_ENV_PATH)

    # 确保 session 目录存在
    session_dir = config.telegram.session_dir
    os.makedirs(session_dir, exist_ok=True)

    print("=== TG Manager Session 设置 ===\n")

    await setup_userbot(config)
    await setup_bot(config)

    print("\nSession 设置完成！可以启动 TG Manager 了。")


if __name__ == "__main__":
    asyncio.run(main())
