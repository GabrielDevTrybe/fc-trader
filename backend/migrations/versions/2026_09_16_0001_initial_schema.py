"""initial schema for fc trader

Revision ID: 2026_09_16_0001
Revises: 
Create Date: 2026-09-16 16:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '2026_09_16_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabela players
    op.create_table(
        'players',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('position', sa.String(10), nullable=True),
        sa.Column('rarity', sa.String(50), nullable=True),
        sa.Column('league', sa.String(100), nullable=True),
        sa.Column('club', sa.String(100), nullable=True),
        sa.Column('nation', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_players_name', 'players', ['name'])
    op.create_index('ix_players_rating', 'players', ['rating'])

    # 2. Tabela price_observations
    op.create_table(
        'price_observations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('player_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('observation_type', sa.String(30), nullable=False, server_default='buy_now'),
        sa.Column('source', sa.String(50), nullable=False, server_default='manual'),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_price_observations_player_id', 'price_observations', ['player_id'])
    op.create_index('ix_price_observations_observed_at', 'price_observations', ['observed_at'])

    # 3. Tabela market_opportunities
    op.create_table(
        'market_opportunities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('player_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('observed_price', sa.Integer(), nullable=False),
        sa.Column('market_price', sa.Integer(), nullable=False),
        sa.Column('max_buy_price', sa.Integer(), nullable=False),
        sa.Column('target_sell_price', sa.Integer(), nullable=False),
        sa.Column('estimated_profit', sa.Integer(), nullable=False),
        sa.Column('roi', sa.Float(), nullable=False),
        sa.Column('confidence', sa.String(20), nullable=False),
        sa.Column('liquidity_score', sa.Integer(), nullable=False),
        sa.Column('opportunity_score', sa.Float(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_market_opportunities_player_id', 'market_opportunities', ['player_id'])
    op.create_index('ix_market_opportunities_opportunity_score', 'market_opportunities', ['opportunity_score'])

    # 4. Tabela trades
    op.create_table(
        'trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('player_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('buy_price', sa.Integer(), nullable=False),
        sa.Column('sell_price', sa.Integer(), nullable=True),
        sa.Column('tax', sa.Integer(), nullable=True),
        sa.Column('net_received', sa.Integer(), nullable=True),
        sa.Column('profit', sa.Integer(), nullable=True),
        sa.Column('roi', sa.Float(), nullable=True),
        sa.Column('bought_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('sold_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        sa.Column('is_paper_trade', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_trades_player_id', 'trades', ['player_id'])

    # 5. Tabela bankroll_history
    op.create_table(
        'bankroll_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('balance', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(100), nullable=False),
        sa.Column('is_paper', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('bankroll_history')
    op.drop_table('trades')
    op.drop_table('market_opportunities')
    op.drop_table('price_observations')
    op.drop_table('players')
