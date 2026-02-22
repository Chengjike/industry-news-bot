from datetime import datetime
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.news_source import NewsSource
    from backend.models.finance_item import FinanceItem
    from backend.models.recipient import Recipient
    from backend.models.push_schedule import PushSchedule


class Industry(Base):
    __tablename__ = "industry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    top_n: Mapped[int] = mapped_column(Integer, default=10)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 行业级关键词过滤，格式同 NewsSource.keywords
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    news_sources: Mapped[list["NewsSource"]] = relationship(
        "NewsSource", back_populates="industry", cascade="all, delete-orphan"
    )
    finance_items: Mapped[list["FinanceItem"]] = relationship(
        "FinanceItem", back_populates="industry", cascade="all, delete-orphan"
    )
    recipients: Mapped[list["Recipient"]] = relationship(
        "Recipient", back_populates="industry", cascade="all, delete-orphan"
    )
    push_schedules: Mapped[list["PushSchedule"]] = relationship(
        "PushSchedule", back_populates="industry", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return self.name
