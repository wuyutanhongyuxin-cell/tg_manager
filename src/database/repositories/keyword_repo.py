"""关键词监控 Repository

提供监控关键词的 CRUD 操作（运行时通过 /keyword 命令调用）。
"""

import logging
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.monitor_keyword import MonitorKeyword
from .base_repo import BaseRepository

logger = logging.getLogger(__name__)


class KeywordRepository(BaseRepository[MonitorKeyword]):
    """监控关键词 CRUD 操作"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MonitorKeyword)

    async def get_enabled(self) -> Sequence[MonitorKeyword]:
        """获取所有启用的关键词（按创建时间排序）"""
        stmt = (
            select(MonitorKeyword)
            .where(MonitorKeyword.is_enabled.is_(True))
            .order_by(MonitorKeyword.created_at)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_keyword(self, keyword: str) -> Optional[MonitorKeyword]:
        """按关键词文本查询（大小写不敏感的精确匹配）"""
        stmt = select(MonitorKeyword).where(
            MonitorKeyword.keyword.ilike(keyword)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
