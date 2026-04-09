"""定时任务 Repository

提供定时任务的 CRUD 和状态更新操作。
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.scheduled_job import ScheduledJob
from .base_repo import BaseRepository

logger = logging.getLogger(__name__)


class ScheduleRepository(BaseRepository[ScheduledJob]):
    """定时任务 CRUD 操作"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ScheduledJob)

    async def get_enabled(self) -> Sequence[ScheduledJob]:
        """获取所有启用的定时任务"""
        stmt = (
            select(ScheduledJob)
            .where(ScheduledJob.is_enabled.is_(True))
            .order_by(ScheduledJob.created_at)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_chat(self, chat_id: int) -> Sequence[ScheduledJob]:
        """获取指定聊天的所有定时任务"""
        stmt = (
            select(ScheduledJob)
            .where(ScheduledJob.target_chat_id == chat_id)
            .order_by(ScheduledJob.created_at)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Optional[ScheduledJob]:
        """根据名称查找任务"""
        stmt = select(ScheduledJob).where(ScheduledJob.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_executed(self, job_id: int) -> None:
        """更新任务的执行记录（last_run_at + run_count）"""
        job = await self.get_by_id(job_id)
        if job:
            job.last_run_at = datetime.now(timezone.utc)
            job.run_count = (job.run_count or 0) + 1
            await self._session.flush()
