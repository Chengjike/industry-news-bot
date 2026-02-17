from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SeenArticle(Base):
    """已见过的文章记录表 - 用于识别新增文章"""
    __tablename__ = "seen_article"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    source_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("news_source.id", ondelete="SET NULL"),
        nullable=True,
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
