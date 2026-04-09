"""消息转发规则模型

定义源聊天到目标聊天的转发映射和过滤条件。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class ForwardRule(Base):
    """转发规则 ORM 模型

    forward_type 取值：
    - forward: 标准转发（保留"转发自"标签）
    - copy: 复制消息（无标签，但需要 Userbot）
    - copy_clean: 复制并清理格式（去除所有来源标记）

    filter_pattern 为空表示转发所有消息，否则仅转发匹配的消息。
    filter_type 控制 filter_pattern 的匹配方式。
    """

    __tablename__ = "forward_rules"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 规则名称
    name: Mapped[str] = mapped_column(
        String(100), comment="规则名称"
    )

    # 源和目标
    source_chat_id: Mapped[int] = mapped_column(
        BigInteger, index=True, comment="源聊天 ID"
    )
    target_chat_id: Mapped[int] = mapped_column(
        BigInteger, comment="目标聊天 ID"
    )

    # 转发方式
    forward_type: Mapped[str] = mapped_column(
        String(20), default="forward",
        comment="转发类型: forward/copy/copy_clean",
    )

    # 过滤条件（可选）
    filter_pattern: Mapped[Optional[str]] = mapped_column(
        String(500), comment="过滤关键词或正则"
    )
    filter_type: Mapped[str] = mapped_column(
        String(20), default="keyword",
        comment="过滤类型: keyword/regex/none",
    )

    # 选项
    is_enabled: Mapped[bool] = mapped_column(
        default=True, comment="是否启用"
    )
    remove_forward_tag: Mapped[bool] = mapped_column(
        default=False, comment="是否去除转发标签"
    )
    include_media: Mapped[bool] = mapped_column(
        default=True, comment="是否包含媒体文件"
    )

    # 备注
    note: Mapped[Optional[str]] = mapped_column(
        Text, comment="备注"
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
        return f"<ForwardRule(name={self.name}, {self.source_chat_id}->{self.target_chat_id})>"
