from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def _clean_async_url(url: str) -> tuple[str, dict]:
    """Strip sslmode from URL and return connect_args for asyncpg."""
    connect_args = {}
    if "sslmode=disable" in url:
        url = url.replace("?sslmode=disable", "").replace("&sslmode=disable", "")
        connect_args["ssl"] = False
    elif "sslmode=require" in url:
        url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
        connect_args["ssl"] = True
    return url, connect_args


_db_url, _connect_args = _clean_async_url(settings.DATABASE_URL)

engine = create_async_engine(
    _db_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=(settings.APP_ENV == "development"),
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
