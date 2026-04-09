"""Telegram 用户记录模型

存储与管理相关的用户信息，支持封禁、警告等群管功能。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class User(Base):
    """Telegram 用户 ORM 模型

    记录用户基本信息和管理状态（封禁、警告计数等）。
    warn_count 达到阈值时可自动触发封禁。
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Telegram 用户标识（唯一）
    user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, comment="Telegram 用户 ID"
    )

    # 基本信息
    username: Mapped[Optional[str]] = mapped_column(
        String(100), comment="@用户名"
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(100), comment="名"
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(100), comment="姓"
    )

    # 管理状态
    is_admin: Mapped[bool] = mapped_column(
        default=False, comment="是否为 Bot 管理员"
    )
    is_banned: Mapped[bool] = mapped_column(
        default=False, comment="是否被全局封禁"
    )
    warn_count: Mapped[int] = mapped_column(
        default=0, comment="累计警告次数"
    )
    ban_reason: Mapped[Optional[str]] = mapped_column(
        Text, comment="封禁原因"
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
        return f"<User(id={self.user_id}, name={self.username})>"
