"""数据库 ORM 模型

导入所有模型，确保 Base.metadata 包含全部表定义。
DatabaseManager.init() 中的 create_all 依赖这些导入。
"""

from .chat import Chat
from .forward_rule import ForwardRule
from .message import TelegramMessage
from .monitor_keyword import MonitorKeyword
from .rule import AutoReplyRule
from .scheduled_job import ScheduledJob
from .user import User

__all__ = [
    "Chat",
    "ForwardRule",
    "TelegramMessage",
    "MonitorKeyword",
    "AutoReplyRule",
    "ScheduledJob",
    "User",
]
