"""数据库 Repository 层

提供所有模型的 CRUD 操作封装。
业务代码通过 Repository 访问数据库，不直接写 SQL。
"""

from .base_repo import BaseRepository
from .chat_repo import ChatRepository
from .forward_rule_repo import ForwardRuleRepository
from .keyword_repo import KeywordRepository
from .message_repo import MessageRepository
from .rule_repo import RuleRepository
from .schedule_repo import ScheduleRepository
from .user_repo import UserRepository

__all__ = [
    "BaseRepository",
    "ChatRepository",
    "ForwardRuleRepository",
    "KeywordRepository",
    "MessageRepository",
    "RuleRepository",
    "ScheduleRepository",
    "UserRepository",
]
