"""phase 2 goals and actions

Revision ID: 2026_09_16_0002
Revises: 2026_09_16_0001
Create Date: 2026-09-16 17:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '2026_09_16_0002'
down_revision: Union[str, None] = '2026_09_16_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabela trading_goals
    op.create_table(
        'trading_goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('starting_balance', sa.Integer(), nullable=False),
        sa.Column('target_balance', sa.Integer(), nullable=False),
        sa.Column('current_balance', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),
        sa.Column('is_paper', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('data_origin', sa.String(20), nullable=False, server_default='user'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_trading_goals_status', 'trading_goals', ['status'])

    # 2. Tabela action_recommendations
    op.create_table(
        'action_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('trading_goal_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('trading_goals.id', ondelete='SET NULL'), nullable=True),
        sa.Column('opportunity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('market_opportunities.id', ondelete='SET NULL'), nullable=True),
        sa.Column('player_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.String(30), nullable=False),
        sa.Column('strategy_name', sa.String(50), nullable=False),
        sa.Column('player_name', sa.String(100), nullable=False),
        sa.Column('player_rating', sa.Integer(), nullable=False),
        sa.Column('max_buy_price', sa.Integer(), nullable=False),
        sa.Column('target_sell_price', sa.Integer(), nullable=False),
        sa.Column('recommended_quantity', sa.Integer(), nullable=False),
        sa.Column('capital_limit', sa.Integer(), nullable=False),
        sa.Column('estimated_profit_per_card', sa.Integer(), nullable=False),
        sa.Column('estimated_total_profit', sa.Integer(), nullable=False),
        sa.Column('estimated_roi', sa.Float(), nullable=False),
        sa.Column('snapshot_market_price', sa.Integer(), nullable=False),
        sa.Column('snapshot_observed_price', sa.Integer(), nullable=False),
        sa.Column('snapshot_liquidity_score', sa.Integer(), nullable=False),
        sa.Column('snapshot_confidence', sa.String(20), nullable=False),
        sa.Column('snapshot_opportunity_score', sa.Float(), nullable=False),
        sa.Column('snapshot_sample_count', sa.Integer(), nullable=False),
        sa.Column('snapshot_available_cash', sa.Integer(), nullable=False),
        sa.Column('why_explanation', sa.Text(), nullable=False),
        sa.Column('urgency', sa.String(20), nullable=False, server_default='NORMAL'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('is_paper', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('data_origin', sa.String(20), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_action_recommendations_trading_goal_id', 'action_recommendations', ['trading_goal_id'])
    op.create_index('ix_action_recommendations_player_id', 'action_recommendations', ['player_id'])
    op.create_index('ix_action_recommendations_status', 'action_recommendations', ['status'])

    # 3. Tabela action_feedbacks
    op.create_table(
        'action_feedbacks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('recommendation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('action_recommendations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_result', sa.String(30), nullable=False),
        sa.Column('effective_price', sa.Integer(), nullable=True),
        sa.Column('quantity_bought', sa.Integer(), nullable=True),
        sa.Column('missed_reason', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('data_origin', sa.String(20), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_action_feedbacks_recommendation_id', 'action_feedbacks', ['recommendation_id'])

    # 4. Adicionar colunas a tabelas existentes
    op.add_column('players', sa.Column('data_origin', sa.String(20), server_default='user', nullable=False))
    op.add_column('price_observations', sa.Column('data_origin', sa.String(20), server_default='user', nullable=False))
    op.add_column('market_opportunities', sa.Column('data_origin', sa.String(20), server_default='user', nullable=False))

    op.add_column('trades', sa.Column('trading_goal_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('trading_goals.id', ondelete='SET NULL'), nullable=True))
    op.add_column('trades', sa.Column('action_recommendation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('action_recommendations.id', ondelete='SET NULL'), nullable=True))
    op.add_column('trades', sa.Column('data_origin', sa.String(20), server_default='user', nullable=False))
    op.create_index('ix_trades_trading_goal_id', 'trades', ['trading_goal_id'])

    op.add_column('bankroll_history', sa.Column('amount', sa.Integer(), nullable=True))
    op.add_column('bankroll_history', sa.Column('entry_type', sa.String(30), server_default='trade', nullable=False))
    op.add_column('bankroll_history', sa.Column('adjustment_type', sa.String(50), nullable=True))
    op.add_column('bankroll_history', sa.Column('trading_goal_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('trading_goals.id', ondelete='SET NULL'), nullable=True))
    op.add_column('bankroll_history', sa.Column('data_origin', sa.String(20), server_default='user', nullable=False))
    op.create_index('ix_bankroll_history_trading_goal_id', 'bankroll_history', ['trading_goal_id'])


def downgrade() -> None:
    op.drop_index('ix_bankroll_history_trading_goal_id', 'bankroll_history')
    op.drop_column('bankroll_history', 'data_origin')
    op.drop_column('bankroll_history', 'trading_goal_id')
    op.drop_column('bankroll_history', 'adjustment_type')
    op.drop_column('bankroll_history', 'entry_type')
    op.drop_column('bankroll_history', 'amount')

    op.drop_index('ix_trades_trading_goal_id', 'trades')
    op.drop_column('trades', 'data_origin')
    op.drop_column('trades', 'action_recommendation_id')
    op.drop_column('trades', 'trading_goal_id')

    op.drop_column('market_opportunities', 'data_origin')
    op.drop_column('price_observations', 'data_origin')
    op.drop_column('players', 'data_origin')

    op.drop_table('action_feedbacks')
    op.drop_table('action_recommendations')
    op.drop_table('trading_goals')
