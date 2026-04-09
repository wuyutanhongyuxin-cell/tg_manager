"""SQLAlchemy 声明式基类

提供所有 ORM 模型共享的基类，统一元数据管理。
"""

import logging

from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类

    所有数据库模型都应继承此类，以确保共享同一个 MetaData 实例，
    从而支持统一的表创建和迁移操作。
    """

    pass
