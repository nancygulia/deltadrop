from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.session import Base


class UserRole(str, enum.Enum):
    user  = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id            : Mapped[int]      = mapped_column(primary_key=True)
    email         : Mapped[str]      = mapped_column(String(255), unique=True, nullable=False, index=True)
    username      : Mapped[str]      = mapped_column(String(100), unique=True, nullable=False)
    password_hash : Mapped[str]      = mapped_column(String(255), nullable=False)
    full_name     : Mapped[str]      = mapped_column(String(200), nullable=True)
    role          : Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user)
    is_active     : Mapped[bool]     = mapped_column(Boolean, default=True)
    is_superuser  : Mapped[bool]     = mapped_column(Boolean, default=False)
    created_at    : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at    : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    watchlist    = relationship("WatchlistItem",  back_populates="user", cascade="all, delete-orphan")
    alerts       = relationship("PriceAlert",     back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         : Mapped[int]      = mapped_column(primary_key=True)
    user_id    : Mapped[int]      = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash : Mapped[str]      = mapped_column(String(255), unique=True, nullable=False)
    expires_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked    : Mapped[bool]     = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="refresh_tokens")


class UsedResetToken(Base):
    __tablename__ = "used_reset_tokens"

    id         : Mapped[int]      = mapped_column(primary_key=True)
    token_hash : Mapped[str]      = mapped_column(String(255), unique=True, nullable=False, index=True)
    used_at    : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
