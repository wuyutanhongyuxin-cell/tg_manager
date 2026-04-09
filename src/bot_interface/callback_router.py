"""InlineKeyboard 回调路由

负责注册和分发 InlineKeyboard 按钮的回调查询，
通过前缀匹配将回调数据路由到对应的处理器。
"""

import logging
from telethon import events
from typing import Callable, Any

logger = logging.getLogger(__name__)


class CallbackRouter:
    """注册和分发 InlineKeyboard 回调

    通过回调数据的前缀匹配，将按钮点击事件
    路由到对应的处理函数。
    """

    def __init__(self, bot_client: Any) -> None:
        """初始化回调路由器

        Args:
            bot_client: BotClient 实例，提供 client 属性用于事件绑定
        """
        self._bot = bot_client
        self._handlers: dict[str, Callable] = {}  # prefix -> handler

    def register(self, prefix: str, handler: Callable) -> None:
        """注册回调处理器

        Args:
            prefix: 回调数据前缀（如 "plugin_"），用于匹配路由
            handler: async 处理函数，接收 (event, data) 参数
        """
        self._handlers[prefix] = handler

    def setup(self) -> None:
        """绑定统一的回调分发器到 Bot 客户端

        创建一个统一的 CallbackQuery 事件处理器，
        根据回调数据前缀将事件分发到对应的处理函数。
        必须在所有回调处理器注册完成后调用。
        """

        @self._bot.client.on(events.CallbackQuery)
        async def callback_dispatcher(event: Any) -> None:
            """统一回调分发器"""
            data = event.data.decode("utf-8", errors="replace") if event.data else ""

            # 按前缀匹配，找到对应的处理器
            for prefix, handler in self._handlers.items():
                if data.startswith(prefix):
                    try:
                        await handler(event, data)
                    except Exception as e:
                        logger.error(f"回调处理失败: {prefix} - {e}")
                        await event.answer("处理失败，请重试")
                    return

            logger.warning(f"未匹配的回调: {data}")
