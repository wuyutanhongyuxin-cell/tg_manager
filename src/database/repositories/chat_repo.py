"""聊天记录 Repository

提供聊天信息的存储、查询和状态管理。
"""

import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.chat import Chat
from .base_repo import BaseRepository

logger = logging.getLogger(__name__)


class ChatRepository(BaseRepository[Chat]):
    """聊天 CRUD 操作"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Chat)

    async def get_by_chat_id(self, chat_id: int) -> Optional[Chat]:
        """根据 Telegram 聊天 ID 查询"""
        stmt = select(Chat).where(Chat.chat_id == chat_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, chat_id: int, **defaults) -> Chat:
        """获取聊天记录，不存在则创建

        Args:
            chat_id: Telegram 聊天 ID
            **defaults: 创建时使用的默认字段值
        """
        existing = await self.get_by_chat_id(chat_id)
        if existing:
            return existing
        return await self.create(chat_id=chat_id, **defaults)

    async def get_monitored(self) -> Sequence[Chat]:
        """获取所有启用监控的聊天"""
        stmt = select(Chat).where(Chat.is_monitored.is_(True))
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_mirror_sources(self) -> Sequence[Chat]:
        """获取所有镜像源聊天"""
        stmt = select(Chat).where(Chat.is_mirror_source.is_(True))
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_mirror_targets(self) -> Sequence[Chat]:
        """获取所有镜像目标聊天"""
        stmt = select(Chat).where(Chat.is_mirror_target.is_(True))
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def set_monitored(self, chat_id: int, enabled: bool) -> Optional[Chat]:
        """设置聊天的监控状态"""
        chat = await self.get_by_chat_id(chat_id)
        if chat:
            return await self.update(chat, is_monitored=enabled)
        return None
