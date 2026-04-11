"""关键词监控模型

存储用户通过 /keyword 命令配置的告警关键词。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class MonitorKeyword(Base):
    """关键词监控 ORM 模型

    每条记录代表一个全局监控关键词。匹配到时通过 client.notify_admin
    向管理员发送告警。关键词以「包含 + 大小写不敏感」方式匹配。
    """

    __tablename__ = "monitor_keywords"

    id: Mapped[int] = mapped_column(primary_key=True)

    keyword: Mapped[str] = mapped_column(
        String(200), unique=True, comment="监控关键词"
    )
    is_enabled: Mapped[bool] = mapped_column(
        default=True, comment="是否启用"
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="创建者 Telegram ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<MonitorKeyword(keyword={self.keyword!r})>"
