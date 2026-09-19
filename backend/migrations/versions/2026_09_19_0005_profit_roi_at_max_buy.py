"""add profit_at_max_buy and roi_at_max_buy to action_recommendations

Revision ID: 2026_09_19_0005
Revises: 2026_09_19_0004
Create Date: 2026-09-19 14:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '2026_09_19_0005'
down_revision: Union[str, None] = '2026_09_19_0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('action_recommendations', sa.Column('profit_at_max_buy', sa.Integer(), nullable=True))
    op.add_column('action_recommendations', sa.Column('roi_at_max_buy', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('action_recommendations', 'roi_at_max_buy')
    op.drop_column('action_recommendations', 'profit_at_max_buy')
