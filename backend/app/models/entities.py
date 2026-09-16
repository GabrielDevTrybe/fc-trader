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
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid():
    return uuid.uuid4()


class Player(Base):
    __tablename__ = "players"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(100), index=True, nullable=False)
    rating = Column(Integer, index=True, nullable=False)
    position = Column(String(10), nullable=True)
    rarity = Column(String(50), nullable=True)
    league = Column(String(100), nullable=True)
    club = Column(String(100), nullable=True)
    nation = Column(String(100), nullable=True)
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    observations = relationship("PriceObservation", back_populates="player", cascade="all, delete-orphan")
    opportunities = relationship("MarketOpportunity", back_populates="player", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="player", cascade="all, delete-orphan")
    recommendations = relationship("ActionRecommendation", back_populates="player", cascade="all, delete-orphan")


class PriceObservation(Base):
    __tablename__ = "price_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    price = Column(Integer, nullable=False)
    observation_type = Column(String(30), nullable=False, default="buy_now")  # buy_now, bid, sale_estimate
    source = Column(String(50), nullable=False, default="manual")
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    player = relationship("Player", back_populates="observations")


class MarketOpportunity(Base):
    __tablename__ = "market_opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    observed_price = Column(Integer, nullable=False)
    market_price = Column(Integer, nullable=False)
    max_buy_price = Column(Integer, nullable=False)
    target_sell_price = Column(Integer, nullable=False)
    estimated_profit = Column(Integer, nullable=False)
    roi = Column(Float, nullable=False)
    confidence = Column(String(20), nullable=False)
    liquidity_score = Column(Integer, nullable=False)
    opportunity_score = Column(Float, nullable=False, index=True)
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    detected_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    player = relationship("Player", back_populates="opportunities")


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
    __tablename__ = "action_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    trading_goal_id = Column(UUID(as_uuid=True), ForeignKey("trading_goals.id", ondelete="SET NULL"), nullable=True, index=True)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("market_opportunities.id", ondelete="SET NULL"), nullable=True)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)

    action_type = Column(String(30), nullable=False)       # MASS_BID, SNIPE_BUY_NOW, CONSERVATIVE_FLIP
    strategy_name = Column(String(50), nullable=False)     # Mass Bidding, Sniping, Flip Conservador
    player_name = Column(String(100), nullable=False)
    player_rating = Column(Integer, nullable=False)
    max_buy_price = Column(Integer, nullable=False)
    target_sell_price = Column(Integer, nullable=False)
    recommended_quantity = Column(Integer, nullable=False)
    capital_limit = Column(Integer, nullable=False)
    estimated_profit_per_card = Column(Integer, nullable=False)
    estimated_total_profit = Column(Integer, nullable=False)
    estimated_roi = Column(Float, nullable=False)

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

    # Relationships
    player = relationship("Player", back_populates="recommendations")
    trading_goal = relationship("TradingGoal", back_populates="recommendations")
    feedbacks = relationship("ActionFeedback", back_populates="recommendation", cascade="all, delete-orphan")


class ActionFeedback(Base):
    __tablename__ = "action_feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("action_recommendations.id", ondelete="CASCADE"), nullable=False, index=True)
    action_result = Column(String(30), nullable=False)  # BOUGHT, MISSED, CANCELLED
    effective_price = Column(Integer, nullable=True)
    quantity_bought = Column(Integer, nullable=True)
    missed_reason = Column(String(50), nullable=True)  # price_rose, no_cards_found, lost_bids, given_up, other
    notes = Column(Text, nullable=True)
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())

    # Relationships
    recommendation = relationship("ActionRecommendation", back_populates="feedbacks")


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
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
    player = relationship("Player", back_populates="trades")
    trading_goal = relationship("TradingGoal", back_populates="trades")


class BankrollHistory(Base):
    __tablename__ = "bankroll_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    balance = Column(Integer, nullable=False)
    reason = Column(String(100), nullable=False)
    is_paper = Column(Boolean, nullable=False, default=False)
    amount = Column(Integer, nullable=True)
    entry_type = Column(String(30), nullable=False, default="trade", server_default="trade")  # trade, external_adjustment, initial_deposit
    adjustment_type = Column(String(50), nullable=True)  # reward, external_purchase, manual_correction
    trading_goal_id = Column(UUID(as_uuid=True), ForeignKey("trading_goals.id", ondelete="SET NULL"), nullable=True, index=True)
    data_origin = Column(String(20), nullable=False, default="user", server_default="user")
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
