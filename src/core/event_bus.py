"""
TG Manager 内部事件总线模块。

提供异步的发布/订阅机制，用于模块间解耦通信。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

from .constants import (
    EVENT_ERROR,
    EVENT_MESSAGE_RECEIVED,
    EVENT_MESSAGE_SENT,
    EVENT_PLUGIN_LOADED,
)

logger = logging.getLogger(__name__)

# 异步事件处理器类型
AsyncHandler = Callable[..., Coroutine[Any, Any, None]]

# 内置事件列表
BUILT_IN_EVENTS: list[str] = [
    EVENT_MESSAGE_RECEIVED,
    EVENT_MESSAGE_SENT,
    EVENT_PLUGIN_LOADED,
    EVENT_ERROR,
]


class EventBus:
    """异步事件总线，支持发布/订阅模式。

    所有处理器必须是异步可调用对象，事件触发时并发调用所有已注册的处理器。
    """

    def __init__(self) -> None:
        """初始化事件总线，创建内置事件的空处理器列表。"""
        self._handlers: dict[str, list[AsyncHandler]] = {}
        self._lock = asyncio.Lock()

        # 预注册内置事件
        for event in BUILT_IN_EVENTS:
            self._handlers[event] = []

        logger.debug("事件总线已初始化，内置事件: %s", BUILT_IN_EVENTS)

    async def subscribe(self, event_name: str, handler: AsyncHandler) -> None:
        """订阅事件，注册异步处理器。

        Args:
            event_name: 事件名称。
            handler: 异步事件处理器。
        """
        async with self._lock:
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            if handler not in self._handlers[event_name]:
                self._handlers[event_name].append(handler)
                logger.debug(
                    "已订阅事件 '%s'，处理器: %s", event_name, handler.__name__
                )

    async def unsubscribe(self, event_name: str, handler: AsyncHandler) -> None:
        """取消订阅事件，移除指定处理器。

        Args:
            event_name: 事件名称。
            handler: 要移除的异步事件处理器。
        """
        async with self._lock:
            if event_name in self._handlers:
                try:
                    self._handlers[event_name].remove(handler)
                    logger.debug(
                        "已取消订阅事件 '%s'，处理器: %s",
                        event_name,
                        handler.__name__,
                    )
                except ValueError:
                    logger.warning(
                        "处理器 %s 未在事件 '%s' 中注册",
                        handler.__name__,
                        event_name,
                    )

    async def emit(self, event_name: str, **kwargs: Any) -> None:
        """触发事件，同步 await 所有已注册处理器（非 fire-and-forget）。

        注意：此方法会等待所有处理器执行完成（通过 asyncio.gather），
        但 _safe_call 会吞掉处理器异常（仅记录日志），因此调用方
        无法得知处理器是否执行成功。这是有意设计：保证事件处理不会
        因单个处理器失败而中断其他处理器或调用方的流程。

        Args:
            event_name: 事件名称。
            **kwargs: 传递给处理器的关键字参数。
        """
        async with self._lock:
            handlers = list(self._handlers.get(event_name, []))

        if not handlers:
            logger.debug("事件 '%s' 无处理器，跳过", event_name)
            return

        logger.debug(
            "触发事件 '%s'，处理器数量: %d，参数: %s",
            event_name,
            len(handlers),
            list(kwargs.keys()),
        )

        tasks = [self._safe_call(handler, event_name, **kwargs) for handler in handlers]
        await asyncio.gather(*tasks)

    @staticmethod
    async def _safe_call(
        handler: AsyncHandler, event_name: str, **kwargs: Any
    ) -> None:
        """安全调用处理器，捕获并记录异常。

        Args:
            handler: 异步事件处理器。
            event_name: 事件名称（用于日志）。
            **kwargs: 传递给处理器的关键字参数。
        """
        try:
            await handler(**kwargs)
        except Exception:
            logger.exception(
                "事件 '%s' 的处理器 %s 执行异常", event_name, handler.__name__
            )

    def has_handlers(self, event_name: str) -> bool:
        """检查指定事件是否有已注册的处理器。

        Args:
            event_name: 事件名称。

        Returns:
            如果有处理器返回 True，否则返回 False。
        """
        return bool(self._handlers.get(event_name))
