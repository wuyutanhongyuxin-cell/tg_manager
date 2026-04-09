"""自动回复规则模型

存储关键词/正则匹配规则和对应的自动回复模板。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class AutoReplyRule(Base):
    """自动回复规则 ORM 模型

    rule_type 取值：
    - keyword: 关键词包含匹配（大小写不敏感）
    - regex: 正则表达式匹配
    - exact: 精确匹配

    chat_id 为空表示全局规则，适用于所有聊天。
    优先级数字越大越先匹配，匹配到第一条即停止。
    """

    __tablename__ = "auto_reply_rules"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 规则基本信息
    name: Mapped[str] = mapped_column(
        String(100), comment="规则名称（便于管理）"
    )
    rule_type: Mapped[str] = mapped_column(
        String(20), comment="匹配类型: keyword/regex/exact"
    )
    pattern: Mapped[str] = mapped_column(
        String(500), comment="匹配模式（关键词、正则表达式或精确文本）"
    )
    response: Mapped[str] = mapped_column(
        Text, comment="回复内容（支持变量替换）"
    )

    # 适用范围
    chat_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, index=True, comment="适用聊天 ID（空=全局）"
    )

    # 状态与优先级
    is_enabled: Mapped[bool] = mapped_column(
        default=True, comment="是否启用"
    )
    priority: Mapped[int] = mapped_column(
        default=0, comment="优先级（数字越大越优先）"
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
        return f"<Rule(name={self.name}, type={self.rule_type})>"
