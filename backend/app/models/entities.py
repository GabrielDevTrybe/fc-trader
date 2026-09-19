import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid():
    return uuid.uuid4()


class Player(Base):
    """Representa a entidade humana/atleta no mundo real."""
    __tablename__ = "players"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(100), index=True, nullable=False)
    nation = Column(String(100), nullable=True)
    # Colunas legadas mantidas para retrocompatibilidade no banco
    rating = Column(Integer, index=True, nullable=True)
    position = Column(String(10), nullable=True)
    rarity = Column(String(50), nullable=True)
    league = Column(String(100), nullable=True)
    club = Column(String(100), nullable=True)
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relacionamento com as versões negociáveis de cartas do atleta
    cards = relationship("PlayerCard", back_populates="player", cascade="all, delete-orphan")


class PlayerCard(Base):
    """Representa uma versão de carta negociável específica (CardVersion / PlayerItem).

    Exemplo:
      Atleta Exemplo -> Gold 82 Clube A
      Atleta Exemplo -> Gold 82 Clube B
    A plataforma pertence à observação de mercado, não à identidade intrínseca da carta.
    """
    __tablename__ = "player_cards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    game_version = Column(String(20), nullable=False, default="FC27", server_default="FC27")
    rating = Column(Integer, index=True, nullable=False)
    position = Column(String(10), nullable=True)
    rarity = Column(String(50), nullable=True)       # Gold Rare, Gold Common, TOTW, Hero, etc.
    club = Column(String(100), nullable=True)
    league = Column(String(100), nullable=True)
    nation = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    player = relationship("Player", back_populates="cards")
    external_ids = relationship("CardExternalId", back_populates="card", cascade="all, delete-orphan")
    observations = relationship("PriceObservation", back_populates="card", cascade="all, delete-orphan")
    opportunities = relationship("MarketOpportunity", back_populates="card", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="card", cascade="all, delete-orphan")
    recommendations = relationship("ActionRecommendation", back_populates="card", cascade="all, delete-orphan")
    snapshots = relationship("MarketSnapshot", back_populates="card", cascade="all, delete-orphan")


class MarketSnapshot(Base):
    """Snapshot estatístico determinístico de inteligência de mercado para uma CardVersion e plataforma."""
    __tablename__ = "market_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    card_id = Column(UUID(as_uuid=True), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(20), nullable=False, default="console", server_default="console")
    sample_count = Column(Integer, nullable=False, default=0)
    valid_sample_count = Column(Integer, nullable=False, default=0)
    min_price = Column(Integer, nullable=True)
    max_price = Column(Integer, nullable=True)
    median_price = Column(Integer, nullable=True)
    p20_price = Column(Integer, nullable=True)
    p80_price = Column(Integer, nullable=True)
    robust_mean = Column(Float, nullable=True)
    std_dev = Column(Float, nullable=True)
    dispersion_ratio = Column(Float, nullable=True)
    estimated_market_price = Column(Integer, nullable=True)
    conservative_buy_price = Column(Integer, nullable=True)
    conservative_sell_price = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=False, default=0.0)
    confidence_level = Column(String(20), nullable=False, default="LOW")
    freshness_status = Column(String(20), nullable=False, default="FRESH")
    newest_observation_age_seconds = Column(Integer, nullable=True)
    trend = Column(String(20), nullable=False, default="NEUTRAL")
    data_quality = Column(String(30), nullable=False, default="OK")
    calculated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")

    # Relationships
    card = relationship("PlayerCard", back_populates="snapshots")


class CardExternalId(Base):
    """Mapeia identificadores externos fornecidos por diferentes provedores de mercado autorizados."""
    __tablename__ = "card_external_ids"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    card_id = Column(UUID(as_uuid=True), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)  # ex: provider_a, provider_b
    external_id = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "external_id", name="uq_card_external_provider_id"),
        UniqueConstraint("card_id", "provider", name="uq_card_provider"),
    )

    card = relationship("PlayerCard", back_populates="external_ids")


class PriceObservation(Base):
    """Observação de preço no mercado vinculada à versão específica da carta."""
    __tablename__ = "price_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    card_id = Column(UUID(as_uuid=True), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=True, index=True)
    price = Column(Integer, nullable=False)
    observation_type = Column(String(30), nullable=False, default="buy_now")  # buy_now, bid, sale_estimate
    platform = Column(String(20), nullable=False, default="console", server_default="console")  # console, pc
    source = Column(String(50), nullable=False, default="manual")  # Proveniência: manual, csv, USER_MARKET_CHECK
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    card = relationship("PlayerCard", back_populates="observations")
    player = relationship("Player")


class MarketOpportunity(Base):
    """Oportunidade de mercado detectada para uma versão específica de carta."""
    __tablename__ = "market_opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    card_id = Column(UUID(as_uuid=True), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=True, index=True)
    observed_price = Column(Integer, nullable=False)
    market_price = Column(Integer, nullable=False)
    max_buy_price = Column(Integer, nullable=False)
    target_sell_price = Column(Integer, nullable=False)
    estimated_profit = Column(Integer, nullable=False)
    roi = Column(Float, nullable=False)
    confidence = Column(String(20), nullable=False)
    liquidity_score = Column(Integer, nullable=False)
    opportunity_score = Column(Float, nullable=False, index=True)
    strategy_type = Column(String(30), nullable=False, default="QUICK_FLIP", server_default="QUICK_FLIP")
    capital_efficiency = Column(Float, nullable=True)
    expected_holding_time_minutes = Column(Integer, nullable=True)
    platform = Column(String(20), nullable=False, default="console", server_default="console")
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    detected_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    card = relationship("PlayerCard", back_populates="opportunities")
    player = relationship("Player")


class TradingGoal(Base):
    __tablename__ = "trading_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    starting_balance = Column(Integer, nullable=False)
    target_balance = Column(Integer, nullable=False)
    current_balance = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE", server_default="ACTIVE")  # ACTIVE, COMPLETED, CLOSED
    is_paper = Column(Boolean, nullable=False, default=False, server_default="false")
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    trades = relationship("Trade", back_populates="trading_goal")
    recommendations = relationship("ActionRecommendation", back_populates="trading_goal")


class ActionRecommendation(Base):
    """Recomendação executável snapshotada para uma versão específica de carta."""
    __tablename__ = "action_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    trading_goal_id = Column(UUID(as_uuid=True), ForeignKey("trading_goals.id", ondelete="SET NULL"), nullable=True, index=True)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("market_opportunities.id", ondelete="SET NULL"), nullable=True)
    card_id = Column(UUID(as_uuid=True), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=True, index=True)

    action_type = Column(String(30), nullable=False)       # MASS_BID, SNIPE_BUY_NOW, CONSERVATIVE_FLIP
    strategy_name = Column(String(50), nullable=False)     # Mass Bidding, Sniping, Flip Conservador
    player_name = Column(String(100), nullable=False)
    player_rating = Column(Integer, nullable=False)

    # Identidade Inequívoca da Versão da Carta
    card_version_name = Column(String(50), nullable=True)  # Gold, TOTW, etc.
    card_club = Column(String(100), nullable=True)          # Benfica, Bayern München, etc.
    card_league = Column(String(100), nullable=True)        # Liga Portugal, Bundesliga, etc.
    card_position = Column(String(10), nullable=True)       # CDM, CM, etc.
    card_platform = Column(String(20), nullable=True, default="console")

    max_buy_price = Column(Integer, nullable=False)
    target_sell_price = Column(Integer, nullable=False)
    recommended_quantity = Column(Integer, nullable=False)
    capital_limit = Column(Integer, nullable=False)
    estimated_profit_per_card = Column(Integer, nullable=False)
    estimated_total_profit = Column(Integer, nullable=False)
    estimated_roi = Column(Float, nullable=False)

    # Métricas Estruturadas no Teto Máximo de Compra (Cenário Conservador)
    profit_at_max_buy = Column(Integer, nullable=True)
    roi_at_max_buy = Column(Float, nullable=True)

    # Snapshot Quantitativo Auditável
    snapshot_market_price = Column(Integer, nullable=False)
    snapshot_observed_price = Column(Integer, nullable=False)
    snapshot_liquidity_score = Column(Integer, nullable=False)
    snapshot_confidence = Column(String(20), nullable=False)
    snapshot_opportunity_score = Column(Float, nullable=False)
    snapshot_sample_count = Column(Integer, nullable=False)
    snapshot_available_cash = Column(Integer, nullable=False)

    why_explanation = Column(Text, nullable=False)
    urgency = Column(String(20), nullable=False, default="NORMAL", server_default="NORMAL")
    status = Column(String(20), nullable=False, default="active", server_default="active")  # active, executed, missed, expired
    is_paper = Column(Boolean, nullable=False, default=False, server_default="false")
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Auditoria e Rastreabilidade da Fase 3A
    market_snapshot_id = Column(UUID(as_uuid=True), ForeignKey("market_snapshots.id", ondelete="SET NULL"), nullable=True)
    market_data_age_seconds = Column(Integer, nullable=True)
    strategy_type = Column(String(30), nullable=False, default="QUICK_FLIP", server_default="QUICK_FLIP")
    capital_efficiency = Column(Float, nullable=True)
    expected_holding_time_minutes = Column(Integer, nullable=True)
    no_action_reason_code = Column(String(50), nullable=True)

    # Relationships
    card = relationship("PlayerCard", back_populates="recommendations")
    player = relationship("Player")
    trading_goal = relationship("TradingGoal", back_populates="recommendations")
    market_snapshot = relationship("MarketSnapshot")
    feedbacks = relationship("ActionFeedback", back_populates="recommendation", cascade="all, delete-orphan")


class ActionFeedback(Base):
    __tablename__ = "action_feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("action_recommendations.id", ondelete="CASCADE"), nullable=False, index=True)
    action_result = Column(String(30), nullable=False)  # BOUGHT, MISSED, CANCELLED
    effective_price = Column(Integer, nullable=True)
    quantity_bought = Column(Integer, nullable=True)
    missed_reason = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    recommendation = relationship("ActionRecommendation", back_populates="feedbacks")


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    card_id = Column(UUID(as_uuid=True), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=True, index=True)
    trading_goal_id = Column(UUID(as_uuid=True), ForeignKey("trading_goals.id", ondelete="SET NULL"), nullable=True, index=True)
    action_recommendation_id = Column(UUID(as_uuid=True), ForeignKey("action_recommendations.id", ondelete="SET NULL"), nullable=True, index=True)
    buy_price = Column(Integer, nullable=False)
    sell_price = Column(Integer, nullable=True)
    tax = Column(Integer, nullable=True)
    net_received = Column(Integer, nullable=True)
    profit = Column(Integer, nullable=True)
    roi = Column(Float, nullable=True)
    bought_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    sold_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="open")  # open, sold, cancelled
    is_paper_trade = Column(Boolean, nullable=False, default=True)
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    card = relationship("PlayerCard", back_populates="trades")
    player = relationship("Player")
    trading_goal = relationship("TradingGoal", back_populates="trades")


class BankrollHistory(Base):
    __tablename__ = "bankroll_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    balance = Column(Integer, nullable=False)
    reason = Column(String(100), nullable=False)
    is_paper = Column(Boolean, nullable=False, default=False)
    amount = Column(Integer, nullable=True)
    # Tipos de entrada: trade, external_adjustment, initial_deposit, manual_reconciliation
    entry_type = Column(String(30), nullable=False, default="trade", server_default="trade")
    # Subtipos: reward, external_purchase, manual_correction, reconciliation
    adjustment_type = Column(String(50), nullable=True)
    trading_goal_id = Column(UUID(as_uuid=True), ForeignKey("trading_goals.id", ondelete="SET NULL"), nullable=True, index=True)
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
