"""定时任务模型

存储用户配置的定时发送任务（cron 表达式 + 目标聊天 + 消息内容）。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class ScheduledJob(Base):
    """定时任务 ORM 模型

    每条记录代表一个定时发送任务：
    - cron_expr: 标准 cron 表达式（分 时 日 月 周）
    - target_chat_id: 发送目标聊天
    - message_text: 要发送的文本内容
    """

    __tablename__ = "scheduled_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 任务基本信息
    name: Mapped[str] = mapped_column(
        String(100), comment="任务名称（便于管理）"
    )
    cron_expr: Mapped[str] = mapped_column(
        String(100), comment="Cron 表达式（分 时 日 月 周）"
    )

    # 发送目标
    target_chat_id: Mapped[int] = mapped_column(
        BigInteger, index=True, comment="目标聊天 ID"
    )

    # 消息内容
    message_text: Mapped[str] = mapped_column(
        Text, comment="发送的文本消息"
    )

    # 状态控制
    is_enabled: Mapped[bool] = mapped_column(
        default=True, comment="是否启用"
    )
    timezone: Mapped[str] = mapped_column(
        String(50), default="Asia/Shanghai", comment="时区"
    )

    # 执行记录
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="上次执行时间"
    )
    run_count: Mapped[int] = mapped_column(
        default=0, comment="累计执行次数"
    )

    # 创建者
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="创建者 Telegram ID"
    )

    # 记录时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<ScheduledJob(name={self.name}, cron={self.cron_expr})>"
