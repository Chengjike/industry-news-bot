from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.industry import Industry


class FinanceItem(Base):
    __tablename__ = "finance_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    industry_id: Mapped[int] = mapped_column(ForeignKey("industry.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "stock" | "futures"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    industry: Mapped["Industry"] = relationship("Industry", back_populates="finance_items")

    def __str__(self) -> str:
        return f"{self.name}({self.symbol})"
