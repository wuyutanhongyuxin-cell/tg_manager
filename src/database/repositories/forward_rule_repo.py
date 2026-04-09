"""转发规则 Repository

提供转发规则的 CRUD 和按源聊天查询。
"""

import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.forward_rule import ForwardRule
from .base_repo import BaseRepository

logger = logging.getLogger(__name__)


class ForwardRuleRepository(BaseRepository[ForwardRule]):
    """转发规则 CRUD 操作"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ForwardRule)

    async def get_by_source(
        self, source_chat_id: int
    ) -> Sequence[ForwardRule]:
        """获取某个源聊天的所有已启用转发规则"""
        stmt = (
            select(ForwardRule)
            .where(
                ForwardRule.source_chat_id == source_chat_id,
                ForwardRule.is_enabled.is_(True),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_enabled(self) -> Sequence[ForwardRule]:
        """获取所有已启用的转发规则"""
        stmt = select(ForwardRule).where(
            ForwardRule.is_enabled.is_(True)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Optional[ForwardRule]:
        """根据规则名称查询"""
        stmt = select(ForwardRule).where(ForwardRule.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def toggle(self, rule_id: int, enabled: bool) -> Optional[ForwardRule]:
        """启用/禁用转发规则"""
        rule = await self.get_by_id(rule_id)
        if rule:
            return await self.update(rule, is_enabled=enabled)
        return None
