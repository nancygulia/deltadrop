"""fix in_stock not-null constraint and patch nulls to true

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-04-24

Root cause: SerpAPI scraper was returning None for ambiguous stock status,
which was being written directly to the NOT NULL column in_stock.
This migration patches all existing NULL rows and enforces the DB default.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'a1b2c3d4e5f6'
down_revision = 'f7192d204668'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Patch any existing NULL rows to TRUE so the NOT NULL constraint passes
    op.execute(
        "UPDATE retailer_listings SET in_stock = TRUE WHERE in_stock IS NULL"
    )
    op.execute(
        "UPDATE price_history SET in_stock = TRUE WHERE in_stock IS NULL"
    )

    # 2. Ensure column has a server-side default so future inserts without an
    #    explicit value still get TRUE instead of NULL
    op.alter_column(
        'retailer_listings', 'in_stock',
        existing_type=sa.Boolean(),
        server_default=sa.text('TRUE'),
        nullable=True,
    )
    op.alter_column(
        'price_history', 'in_stock',
        existing_type=sa.Boolean(),
        server_default=sa.text('TRUE'),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'retailer_listings', 'in_stock',
        existing_type=sa.Boolean(),
        server_default=None,
        nullable=True,
    )
    op.alter_column(
        'price_history', 'in_stock',
        existing_type=sa.Boolean(),
        server_default=None,
        nullable=True,
    )
