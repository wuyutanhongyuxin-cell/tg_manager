"""用户 Repository

提供用户的查询、警告计数、封禁状态管理。
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from .base_repo import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """用户 CRUD 操作"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_user_id(self, user_id: int) -> Optional[User]:
        """根据 Telegram 用户 ID 查询"""
        stmt = select(User).where(User.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: int, **kwargs) -> User:
        """获取或创建用户记录"""
        user = await self.get_by_user_id(user_id)
        if user:
            return user
        return await self.create(user_id=user_id, **kwargs)

    async def increment_warn(self, user_id: int) -> int:
        """增加用户警告计数并返回当前计数"""
        user = await self.get_or_create(user_id)
        user.warn_count = (user.warn_count or 0) + 1
        await self._session.flush()
        return user.warn_count

    async def update_ban_status(
        self, user_id: int, is_banned: bool = False, ban_reason: str = ""
    ) -> None:
        """更新用户封禁状态"""
        user = await self.get_or_create(user_id)
        user.is_banned = is_banned
        user.ban_reason = ban_reason
        await self._session.flush()

    async def get_banned_users(self, limit: int = 100) -> list[User]:
        """获取所有被封禁的用户"""
        stmt = (
            select(User)
            .where(User.is_banned.is_(True))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
