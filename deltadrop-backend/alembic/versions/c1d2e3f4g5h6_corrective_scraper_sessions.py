"""corrective migration for scraper sessions

Revision ID: c1d2e3f4g5h6
Revises: b7c8d9e0f1a2
Create Date: 2026-04-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4g5h6"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing indexes for better performance
    op.create_index("ix_scraper_sessions_domain", "scraper_sessions", ["domain"], unique=True)
    op.create_index("ix_scraper_sessions_status", "scraper_sessions", ["status"])
    
    # Ensure proper defaults for existing records
    op.execute("""
        UPDATE scraper_sessions 
        SET successful_uses = COALESCE(successful_uses, 0),
            failed_uses = COALESCE(failed_uses, 0),
            login_attempts = COALESCE(login_attempts, 0)
        WHERE successful_uses IS NULL OR failed_uses IS NULL OR login_attempts IS NULL
    """)
    
    # Set default status for any NULL values
    op.execute("""
        UPDATE scraper_sessions 
        SET status = 'pending' 
        WHERE status IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_scraper_sessions_status", table_name="scraper_sessions")
    op.drop_index("ix_scraper_sessions_domain", table_name="scraper_sessions")
