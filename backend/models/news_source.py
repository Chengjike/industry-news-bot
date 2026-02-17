from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.industry import Industry


class NewsSource(Base):
    __tablename__ = "news_source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    industry_id: Mapped[int] = mapped_column(ForeignKey("industry.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=5)  # 1-10
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # "+必须词 !排除词 普通词"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    industry: Mapped["Industry"] = relationship("Industry", back_populates="news_sources")

    def __str__(self) -> str:
        return self.name
