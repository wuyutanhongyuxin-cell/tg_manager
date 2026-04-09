"""Telegram 消息记录模型

存储从 Telegram 抓取/监控的消息，用于搜索、导出、AI 总结等功能。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class TelegramMessage(Base):
    """Telegram 消息 ORM 模型

    使用 (chat_id, message_id) 联合唯一索引确保不重复存储。
    Telegram ID 使用 BigInteger，因为频道 ID 可能超过 32 位范围。
    """

    __tablename__ = "telegram_messages"

    # 主键（数据库自增）
    id: Mapped[int] = mapped_column(primary_key=True)

    # Telegram 消息标识
    message_id: Mapped[int] = mapped_column(
        BigInteger, comment="Telegram 消息 ID"
    )
    chat_id: Mapped[int] = mapped_column(
        BigInteger, index=True, comment="聊天 ID"
    )
    sender_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="发送者 ID（匿名管理员为空）"
    )

    # 消息内容
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="发送时间（UTC）"
    )
    text: Mapped[str] = mapped_column(
        Text, default="", comment="消息文本"
    )
    media_type: Mapped[Optional[str]] = mapped_column(
        String(50), comment="媒体类型: photo/document/video 等"
    )

    # 转发信息
    is_forward: Mapped[bool] = mapped_column(
        default=False, comment="是否为转发消息"
    )
    forward_from_chat_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="转发来源聊天 ID"
    )
    forward_from_msg_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="转发来源消息 ID"
    )

    # 回复与分组
    reply_to_msg_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="回复的消息 ID"
    )
    grouped_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="媒体组 ID（相册）"
    )

    # 状态
    views: Mapped[Optional[int]] = mapped_column(comment="浏览数（频道）")
    is_pinned: Mapped[bool] = mapped_column(
        default=False, comment="是否置顶"
    )

    # 原始数据（用于调试和数据恢复）
    raw_data: Mapped[Optional[str]] = mapped_column(
        Text, comment="原始 JSON 数据"
    )

    # 记录时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 联合唯一索引：同一聊天中的消息 ID 不重复
    __table_args__ = (
        Index("ix_msg_chat_msgid", "chat_id", "message_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Message(chat={self.chat_id}, msg={self.message_id})>"
