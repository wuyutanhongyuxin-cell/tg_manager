"""Cron 定时消息发送插件 — APScheduler 驱动，任务持久化到数据库。"""

from __future__ import annotations

from typing import Any

from src.core.exceptions import PluginError
from src.database.repositories.schedule_repo import ScheduleRepository
from src.plugins.plugin_base import PluginBase


class CronSenderPlugin(PluginBase):
    """Cron 定时发送插件 — APScheduler 驱动的定时消息"""

    @property
    def name(self) -> str:
        return "scheduler.cron_sender"

    @property
    def description(self) -> str:
        return "Cron 定时消息发送，支持 cron 表达式"

    async def setup(self) -> None:
        """初始化调度器并加载数据库中的任务"""
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        cfg = self.get_plugin_config()
        self._timezone = cfg.get("timezone", "Asia/Shanghai")
        self._CronTrigger = CronTrigger

        # 创建异步调度器
        self._scheduler = AsyncIOScheduler(timezone=self._timezone)
        self._scheduler.start()

        # 从数据库加载已有任务
        await self._load_jobs_from_db()

        # 订阅管理事件
        await self.event_bus.subscribe("schedule_add", self._handle_add)
        await self.event_bus.subscribe("schedule_remove", self._handle_remove)
        await self.event_bus.subscribe("schedule_list", self._handle_list)
        self.logger.info("定时发送插件已启动，时区: %s", self._timezone)

    async def teardown(self) -> None:
        """停止调度器并取消事件订阅"""
        if hasattr(self, "_scheduler") and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        await self.event_bus.unsubscribe("schedule_add", self._handle_add)
        await self.event_bus.unsubscribe("schedule_remove", self._handle_remove)
        await self.event_bus.unsubscribe("schedule_list", self._handle_list)

    async def _load_jobs_from_db(self) -> None:
        """从数据库加载所有启用的定时任务"""
        session = self.db.get_session()
        async with session:
            repo = ScheduleRepository(session)
            jobs = await repo.get_enabled()

        loaded = 0
        for job in jobs:
            try:
                self._add_scheduler_job(job.id, job.cron_expr, job.target_chat_id, job.message_text)
                loaded += 1
            except Exception as e:
                self.logger.warning("加载任务 '%s' 失败: %s", job.name, e)
        self.logger.info("从数据库加载了 %d 个定时任务", loaded)

    def _add_scheduler_job(
        self, job_id: int, cron_expr: str, chat_id: int, text: str
    ) -> None:
        """向 APScheduler 添加一个 cron 任务"""
        # 解析 cron 表达式（分 时 日 月 周）
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise PluginError(f"无效 cron 表达式: '{cron_expr}'（需要 5 个字段）")

        trigger = self._CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            timezone=self._timezone,
        )
        self._scheduler.add_job(
            self._execute_send,
            trigger=trigger,
            args=[job_id, chat_id, text],
            id=f"cron_{job_id}",
            replace_existing=True,
        )

    async def _execute_send(self, job_id: int, chat_id: int, text: str) -> None:
        """执行定时发送（APScheduler 回调）"""
        try:
            await self.client.send_message(chat_id, text)
            # 更新执行记录
            session = self.db.get_session()
            async with session:
                async with session.begin():
                    repo = ScheduleRepository(session)
                    await repo.mark_executed(job_id)
            self.logger.info("定时消息已发送: job=%d, chat=%d", job_id, chat_id)
        except Exception as e:
            self.logger.error("定时发送失败: job=%d, %s", job_id, e)

    async def _handle_add(self, **kwargs: Any) -> None:
        """处理添加定时任务事件"""
        name = kwargs.get("name", "")
        cron_expr = kwargs.get("cron_expr", "")
        chat_id = kwargs.get("chat_id")
        text = kwargs.get("text", "")
        reply_to = kwargs.get("reply_to_chat")
        created_by = kwargs.get("created_by")

        if not all([name, cron_expr, chat_id, text]):
            if reply_to:
                await self.client.send_message(reply_to, "缺少必要参数: name, cron_expr, chat_id, text")
            return

        try:
            # 保存到数据库
            session = self.db.get_session()
            async with session:
                async with session.begin():
                    repo = ScheduleRepository(session)
                    job = await repo.create(
                        name=name,
                        cron_expr=cron_expr,
                        target_chat_id=chat_id,
                        message_text=text,
                        timezone=self._timezone,
                        created_by=created_by,
                    )
                    job_id = job.id

            # 注册到调度器
            self._add_scheduler_job(job_id, cron_expr, chat_id, text)
            if reply_to:
                await self.client.send_message(
                    reply_to, f"✅ 定时任务已创建: {name}\nCron: {cron_expr}"
                )
        except Exception as e:
            if reply_to:
                await self.client.send_message(reply_to, f"创建失败: {e}")
            self.logger.error("添加定时任务失败: %s", e)

    async def _handle_remove(self, **kwargs: Any) -> None:
        """处理删除定时任务事件"""
        job_id = kwargs.get("job_id")
        reply_to = kwargs.get("reply_to_chat")
        if not job_id:
            return

        try:
            # 从调度器移除
            scheduler_id = f"cron_{job_id}"
            if self._scheduler.get_job(scheduler_id):
                self._scheduler.remove_job(scheduler_id)
            # 数据库标记禁用
            session = self.db.get_session()
            async with session:
                async with session.begin():
                    repo = ScheduleRepository(session)
                    job = await repo.get_by_id(job_id)
                    if job:
                        await repo.update(job, is_enabled=False)
            if reply_to:
                await self.client.send_message(reply_to, f"✅ 定时任务 #{job_id} 已停止")
        except Exception as e:
            if reply_to:
                await self.client.send_message(reply_to, f"删除失败: {e}")

    async def _handle_list(self, **kwargs: Any) -> None:
        """处理列出定时任务事件"""
        reply_to = kwargs.get("reply_to_chat")
        if not reply_to:
            return

        session = self.db.get_session()
        async with session:
            repo = ScheduleRepository(session)
            jobs = await repo.get_enabled()

        if not jobs:
            await self.client.send_message(reply_to, "暂无定时任务。")
            return

        lines = ["📋 定时任务列表：\n"]
        for job in jobs:
            last = job.last_run_at.strftime("%m-%d %H:%M") if job.last_run_at else "从未"
            lines.append(
                f"#{job.id} {job.name}\n"
                f"  Cron: {job.cron_expr}\n"
                f"  目标: {job.target_chat_id}\n"
                f"  上次执行: {last} (共{job.run_count}次)"
            )
        await self.client.send_message(reply_to, "\n".join(lines))
