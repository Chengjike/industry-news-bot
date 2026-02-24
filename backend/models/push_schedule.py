from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.industry import Industry


class PushSchedule(Base):
    __tablename__ = "push_schedule"
    __table_args__ = (
        CheckConstraint(
            "(push_type = 'morning' AND hour BETWEEN 6 AND 12) OR "
            "(push_type = 'evening' AND hour BETWEEN 16 AND 21)",
            name="check_push_time_reasonable"
        ),
    )

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
