"""Telegram 客户端封装模块。

提供 Userbot、Bot 和双客户端协调器。
"""

from .bot import BotClient
from .dual_client import DualClient
from .userbot import UserbotClient

__all__ = ["UserbotClient", "BotClient", "DualClient"]
