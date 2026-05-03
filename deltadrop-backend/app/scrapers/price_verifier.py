import asyncio
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import quote_plus

import requests

from app.core.config import settings

_scraperapi_verify_semaphore = asyncio.Semaphore(5)
_price_pattern = re.compile(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)


def _extract_price(html: str) -> Decimal | None:
    if not html:
        return None
    match = _price_pattern.search(html)
    if not match:
        return None
    try:
        return Decimal(match.group(1).replace(",", ""))
    except Exception:
        return None


def _extract_stock(html: str) -> bool | None:
    text = (html or "").lower()
    if any(k in text for k in ["out of stock", "sold out", "unavailable"]):
        return False
    if any(k in text for k in ["in stock", "add to cart", "buy now"]):
        return True
    return None


async def verify_retailer_price(url: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    if not settings.SCRAPER_API_KEY:
        return {"url": url, "verified_price": None, "in_stock": None, "verified_at": now, "ok": False, "error": "SCRAPER_API_KEY missing"}

    async with _scraperapi_verify_semaphore:
        try:
            encoded_url = quote_plus(url)
            api_url = f"http://scraperapi.com?api_key={settings.SCRAPER_API_KEY}&url={encoded_url}"
            response = await asyncio.to_thread(requests.get, api_url, timeout=20)
            response.raise_for_status()
            html = response.text
            return {
                "url": url,
                "verified_price": _extract_price(html),
                "in_stock": _extract_stock(html),
                "verified_at": now,
                "ok": True,
                "error": None,
            }
        except Exception as exc:
            return {"url": url, "verified_price": None, "in_stock": None, "verified_at": now, "ok": False, "error": str(exc)}


async def verify_retailer_prices(urls: list[str]) -> list[dict[str, Any]]:
    return await asyncio.gather(*(verify_retailer_price(url) for url in urls))
