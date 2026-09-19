"""market intelligence, snapshots, and strategy audit fields

Revision ID: 2026_09_19_0004
Revises: 2026_09_18_0003
Create Date: 2026-09-19 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '2026_09_19_0004'
down_revision: Union[str, None] = '2026_09_18_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabela market_snapshots para auditoria quantitativa de mercado
    op.create_table(
        'market_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('card_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('player_cards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform', sa.String(20), nullable=False, server_default='console'),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('min_price', sa.Integer(), nullable=True),
        sa.Column('max_price', sa.Integer(), nullable=True),
        sa.Column('median_price', sa.Integer(), nullable=True),
        sa.Column('p20_price', sa.Integer(), nullable=True),
        sa.Column('p80_price', sa.Integer(), nullable=True),
        sa.Column('robust_mean', sa.Float(), nullable=True),
        sa.Column('std_dev', sa.Float(), nullable=True),
        sa.Column('dispersion_ratio', sa.Float(), nullable=True),
        sa.Column('estimated_market_price', sa.Integer(), nullable=True),
        sa.Column('conservative_buy_price', sa.Integer(), nullable=True),
        sa.Column('conservative_sell_price', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('confidence_level', sa.String(20), nullable=False, server_default='LOW'),
        sa.Column('freshness_status', sa.String(20), nullable=False, server_default='FRESH'),
        sa.Column('newest_observation_age_seconds', sa.Integer(), nullable=True),
        sa.Column('trend', sa.String(20), nullable=False, server_default='NEUTRAL'),
        sa.Column('data_quality', sa.String(30), nullable=False, server_default='OK'),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('data_origin', sa.String(20), nullable=False, server_default='user'),
    )
    op.create_index('ix_market_snapshots_card_id', 'market_snapshots', ['card_id'])
    op.create_index('ix_market_snapshots_calculated_at', 'market_snapshots', ['calculated_at'])

    # 2. Adiciona campos de estratégia e eficiência a market_opportunities
    op.add_column('market_opportunities', sa.Column('strategy_type', sa.String(30), nullable=False, server_default='QUICK_FLIP'))
    op.add_column('market_opportunities', sa.Column('capital_efficiency', sa.Float(), nullable=True))
    op.add_column('market_opportunities', sa.Column('expected_holding_time_minutes', sa.Integer(), nullable=True))

    # 3. Adiciona campos de auditoria e estratégia a action_recommendations
    op.add_column('action_recommendations', sa.Column('market_snapshot_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('action_recommendations', sa.Column('market_data_age_seconds', sa.Integer(), nullable=True))
    op.add_column('action_recommendations', sa.Column('strategy_type', sa.String(30), nullable=False, server_default='QUICK_FLIP'))
    op.add_column('action_recommendations', sa.Column('capital_efficiency', sa.Float(), nullable=True))
    op.add_column('action_recommendations', sa.Column('expected_holding_time_minutes', sa.Integer(), nullable=True))
    op.add_column('action_recommendations', sa.Column('no_action_reason_code', sa.String(50), nullable=True))
    op.create_foreign_key('fk_action_recommendations_snapshot', 'action_recommendations', 'market_snapshots', ['market_snapshot_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_action_recommendations_snapshot_id', 'action_recommendations', ['market_snapshot_id'])


def downgrade() -> None:
    # 3. Reversão action_recommendations
    op.drop_constraint('fk_action_recommendations_snapshot', 'action_recommendations', type_='foreignkey')
    op.drop_index('ix_action_recommendations_snapshot_id', 'action_recommendations')
    op.drop_column('action_recommendations', 'no_action_reason_code')
    op.drop_column('action_recommendations', 'expected_holding_time_minutes')
    op.drop_column('action_recommendations', 'capital_efficiency')
    op.drop_column('action_recommendations', 'strategy_type')
    op.drop_column('action_recommendations', 'market_data_age_seconds')
    op.drop_column('action_recommendations', 'market_snapshot_id')

    # 2. Reversão market_opportunities
    op.drop_column('market_opportunities', 'expected_holding_time_minutes')
    op.drop_column('market_opportunities', 'capital_efficiency')
    op.drop_column('market_opportunities', 'strategy_type')

    # 1. Reversão market_snapshots
    op.drop_table('market_snapshots')
