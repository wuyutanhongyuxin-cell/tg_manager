"""聊天（群组/频道/私聊）记录模型

存储需要管理的 Telegram 聊天信息，支持监控和镜像功能标记。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class Chat(Base):
    """Telegram 聊天 ORM 模型

    记录群组、频道、私聊的基本信息和管理状态。
    chat_type 取值：user（私聊）、group（普通群）、channel（频道/超级群）。
    """

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Telegram 聊天标识（唯一）
    chat_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, comment="Telegram 聊天 ID"
    )
    chat_type: Mapped[str] = mapped_column(
        String(20), comment="类型: user/group/channel"
    )

    # 基本信息
    title: Mapped[Optional[str]] = mapped_column(
        String(255), comment="聊天标题或用户名"
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(100), comment="@用户名"
    )

    # 功能标记
    is_monitored: Mapped[bool] = mapped_column(
        default=False, comment="是否启用关键词监控"
    )
    is_mirror_source: Mapped[bool] = mapped_column(
        default=False, comment="是否为镜像同步源"
    )
    is_mirror_target: Mapped[bool] = mapped_column(
        default=False, comment="是否为镜像同步目标"
    )

    # 备注
    note: Mapped[Optional[str]] = mapped_column(
        Text, comment="管理员备注"
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
        return f"<Chat(id={self.chat_id}, type={self.chat_type}, title={self.title})>"
