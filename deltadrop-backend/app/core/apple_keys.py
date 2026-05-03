import logging
import time
from typing import Any

import requests
from jwt.algorithms import RSAAlgorithm


APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
_CACHE_TTL_SECONDS = 3600

logger = logging.getLogger(__name__)

_cached_keys: dict[str, Any] = {}
_cache_expires_at: float = 0.0


def _fetch_apple_keys() -> dict[str, Any]:
    response = requests.get(APPLE_KEYS_URL, timeout=10)
    response.raise_for_status()
    payload = response.json()
    keys = payload.get("keys", [])

    parsed: dict[str, Any] = {}
    for key in keys:
        kid = key.get("kid")
        if not kid:
            continue
        parsed[kid] = RSAAlgorithm.from_jwk(key)
    return parsed


def get_apple_public_key(kid: str):
    global _cached_keys, _cache_expires_at

    now = time.time()
    if now >= _cache_expires_at or not _cached_keys:
        try:
            _cached_keys = _fetch_apple_keys()
            _cache_expires_at = now + _CACHE_TTL_SECONDS
        except Exception as exc:
            logger.error("Failed to refresh Apple JWK cache: %s", exc)
            # If refresh fails but cache exists, keep using stale keys.
            if not _cached_keys:
                raise

    return _cached_keys.get(kid)
