from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.industry import Industry


class Recipient(Base):
    __tablename__ = "recipient"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    industry_id: Mapped[int] = mapped_column(ForeignKey("industry.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    industry: Mapped["Industry"] = relationship("Industry", back_populates="recipients")

    def __str__(self) -> str:
        return self.email
