"""final_hardening_v2

Revision ID: f7192d204668
Revises: 8058a8219ce4
Create Date: 2026-04-18 00:29:18.688836
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f7192d204668'
down_revision: Union[str, None] = '8058a8219ce4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'scraper_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('domain', sa.String(255), nullable=False, unique=True),
        sa.Column('cookies_encrypted', sa.Text()),
        sa.Column('status', sa.String(50), default='active'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('error_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    op.create_table(
        'rate_limit_state',
        sa.Column('key', sa.String(255), primary_key=True),
        sa.Column('last_triggered', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hits', sa.Integer(), default=1),
    )
    op.create_table(
        'used_reset_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('used_at', sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table('used_reset_tokens')
    op.drop_table('rate_limit_state')
    op.drop_table('scraper_sessions')
