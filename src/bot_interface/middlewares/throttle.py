"""命令节流中间件

防止用户频繁调用命令，通过记录每个用户的上次调用时间
来限制同一用户在指定时间窗口内的命令频率。
"""

import time
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


def throttle(seconds: float = 3.0) -> Callable:
    """装饰器：限制同一用户的命令频率

    在指定的时间窗口内，同一用户只能执行一次命令。
    如果调用过于频繁，将收到等待提示。

    Args:
        seconds: 两次调用之间的最小间隔秒数，默认 3.0 秒

    Returns:
        装饰器函数
    """
    _last_call: dict[int, float] = {}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(event: Any, *args: Any, **kwargs: Any) -> Any:
            user_id = event.sender_id
            now = time.time()
            last = _last_call.get(user_id, 0)

            if now - last < seconds:
                remaining = seconds - (now - last)
                await event.reply(f"请等待 {remaining:.1f} 秒后再试")
                return None

            _last_call[user_id] = now
            return await func(event, *args, **kwargs)

        return wrapper

    return decorator
