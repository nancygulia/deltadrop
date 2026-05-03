"""
Run once to create all tables and seed the admin user.
Usage: python scripts/init_db.py
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.session import engine, Base
from app.core.config import settings
from app.core.security import hash_password

import app.models.user    # noqa — register all models
import app.models.product # noqa


async def main():
    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created")

    from app.db.session import AsyncSessionLocal
    from app.models.user import User, UserRole
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        if result.scalar_one_or_none():
            print(f"ℹ️  Admin already exists: {settings.ADMIN_EMAIL}")
        else:
            db.add(User(
                email         = settings.ADMIN_EMAIL,
                username      = "admin",
                password_hash = hash_password(settings.ADMIN_PASSWORD),
                full_name     = "DeltaDrop Admin",
                role          = UserRole.admin,
            ))
            await db.commit()
            print(f"✅ Admin created: {settings.ADMIN_EMAIL} / {settings.ADMIN_PASSWORD}")

    await engine.dispose()
    print("✅ Done. Run: uvicorn app.main:app --reload --port 8000")


if __name__ == "__main__":
    asyncio.run(main())
