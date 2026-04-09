"""通用 Repository 基类

提供 CRUD 基础操作，所有具体 Repository 继承此类。
业务代码通过 Repository 访问数据库，不直接写 SQL。
"""

import logging
from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# 泛型类型变量，代表具体的 ORM 模型类
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """通用 CRUD Repository

    Args:
        session: 异步数据库会话
        model: ORM 模型类
    """

    def __init__(self, session: AsyncSession, model: Type[T]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, id: int) -> Optional[T]:
        """根据主键 ID 查询单条记录"""
        return await self._session.get(self._model, id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[T]:
        """查询全部记录（分页）"""
        stmt = select(self._model).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create(self, **kwargs: Any) -> T:
        """创建一条新记录

        Args:
            **kwargs: 模型字段名和值

        Returns:
            创建的模型实例
        """
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def update(self, instance: T, **kwargs: Any) -> T:
        """更新记录的指定字段

        Args:
            instance: 要更新的模型实例
            **kwargs: 需要更新的字段名和新值
        """
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self._session.flush()
        return instance

    async def delete(self, instance: T) -> None:
        """删除一条记录"""
        await self._session.delete(instance)
        await self._session.flush()

    async def count(self) -> int:
        """统计记录总数"""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self._model)
        result = await self._session.execute(stmt)
        return result.scalar_one()
