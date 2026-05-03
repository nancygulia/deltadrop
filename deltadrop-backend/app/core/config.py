"""
DeltaDrop Settings — loaded from .env with strict production validation.

In production (APP_ENV=production):
  - Missing JWT_SECRET_KEY → FATAL: server refuses to start
  - Missing DATABASE_URL   → FATAL: server refuses to start
  - Missing GEMINI_API_KEY → WARNING (AI features degrade to fallback)

In development:
  - All warnings are logged but the server still boots
"""
import sys
import logging
from pydantic_settings import BaseSettings
from functools import lru_cache

logger = logging.getLogger(__name__)

# ── Known-weak secrets that must be rejected in production ────────────────────
_WEAK_JWT_SECRETS = frozenset({
    "",
    "change-this-secret",
    "change-this-to-a-very-long-random-secret",
    "secret",
    "jwt-secret",
})


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    ADMIN_EMAIL: str = "admin@deltadrop.in"
    ADMIN_PASSWORD: str = "Admin@123!"

    # Database
    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""

    # JWT — MUST be set in .env; never committed to source control
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 900

    # Scraper
    SCRAPER_HEADLESS: bool = True
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_TIMEOUT_MS: int = 30000
    SCRAPER_CONCURRENCY: int = 3

    # ML
    ML_MODEL_PATH: str = "app/ml/models/price_predictor.pkl"
    ML_MIN_HISTORY_POINTS: int = 7

    # AI / Google Gemini (backend-only, never expose to frontend)
    GEMINI_API_KEY: str = ""   # set in .env

    # Search APIs
    SERPAPI_API_KEY: str = ""   # set in .env — sign up at serpapi.com
    SCRAPER_API_KEY: str = ""   # set in .env — sign up at scraperapi.com
    SCRAPE_DO_API_KEY: str = "" # set in .env — sign up at scrape.do

    # Google OAuth (for Sign In with Google)
    GOOGLE_CLIENT_ID: str = ""  # set in .env — from Google Cloud Console
    APPLE_BUNDLE_ID: str = ""   # set in .env — native app bundle identifier

    # Email (SMTP)
    SMTP_HOST: str = "sandbox.smtp.mailtrap.io"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM_EMAIL: str = "noreply@deltadrop.in"
    SMTP_FROM_NAME: str = "DeltaDrop"

    # Password Reset
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    FRONTEND_RESET_URL: str = "http://localhost:5173/reset-password"

    # Amazon Product Advertising API
    AMAZON_PA_ACCESS_KEY:   str = ""
    AMAZON_PA_SECRET_KEY:   str = ""
    AMAZON_PA_ASSOCIATE_TAG: str = ""

    # Session store encryption key (AES-256)
    SECRET_KEY: str = ""

    # Cache freshness
    CACHE_STALE_THRESHOLD_MINUTES: int = 30
    CACHE_EXPIRE_THRESHOLD_HOURS: int = 24

    model_config = {"env_file": ".env", "extra": "ignore"}


def _validate_settings(s: Settings) -> None:
    """
    Validate critical environment variables.
    In production → missing required vars crash the process.
    In development → warnings are logged.
    """
    is_prod = s.APP_ENV.lower() in ("production", "prod")
    errors: list[str] = []
    warnings: list[str] = []

    # ── DATABASE_URL ──────────────────────────────────────────────────────
    if not s.DATABASE_URL:
        errors.append(
            "DATABASE_URL is not set. "
            "Set DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/deltadrop in .env"
        )

    # ── JWT_SECRET_KEY ────────────────────────────────────────────────────
    if s.JWT_SECRET_KEY.lower().strip() in _WEAK_JWT_SECRETS:
        errors.append(
            "JWT_SECRET_KEY is missing or too weak. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\" "
            "and add it to your .env file."
        )
    elif len(s.JWT_SECRET_KEY) < 32:
        errors.append(
            f"JWT_SECRET_KEY is only {len(s.JWT_SECRET_KEY)} characters — "
            f"minimum 32 characters required for HS256 security."
        )

    # ── GEMINI_API_KEY (warning only — fallback logic exists) ─────────────
    if not s.GEMINI_API_KEY:
        warnings.append(
            "GEMINI_API_KEY is not set. "
            "AI features will use deterministic fallback logic. "
            "Set GEMINI_API_KEY in .env for full Gemini-powered intelligence."
        )

    # ── SECRET_KEY ────────────────────────────────────────────────────────
    if not s.SECRET_KEY or s.SECRET_KEY == "deltadrop-change-this-in-production":
        import secrets
        object.__setattr__(s, "SECRET_KEY", secrets.token_urlsafe(32))
        if is_prod:
            warnings.append("SECRET_KEY auto-generated. Set a strong SECRET_KEY in .env for production.")

    # ── Log warnings ──────────────────────────────────────────────────────
    for w in warnings:
        logger.warning(f"⚠️  {w}")

    # ── In production, errors are fatal ───────────────────────────────────
    if errors:
        for e in errors:
            logger.critical(f"🚨 FATAL: {e}")

        if is_prod:
            print("\n" + "=" * 70)
            print("  DELTADROP STARTUP FAILED -- MISSING REQUIRED CONFIGURATION")
            print("=" * 70)
            for e in errors:
                print(f"  [X] {e}")
            print("=" * 70 + "\n")
            sys.exit(1)
        else:
            # Development: log errors but allow boot
            for e in errors:
                logger.error(f"❌ [DEV MODE] {e}")
            logger.warning(
                "🔧 Server starting in DEVELOPMENT mode with incomplete config. "
                "Fix the above before deploying to production."
            )


@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    _validate_settings(s)
    return s


settings = get_settings()
