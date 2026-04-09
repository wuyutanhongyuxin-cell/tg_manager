"""自动回复规则 Repository

提供规则的 CRUD 和按优先级匹配查询。
"""

import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.rule import AutoReplyRule
from .base_repo import BaseRepository

logger = logging.getLogger(__name__)


class RuleRepository(BaseRepository[AutoReplyRule]):
    """自动回复规则 CRUD 操作"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AutoReplyRule)

    async def get_enabled_rules(
        self, chat_id: Optional[int] = None
    ) -> Sequence[AutoReplyRule]:
        """获取已启用的规则（按优先级降序）

        返回全局规则 + 指定聊天的规则，按优先级排序。

        Args:
            chat_id: 聊天 ID，空则只返回全局规则
        """
        stmt = select(AutoReplyRule).where(
            AutoReplyRule.is_enabled.is_(True)
        )
        if chat_id is not None:
            # 返回全局规则（chat_id 为空）和指定聊天的规则
            stmt = stmt.where(
                (AutoReplyRule.chat_id.is_(None))
                | (AutoReplyRule.chat_id == chat_id)
            )
        else:
            stmt = stmt.where(AutoReplyRule.chat_id.is_(None))

        stmt = stmt.order_by(AutoReplyRule.priority.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Optional[AutoReplyRule]:
        """根据规则名称查询"""
        stmt = select(AutoReplyRule).where(AutoReplyRule.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def toggle(self, rule_id: int, enabled: bool) -> Optional[AutoReplyRule]:
        """启用/禁用规则"""
        rule = await self.get_by_id(rule_id)
        if rule:
            return await self.update(rule, is_enabled=enabled)
        return None
