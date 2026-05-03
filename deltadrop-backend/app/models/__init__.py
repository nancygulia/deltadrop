"""
app/models/__init__.py
======================
Central model registry — MUST be imported before any SQLAlchemy session is opened.

SQLAlchemy resolves relationship() string references (e.g. relationship("User"))
lazily when the mapper is first used. If the referenced class hasn't been imported
yet, the mapper raises "expression 'User' failed to locate a name" and EVERY
subsequent DB write in that process fails with a rollback.

Import order matters:
  1. user.py    — defines User, RefreshToken, UsedResetToken
  2. product.py — defines Product, RetailerListing, etc. (references "User")
  3. system.py  — defines RateLimitState, ScraperSession
  4. scraper_session.py

By importing all modules here, anyone who does `from app.models import ...`
or `import app.models` gets a fully-initialised mapper registry.
"""

# 1. User model FIRST — WatchlistItem/PriceAlert in product.py reference "User"
from app.models.user import User, RefreshToken, UsedResetToken  # noqa: F401

# 2. Product models — safely reference "User" now that it's registered
from app.models.product import (  # noqa: F401
    Product,
    RetailerListing,
    PriceHistory,
    PricePrediction,
    WatchlistItem,
    PriceAlert,
    RetailerName,
    ProductCategory,
)

# 3. System / infrastructure models
from app.models.system import RateLimitState  # noqa: F401

try:
    from app.models.scraper_session import ScraperSession  # noqa: F401
except ImportError:
    pass  # optional module
