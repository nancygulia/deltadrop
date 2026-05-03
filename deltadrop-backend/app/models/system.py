from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RateLimitState(Base):
    """
    Persistent store for rate limiting state.
    Used for unauthenticated public endpoints and admin job triggers.
    Replaces module-level dicts that reset on server restart.
    """
    __tablename__ = "rate_limit_state"

    # key example: "public:image-search:127.0.0.1" or "admin:job:manual_sync"
    key            : Mapped[str]      = mapped_column(String(255), primary_key=True)
    last_triggered : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Optional metadata or request count if we want to expand beyond simple 'last timestamp'
    hits           : Mapped[int]      = mapped_column(default=1)

    def __repr__(self):
        return f"<RateLimitState {self.key} [{self.last_triggered}]>"
