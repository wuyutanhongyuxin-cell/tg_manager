"""消息记录 Repository

提供消息的存储、查询和批量操作。
"""

import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.message import TelegramMessage
from .base_repo import BaseRepository

logger = logging.getLogger(__name__)


class MessageRepository(BaseRepository[TelegramMessage]):
    """消息 CRUD 操作"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TelegramMessage)

    async def get_by_chat_and_msg_id(
        self, chat_id: int, message_id: int
    ) -> Optional[TelegramMessage]:
        """根据聊天 ID + 消息 ID 查询（唯一索引）"""
        stmt = select(TelegramMessage).where(
            TelegramMessage.chat_id == chat_id,
            TelegramMessage.message_id == message_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_chat(
        self, chat_id: int, limit: int = 100, offset: int = 0
    ) -> Sequence[TelegramMessage]:
        """获取某个聊天的消息列表（按时间倒序）"""
        stmt = (
            select(TelegramMessage)
            .where(TelegramMessage.chat_id == chat_id)
            .order_by(TelegramMessage.date.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def search_text(
        self, keyword: str, chat_id: Optional[int] = None, limit: int = 50
    ) -> Sequence[TelegramMessage]:
        """搜索包含关键词的消息

        Args:
            keyword: 搜索关键词
            chat_id: 限定聊天（空=全局搜索）
            limit: 结果数量上限
        """
        stmt = select(TelegramMessage).where(
            TelegramMessage.text.contains(keyword)
        )
        if chat_id is not None:
            stmt = stmt.where(TelegramMessage.chat_id == chat_id)
        stmt = stmt.order_by(TelegramMessage.date.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def upsert(self, **kwargs) -> TelegramMessage:
        """插入或更新消息（基于 chat_id + message_id 去重）

        使用数据库级别的 INSERT ... ON CONFLICT 保证原子性。
        自动检测方言（SQLite / PostgreSQL），避免竞态条件。
        """
        update_fields = {
            k: kwargs[k] for k in ("text", "views", "is_pinned", "raw_data") if k in kwargs
        }
        dialect = self._session.bind.dialect.name if self._session.bind else "sqlite"
        stmt = self._build_upsert(dialect, kwargs, update_fields)
        await self._session.execute(stmt)
        await self._session.flush()
        return await self.get_by_chat_and_msg_id(kwargs["chat_id"], kwargs["message_id"])

    @staticmethod
    def _build_upsert(dialect: str, values: dict, update_fields: dict):
        """根据方言构建原子 upsert 语句"""
        if dialect == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(TelegramMessage).values(**values)
        else:
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert
            stmt = sqlite_insert(TelegramMessage).values(**values)
        if update_fields:
            return stmt.on_conflict_do_update(
                index_elements=["chat_id", "message_id"], set_=update_fields,
            )
        return stmt.on_conflict_do_nothing(index_elements=["chat_id", "message_id"])

    async def get_forwarded(
        self, chat_id: int, limit: int = 50
    ) -> Sequence[TelegramMessage]:
        """获取某聊天中的转发消息"""
        stmt = (
            select(TelegramMessage)
            .where(
                TelegramMessage.chat_id == chat_id,
                TelegramMessage.is_forward.is_(True),
            )
            .order_by(TelegramMessage.date.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
