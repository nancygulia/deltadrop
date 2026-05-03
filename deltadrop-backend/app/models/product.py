from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String, Text, Numeric, Integer, DateTime, Boolean,
    ForeignKey, UniqueConstraint, Index, Enum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal
import enum

from app.db.session import Base


class ProductCategory(str, enum.Enum):
    smartphones   = "Smartphones"
    laptops       = "Laptops"
    headphones    = "Headphones"
    earbuds       = "Earbuds"
    speakers      = "Speakers"
    cameras       = "Cameras"
    television    = "Television"
    monitors      = "Monitors"
    gaming        = "Gaming"
    appliances    = "Appliances"
    fashion       = "Fashion"
    shoes         = "Shoes"
    smartwatches  = "Smartwatches"
    tablets       = "Tablets"
    kitchen       = "Kitchen"
    accessories   = "Accessories"
    other         = "Other"


class RetailerName(str, enum.Enum):
    amazon    = "Amazon.in"
    flipkart  = "Flipkart"
    myntra    = "Myntra"
    reliance  = "Reliance Digital"
    nykaa     = "Nykaa"
    tatacliq  = "Tata CLiQ"
    croma     = "Croma"
    meesho    = "Meesho"
    ajio      = "AJIO"
    snapdeal  = "Snapdeal"
    cashify   = "Cashify"


class Product(Base):
    __tablename__ = "products"

    id              : Mapped[int]              = mapped_column(primary_key=True)
    name            : Mapped[str]              = mapped_column(String(500), nullable=False)
    slug            : Mapped[str]              = mapped_column(String(600), unique=True, nullable=False, index=True)
    brand           : Mapped[Optional[str]]    = mapped_column(String(200))
    category        : Mapped[ProductCategory]  = mapped_column(Enum(ProductCategory), nullable=False, index=True)
    description     : Mapped[Optional[str]]    = mapped_column(Text)
    image_url       : Mapped[Optional[str]]    = mapped_column(String(2000))
    specs           : Mapped[Optional[str]]    = mapped_column(Text)   # JSON string of specs
    is_active       : Mapped[bool]             = mapped_column(Boolean, default=True)
    created_at      : Mapped[datetime]         = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at      : Mapped[datetime]         = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    retailer_listings = relationship("RetailerListing", back_populates="product", cascade="all, delete-orphan")
    price_history     = relationship("PriceHistory",     back_populates="product", cascade="all, delete-orphan", order_by="PriceHistory.recorded_at")
    watchlist_items   = relationship("WatchlistItem",    back_populates="product", cascade="all, delete-orphan")
    alerts            = relationship("PriceAlert",       back_populates="product", cascade="all, delete-orphan")
    predictions       = relationship("PricePrediction",  back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_products_category_active", "category", "is_active"),
    )

    def __repr__(self):
        return f"<Product {self.name}>"


class RetailerListing(Base):
    """One product can exist across multiple retailers at different prices."""
    __tablename__ = "retailer_listings"

    id              : Mapped[int]             = mapped_column(primary_key=True)
    product_id      : Mapped[int]             = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    retailer        : Mapped[RetailerName]    = mapped_column(Enum(RetailerName), nullable=False)
    retailer_url    : Mapped[str]             = mapped_column(String(2000), nullable=False)
    retailer_sku    : Mapped[Optional[str]]   = mapped_column(String(500))
    current_price   : Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    mrp             : Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    in_stock        : Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)
    is_active       : Mapped[bool]            = mapped_column(Boolean, default=True)
    last_scraped_at : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scrape_errors   : Mapped[int]             = mapped_column(Integer, default=0)
    created_at      : Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    product       = relationship("Product",      back_populates="retailer_listings")
    price_history = relationship("PriceHistory", back_populates="listing",  cascade="all, delete-orphan")

    @property
    def safe_in_stock(self) -> bool:
        """Safe stock check - returns True if in_stock is True or None (treated as True)"""
        return self.in_stock is True or self.in_stock is None

    __table_args__ = (
        UniqueConstraint("product_id", "retailer", name="uq_product_retailer"),
        Index("ix_listings_retailer_active", "retailer", "is_active"),
    )


class PriceHistory(Base):
    """Immutable time-series price records — append only, never mutated."""
    __tablename__ = "price_history"

    id          : Mapped[int]             = mapped_column(primary_key=True)
    product_id  : Mapped[int]             = mapped_column(ForeignKey("products.id",          ondelete="CASCADE"), nullable=False, index=True)
    listing_id  : Mapped[int]             = mapped_column(ForeignKey("retailer_listings.id",  ondelete="CASCADE"), nullable=False, index=True)
    retailer    : Mapped[RetailerName]    = mapped_column(Enum(RetailerName), nullable=False)
    price       : Mapped[Decimal]         = mapped_column(Numeric(12, 2), nullable=False)
    mrp         : Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    discount_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    in_stock    : Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)
    recorded_at : Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    product = relationship("Product",         back_populates="price_history")
    listing = relationship("RetailerListing", back_populates="price_history")

    __table_args__ = (
        Index("ix_price_history_product_retailer_time", "product_id", "retailer", "recorded_at"),
    )


class PricePrediction(Base):
    """ML model output stored per product."""
    __tablename__ = "price_predictions"

    id                  : Mapped[int]             = mapped_column(primary_key=True)
    product_id          : Mapped[int]             = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    predicted_price     : Mapped[Decimal]         = mapped_column(Numeric(12, 2), nullable=False)
    predicted_low       : Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    predicted_high      : Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    confidence          : Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))   # 0.0 – 1.0
    horizon_days        : Mapped[int]             = mapped_column(Integer, default=14)
    verdict             : Mapped[str]             = mapped_column(String(20), default="WAIT")   # BUY_NOW | WAIT | NEUTRAL
    reasoning           : Mapped[Optional[str]]   = mapped_column(Text)
    model_version       : Mapped[str]             = mapped_column(String(50), default="v1")
    predicted_at        : Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="predictions")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id         : Mapped[int]  = mapped_column(primary_key=True)
    user_id    : Mapped[int]  = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id : Mapped[int]  = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    added_at   : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user    = relationship("User",    back_populates="watchlist")
    product = relationship("Product", back_populates="watchlist_items")

    __table_args__ = (UniqueConstraint("user_id", "product_id"),)


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id            : Mapped[int]           = mapped_column(primary_key=True)
    user_id       : Mapped[int]           = mapped_column(ForeignKey("users.id",     ondelete="CASCADE"), nullable=False, index=True)
    product_id    : Mapped[int]           = mapped_column(ForeignKey("products.id",  ondelete="CASCADE"), nullable=False, index=True)
    target_price  : Mapped[Decimal]       = mapped_column(Numeric(12, 2), nullable=False)
    threshold_pct : Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    retailer      : Mapped[Optional[str]] = mapped_column(String(100))   # None = any retailer
    is_active     : Mapped[bool]          = mapped_column(Boolean, default=True)
    triggered_at  : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at    : Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user    = relationship("User",    back_populates="alerts")
    product = relationship("Product", back_populates="alerts")

from sqlalchemy import JSON

class SearchCache(Base):
    __tablename__ = "search_cache"

    id         : Mapped[int]      = mapped_column(primary_key=True)
    query      : Mapped[str]      = mapped_column(String(500), unique=True, index=True, nullable=False)
    stores     : Mapped[dict]     = mapped_column(JSON, nullable=False)
    best_price : Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    timestamp  : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class SimpleWatchlistAlert(Base):
    """
    Lightweight email-only price alert that does NOT require user registration.
    Created when a user enters their email + target price from any product page.
    """
    __tablename__ = "simple_watchlist_alerts"

    id           : Mapped[int]             = mapped_column(primary_key=True)
    email        : Mapped[str]             = mapped_column(String(320), nullable=False, index=True)
    product_name : Mapped[str]             = mapped_column(String(500), nullable=False)
    target_price : Mapped[Decimal]         = mapped_column(Numeric(12, 2), nullable=False)
    last_price   : Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))   # cached latest price
    product_url  : Mapped[Optional[str]]   = mapped_column(String(2000))
    image_url    : Mapped[Optional[str]]   = mapped_column(String(2000))
    is_active    : Mapped[bool]            = mapped_column(Boolean, default=True)
    triggered_at : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at   : Mapped[datetime]        = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_simple_alerts_email_active", "email", "is_active"),
    )


class Notification(Base):
    """
    In-app notifications persisted to DB.
    Keyed by email (supports both logged-in and anonymous users).
    """
    __tablename__ = "notifications"

    id         : Mapped[int]           = mapped_column(primary_key=True)
    email      : Mapped[str]           = mapped_column(String(320), nullable=False, index=True)
    title      : Mapped[str]           = mapped_column(String(300), nullable=False)
    body       : Mapped[str]           = mapped_column(Text, nullable=False)
    icon       : Mapped[str]           = mapped_column(String(10), default="🔔")
    is_read    : Mapped[bool]          = mapped_column(Boolean, default=False, index=True)
    action_url : Mapped[Optional[str]] = mapped_column(String(2000))   # link to product page
    created_at : Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("ix_notifications_email_unread", "email", "is_read"),
    )
