"""align scraper_sessions schema to ORM

Revision ID: b7c8d9e0f1a2
Revises: 18c6f4cb77c3
Create Date: 2026-04-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "18c6f4cb77c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("scraper_sessions", "cookies_encrypted", new_column_name="cookies_enc")
    op.alter_column("scraper_sessions", "last_login_at", new_column_name="logged_in_at")

    op.add_column("scraper_sessions", sa.Column("bot_email", sa.String(length=500), nullable=True))
    op.add_column("scraper_sessions", sa.Column("bot_phone", sa.String(length=200), nullable=True))
    op.add_column("scraper_sessions", sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("scraper_sessions", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("scraper_sessions", sa.Column("successful_uses", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scraper_sessions", sa.Column("failed_uses", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scraper_sessions", sa.Column("login_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scraper_sessions", sa.Column("notes", sa.Text(), nullable=True))

    op.drop_column("scraper_sessions", "is_active")
    op.drop_column("scraper_sessions", "error_count")


def downgrade() -> None:
    op.add_column("scraper_sessions", sa.Column("error_count", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("scraper_sessions", sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")))
    op.drop_column("scraper_sessions", "notes")
    op.drop_column("scraper_sessions", "login_attempts")
    op.drop_column("scraper_sessions", "failed_uses")
    op.drop_column("scraper_sessions", "successful_uses")
    op.drop_column("scraper_sessions", "last_checked_at")
    op.drop_column("scraper_sessions", "last_used_at")
    op.drop_column("scraper_sessions", "bot_phone")
    op.drop_column("scraper_sessions", "bot_email")
    op.alter_column("scraper_sessions", "logged_in_at", new_column_name="last_login_at")
    op.alter_column("scraper_sessions", "cookies_enc", new_column_name="cookies_encrypted")
