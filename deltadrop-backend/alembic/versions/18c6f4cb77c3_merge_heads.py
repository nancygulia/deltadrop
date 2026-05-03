"""merge heads

Revision ID: 18c6f4cb77c3
Revises: a1b2c3d4e5f6, f7192d204668
Create Date: 2026-04-26 00:38:05.998873

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '18c6f4cb77c3'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'f7192d204668')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
