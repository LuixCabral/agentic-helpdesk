from datetime import datetime, timezone
from typing import List, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from api.Models.api_key_model import ApiKey


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    api_keys: Mapped[List["ApiKey"]] = relationship("ApiKey", back_populates="user")

    @classmethod
    def create_user(cls, name: str, email: str, password: str) -> "User":
        return cls(
            name=name,
            email=email,
            password=password,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def update_user(self, name: str, email: str, password: str) -> "User":
        self.name = name
        self.email = email
        self.password = password
        self.updated_at = datetime.now(timezone.utc)
        return self

    def soft_delete_user(self) -> "User":
        self.is_deleted = True
        self.updated_at = datetime.now(timezone.utc)
        return self
