"""权限检查中间件

提供装饰器用于限制命令的访问权限，
确保敏感操作仅管理员可执行。
"""

import logging
from functools import wraps
from typing import Callable, Any

from src.core.config import Config

logger = logging.getLogger(__name__)


def admin_only(config: Config) -> Callable:
    """装饰器：仅允许管理员执行

    从配置中读取 admin_user_id，与事件发送者进行比对。
    非管理员用户将收到权限不足的提示。

    Args:
        config: 应用配置实例，包含管理员 ID

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(event: Any, *args: Any, **kwargs: Any) -> Any:
            sender_id = event.sender_id
            admin_id = int(config.telegram.admin_user_id)

            if sender_id != admin_id:
                await event.reply("⛔ 无权限执行此操作")
                logger.warning(f"未授权访问: user_id={sender_id}")
                return None

            return await func(event, *args, **kwargs)

        return wrapper

    return decorator
