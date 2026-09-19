"""card identity, multi provider external ids and market data isolation

Revision ID: 2026_09_18_0003
Revises: 2026_09_16_0002
Create Date: 2026-09-18 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '2026_09_18_0003'
down_revision: Union[str, None] = '2026_09_16_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabela player_cards (CardVersion canônica e desacoplada de plataforma)
    op.create_table(
        'player_cards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('player_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('game_version', sa.String(20), nullable=False, server_default='FC27'),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('position', sa.String(10), nullable=True),
        sa.Column('rarity', sa.String(50), nullable=True),
        sa.Column('club', sa.String(100), nullable=True),
        sa.Column('league', sa.String(100), nullable=True),
        sa.Column('nation', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('data_origin', sa.String(20), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_player_cards_player_id', 'player_cards', ['player_id'])
    op.create_index('ix_player_cards_rating', 'player_cards', ['rating'])

    # 2. Tabela card_external_ids (Suporte extensível a múltiplos provedores de mercado)
    op.create_table(
        'card_external_ids',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('card_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('player_cards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('external_id', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('provider', 'external_id', name='uq_card_external_provider_id'),
        sa.UniqueConstraint('card_id', 'provider', name='uq_card_provider'),
    )
    op.create_index('ix_card_external_ids_card_id', 'card_external_ids', ['card_id'])
    op.create_index('ix_card_external_ids_provider', 'card_external_ids', ['provider'])

    # 3. Migração 1-para-1 dos dados legados de players para player_cards (usando id = players.id)
    op.execute("""
        INSERT INTO player_cards (id, player_id, game_version, rating, position, rarity, club, league, nation, is_active, data_origin, created_at, updated_at)
        SELECT id, id, 'FC27', COALESCE(rating, 80), position, rarity, club, league, nation, true, data_origin, created_at, updated_at
        FROM players
        ON CONFLICT (id) DO NOTHING;
    """)

    # 4. Atualização de price_observations
    op.add_column('price_observations', sa.Column('card_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('price_observations', sa.Column('platform', sa.String(20), server_default='console', nullable=False))
    op.execute("UPDATE price_observations SET card_id = player_id WHERE card_id IS NULL;")
    op.alter_column('price_observations', 'card_id', nullable=False)
    op.create_foreign_key('fk_price_observations_card_id', 'price_observations', 'player_cards', ['card_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_price_observations_card_id', 'price_observations', ['card_id'])
    op.alter_column('price_observations', 'player_id', nullable=True)

    # 5. Atualização de market_opportunities
    op.add_column('market_opportunities', sa.Column('card_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('market_opportunities', sa.Column('platform', sa.String(20), server_default='console', nullable=False))
    op.execute("UPDATE market_opportunities SET card_id = player_id WHERE card_id IS NULL;")
    op.alter_column('market_opportunities', 'card_id', nullable=False)
    op.create_foreign_key('fk_market_opportunities_card_id', 'market_opportunities', 'player_cards', ['card_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_market_opportunities_card_id', 'market_opportunities', ['card_id'])
    op.alter_column('market_opportunities', 'player_id', nullable=True)

    # 6. Atualização de trades
    op.add_column('trades', sa.Column('card_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE trades SET card_id = player_id WHERE card_id IS NULL;")
    op.alter_column('trades', 'card_id', nullable=False)
    op.create_foreign_key('fk_trades_card_id', 'trades', 'player_cards', ['card_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_trades_card_id', 'trades', ['card_id'])
    op.alter_column('trades', 'player_id', nullable=True)

    # 7. Atualização de action_recommendations com Card Identity Snapshot
    op.add_column('action_recommendations', sa.Column('card_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('action_recommendations', sa.Column('card_version_name', sa.String(50), nullable=True))
    op.add_column('action_recommendations', sa.Column('card_club', sa.String(100), nullable=True))
    op.add_column('action_recommendations', sa.Column('card_league', sa.String(100), nullable=True))
    op.add_column('action_recommendations', sa.Column('card_position', sa.String(10), nullable=True))
    op.add_column('action_recommendations', sa.Column('card_platform', sa.String(20), server_default='console', nullable=True))
    op.execute("UPDATE action_recommendations SET card_id = player_id WHERE card_id IS NULL;")
    op.execute("""
        UPDATE action_recommendations r
        SET card_version_name = c.rarity,
            card_club = c.club,
            card_league = c.league,
            card_position = c.position,
            card_platform = 'console'
        FROM player_cards c
        WHERE r.card_id = c.id;
    """)
    op.alter_column('action_recommendations', 'card_id', nullable=False)
    op.create_foreign_key('fk_action_recommendations_card_id', 'action_recommendations', 'player_cards', ['card_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_action_recommendations_card_id', 'action_recommendations', ['card_id'])
    op.alter_column('action_recommendations', 'player_id', nullable=True)


def downgrade() -> None:
    # 7. Reversão action_recommendations
    op.drop_constraint('fk_action_recommendations_card_id', 'action_recommendations', type_='foreignkey')
    op.drop_index('ix_action_recommendations_card_id', 'action_recommendations')
    op.drop_column('action_recommendations', 'card_platform')
    op.drop_column('action_recommendations', 'card_position')
    op.drop_column('action_recommendations', 'card_league')
    op.drop_column('action_recommendations', 'card_club')
    op.drop_column('action_recommendations', 'card_version_name')
    op.drop_column('action_recommendations', 'card_id')
    op.alter_column('action_recommendations', 'player_id', nullable=False)

    # 6. Reversão trades
    op.drop_constraint('fk_trades_card_id', 'trades', type_='foreignkey')
    op.drop_index('ix_trades_card_id', 'trades')
    op.drop_column('trades', 'card_id')
    op.alter_column('trades', 'player_id', nullable=False)

    # 5. Reversão market_opportunities
    op.drop_constraint('fk_market_opportunities_card_id', 'market_opportunities', type_='foreignkey')
    op.drop_index('ix_market_opportunities_card_id', 'market_opportunities')
    op.drop_column('market_opportunities', 'platform')
    op.drop_column('market_opportunities', 'card_id')
    op.alter_column('market_opportunities', 'player_id', nullable=False)

    # 4. Reversão price_observations
    op.drop_constraint('fk_price_observations_card_id', 'price_observations', type_='foreignkey')
    op.drop_index('ix_price_observations_card_id', 'price_observations')
    op.drop_column('price_observations', 'platform')
    op.drop_column('price_observations', 'card_id')
    op.alter_column('price_observations', 'player_id', nullable=False)

    # 2. Reversão card_external_ids
    op.drop_table('card_external_ids')

    # 1. Reversão player_cards
    op.drop_table('player_cards')
