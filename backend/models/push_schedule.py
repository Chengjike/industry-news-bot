from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.industry import Industry


class PushSchedule(Base):
    __tablename__ = "push_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    industry_id: Mapped[int] = mapped_column(ForeignKey("industry.id"), nullable=False)
    push_type: Mapped[str] = mapped_column(String(10), nullable=False)  # "morning" | "evening"
    hour: Mapped[int] = mapped_column(Integer, default=9)    # 0-23
    minute: Mapped[int] = mapped_column(Integer, default=0)  # 0-59
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    industry: Mapped["Industry"] = relationship("Industry", back_populates="push_schedules")

    def __str__(self) -> str:
        return f"{self.push_type} {self.hour:02d}:{self.minute:02d}"
