from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SmtpConfig(Base):
    __tablename__ = "smtp_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=465)
    username: Mapped[str] = mapped_column(String(254), nullable=False)
    # 密码使用 Fernet 加密存储
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    sender_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # 侵权联系邮箱（合规要求）
    contact_email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    use_tls: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __str__(self) -> str:
        return f"{self.username}@{self.host}"
