"""推送记录模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.database import Base


class PushLog(Base):
    __tablename__ = "push_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    industry_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("industry.id", ondelete="SET NULL"), nullable=True, index=True
    )
    push_type: Mapped[str] = mapped_column(String(10), nullable=False)       # "morning" | "evening"
    status: Mapped[str] = mapped_column(String(10), nullable=False)          # "success" | "failed" | "skipped"
    article_count: Mapped[int] = mapped_column(Integer, default=0)
    recipient_count: Mapped[int] = mapped_column(Integer, default=0)
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # 失败原因
    html_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 推送邮件 HTML 快照
    triggered_by: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduler")  # "scheduler" | "manual"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
