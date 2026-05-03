"""
DeltaDrop Rate Limiting — Simple in-memory IP-based rate limiter.

Uses a sliding window counter per IP. No external dependencies (no Redis required).
Suitable for single-process deployments. For multi-process/multi-node,
swap with a Redis-backed implementation.
"""
import time
import logging
from collections import defaultdict
from functools import wraps

from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sliding-window rate limiter keyed by client IP.

    Usage:
        limiter = RateLimiter()

        @app.post("/login")
        @limiter.limit("login", max_requests=5, window_seconds=60)
        async def login(request: Request, ...):
            ...
    """

    def __init__(self):
        # {bucket_key: [(timestamp, ...),]}
        self._buckets: dict[str, list[float]] = defaultdict(list)
        # Cleanup counter — prune stale entries every N calls
        self._call_count = 0
        self._cleanup_interval = 500

    def _get_client_ip(self, request: Request) -> str:
        """Extract the real client IP, respecting X-Forwarded-For behind a proxy."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _prune_expired(self, key: str, window_seconds: int) -> None:
        """Remove timestamps older than the sliding window."""
        cutoff = time.monotonic() - window_seconds
        self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]

    def _maybe_gc(self) -> None:
        """Periodic garbage collection of empty buckets."""
        self._call_count += 1
        if self._call_count % self._cleanup_interval == 0:
            empty_keys = [k for k, v in self._buckets.items() if not v]
            for k in empty_keys:
                del self._buckets[k]

    def check(self, request: Request, bucket_name: str, max_requests: int, window_seconds: int) -> None:
        """
        Check rate limit. Raises HTTPException(429) if exceeded.
        Call this at the start of any endpoint handler.
        """
        ip = self._get_client_ip(request)
        key = f"{bucket_name}:{ip}"
        now = time.monotonic()

        self._prune_expired(key, window_seconds)
        self._maybe_gc()

        if len(self._buckets[key]) >= max_requests:
            retry_after = int(window_seconds - (now - self._buckets[key][0])) + 1
            logger.warning(
                f"[RATE_LIMIT] {bucket_name} limit exceeded for IP {ip} "
                f"({len(self._buckets[key])}/{max_requests} in {window_seconds}s)"
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "error": True,
                    "message": f"Too many requests. Try again in {retry_after} seconds.",
                    "status_code": 429,
                },
                headers={"Retry-After": str(retry_after)},
            )

        self._buckets[key].append(now)

    def limit(self, bucket_name: str, max_requests: int = 10, window_seconds: int = 60):
        """
        Decorator for rate-limiting endpoint functions.
        The decorated function MUST accept `request: Request` as its first arg.
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Find the Request object in args/kwargs
                request = kwargs.get("request")
                if request is None:
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                if request is None:
                    # Can't rate-limit without a Request, just run the handler
                    return await func(*args, **kwargs)

                self.check(request, bucket_name, max_requests, window_seconds)
                return await func(*args, **kwargs)
            return wrapper
        return decorator


# ── Singleton instance ────────────────────────────────────────────────────────
rate_limiter = RateLimiter()
