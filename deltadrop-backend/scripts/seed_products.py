"""
Seeds PostgreSQL with sample products and synthetic price history
so the ML model has data to train on immediately.

Usage: python scripts/seed_products.py
"""
import sys, os, asyncio, random
from decimal import Decimal
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app.models.user    # noqa
import app.models.product # noqa

from app.db.session import engine, Base, AsyncSessionLocal
from app.models.product import (
    Product, RetailerListing, PriceHistory,
    ProductCategory, RetailerName,
)
from app.utils.slugify import slugify

SEED_PRODUCTS = [
    {
        "name": "Apple iPhone 15 Pro",
        "brand": "Apple",
        "category": ProductCategory.smartphones,
        "image_url": "https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/iphone-15-pro-finish-select-202309-6-7inch-naturaltitanium",
        "retailers": [
            {"retailer": RetailerName.amazon,   "url": "https://www.amazon.in/Apple-iPhone-15-Pro-256GB/dp/B0CHX1W1XY", "price": 127900, "mrp": 134900},
            {"retailer": RetailerName.flipkart,  "url": "https://www.flipkart.com/apple-iphone-15-pro/p/itm", "price": 129900, "mrp": 134900},
            {"retailer": RetailerName.reliance,  "url": "https://www.reliancedigital.in/apple-iphone-15-pro", "price": 132900, "mrp": 134900},
        ],
    },
    {
        "name": "Sony WH-1000XM5",
        "brand": "Sony",
        "category": ProductCategory.headphones,
        "image_url": "https://www.sony.co.in/image/e7c53e50e9d3e70bed5b48d0bad7b2b3",
        "retailers": [
            {"retailer": RetailerName.amazon,   "url": "https://www.amazon.in/Sony-WH-1000XM5-Cancelling-Headphones/dp/B09XS7JWHH", "price": 24990, "mrp": 34990},
            {"retailer": RetailerName.flipkart,  "url": "https://www.flipkart.com/sony-wh-1000xm5/p/itm", "price": 25999, "mrp": 34990},
            {"retailer": RetailerName.reliance,  "url": "https://www.reliancedigital.in/sony-wh-1000xm5", "price": 26490, "mrp": 34990},
        ],
    },
    {
        "name": "MacBook Air M2",
        "brand": "Apple",
        "category": ProductCategory.laptops,
        "image_url": "https://store.storeimages.cdn-apple.com/4982/as-images.apple.com/is/macbook-air-midnight-config-20220606",
        "retailers": [
            {"retailer": RetailerName.amazon,   "url": "https://www.amazon.in/Apple-MacBook-Chip-13-inch-256GB/dp/B0B3C5MFHQ", "price": 89900, "mrp": 114900},
            {"retailer": RetailerName.flipkart,  "url": "https://www.flipkart.com/apple-macbook-air-m2/p/itm", "price": 91990, "mrp": 114900},
            {"retailer": RetailerName.reliance,  "url": "https://www.reliancedigital.in/apple-macbook-air-m2", "price": 89900, "mrp": 114900},
        ],
    },
    {
        "name": "Samsung Galaxy S24 Ultra",
        "brand": "Samsung",
        "category": ProductCategory.smartphones,
        "image_url": "https://images.samsung.com/is/image/samsung/p6pim/in/sm-s928bzkginu/gallery/in-galaxy-s24-ultra-s928-sm-s928bzkginu-thumb-539573387",
        "retailers": [
            {"retailer": RetailerName.amazon,   "url": "https://www.amazon.in/Samsung-Galaxy-S24-Ultra-512GB/dp/B0CS3VV3RJ", "price": 109999, "mrp": 134999},
            {"retailer": RetailerName.flipkart,  "url": "https://www.flipkart.com/samsung-galaxy-s24-ultra/p/itm", "price": 111999, "mrp": 134999},
        ],
    },
    {
        "name": "LG OLED C3 55 inch 4K TV",
        "brand": "LG",
        "category": ProductCategory.television,
        "image_url": "https://www.lg.com/in/images/tvs/md07535551/gallery/desktop-01.jpg",
        "retailers": [
            {"retailer": RetailerName.amazon,   "url": "https://www.amazon.in/LG-139-cm-55-Inch-OLED55C3PSA/dp/B0C7Q6VHHV", "price": 124990, "mrp": 159990},
            {"retailer": RetailerName.flipkart,  "url": "https://www.flipkart.com/lg-oled-c3/p/itm", "price": 127990, "mrp": 159990},
            {"retailer": RetailerName.reliance,  "url": "https://www.reliancedigital.in/lg-oled-c3", "price": 124990, "mrp": 159990},
        ],
    },
    {
        "name": "Nike Air Max 270",
        "brand": "Nike",
        "category": ProductCategory.shoes,
        "image_url": "https://static.nike.com/a/images/c_limit,w_592,f_auto/t_product_v1/e6da41fa-1be4-4ce5-b89c-22be4f1f02d4/air-max-270-shoes-2V5C4p.png",
        "retailers": [
            {"retailer": RetailerName.myntra,   "url": "https://www.myntra.com/sports-shoes/nike/nike-air-max-270/12476484/buy", "price": 9995, "mrp": 12495},
            {"retailer": RetailerName.flipkart,  "url": "https://www.flipkart.com/nike-air-max-270/p/itm", "price": 10495, "mrp": 12495},
        ],
    },
    {
        "name": "Sony Alpha A7 IV",
        "brand": "Sony",
        "category": ProductCategory.cameras,
        "image_url": "https://www.sony.co.in/image/a7iv-camera",
        "retailers": [
            {"retailer": RetailerName.amazon,   "url": "https://www.amazon.in/Sony-Full-Frame-Mirrorless-Camera-ILCE-7M4K/dp/B09JZZ9TSR", "price": 209990, "mrp": 249990},
            {"retailer": RetailerName.flipkart,  "url": "https://www.flipkart.com/sony-alpha-a7-iv/p/itm", "price": 214990, "mrp": 249990},
        ],
    },
    {
        "name": "PlayStation 5 Disc Edition",
        "brand": "Sony",
        "category": ProductCategory.gaming,
        "image_url": "https://gmedia.playstation.com/is/image/SIEPDC/ps5-product-thumbnail-01-en-14sep21",
        "retailers": [
            {"retailer": RetailerName.amazon,   "url": "https://www.amazon.in/Sony-PlayStation-CFI-1200A01/dp/B0BJDMQX7K", "price": 49990, "mrp": 54990},
            {"retailer": RetailerName.flipkart,  "url": "https://www.flipkart.com/sony-playstation-5/p/itm", "price": 49990, "mrp": 54990},
        ],
    },
]


def _gen_price_history(base_price: float, days: int = 90) -> list[float]:
    """Generate synthetic realistic price history with trend + noise."""
    prices = []
    price  = base_price * 1.15   # start 15% above current
    now    = datetime.now(timezone.utc)

    for day in range(days, -1, -1):
        # Gradual downtrend with random noise + occasional spikes
        noise    = random.gauss(0, base_price * 0.008)
        trend    = -base_price * 0.0012   # ~10% drop over 90 days
        spike    = base_price * 0.04 if random.random() < 0.05 else 0   # 5% chance spike
        price    = max(base_price * 0.75, price + trend + noise + spike)
        prices.append((now - timedelta(days=day), round(price, 2)))

    return prices


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables ready")

    async with AsyncSessionLocal() as db:
        seeded = 0
        for pdata in SEED_PRODUCTS:
            slug = slugify(pdata["name"])

            from sqlalchemy import select
            result  = await db.execute(select(Product).where(Product.slug == slug))
            product = result.scalar_one_or_none()

            if product:
                print(f"  ⏭  Skip (exists): {pdata['name']}")
                continue

            product = Product(
                name      = pdata["name"],
                slug      = slug,
                brand     = pdata["brand"],
                category  = pdata["category"],
                image_url = pdata.get("image_url"),
            )
            db.add(product)
            await db.flush()

            for rdata in pdata["retailers"]:
                listing = RetailerListing(
                    product_id    = product.id,
                    retailer      = rdata["retailer"],
                    retailer_url  = rdata["url"],
                    current_price = Decimal(str(rdata["price"])),
                    mrp           = Decimal(str(rdata["mrp"])),
                    in_stock      = True,
                    last_scraped_at = datetime.now(timezone.utc),
                )
                db.add(listing)
                await db.flush()

                # Generate 90 days of price history
                history_points = _gen_price_history(rdata["price"], days=90)
                for recorded_at, price in history_points:
                    mrp = Decimal(str(rdata["mrp"]))
                    prc = Decimal(str(price))
                    disc = ((mrp - prc) / mrp * 100).quantize(Decimal("0.01")) if mrp > 0 else None
                    db.add(PriceHistory(
                        product_id   = product.id,
                        listing_id   = listing.id,
                        retailer     = rdata["retailer"],
                        price        = prc,
                        mrp          = mrp,
                        discount_pct = disc,
                        in_stock     = True,
                        recorded_at  = recorded_at,
                    ))

            await db.commit()
            seeded += 1
            print(f"  ✅ Seeded: {pdata['name']} ({len(pdata['retailers'])} retailers, 90 days history)")

    await engine.dispose()
    print(f"\n✅ Done — {seeded} products seeded with price history")


if __name__ == "__main__":
    asyncio.run(seed())
