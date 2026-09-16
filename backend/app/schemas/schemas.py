from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# --- Player Schemas ---
class PlayerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rating: int = Field(..., ge=40, le=99)
    position: str | None = None
    rarity: str | None = None
    league: str | None = None
    club: str | None = None
    nation: str | None = None


class PlayerCreate(PlayerBase):
    pass


class PlayerRead(PlayerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Observation Schemas ---
class ObservationBatchItem(BaseModel):
    player: str = Field(..., description="Nome do jogador (ex: Palhinha)")
    rating: int = Field(..., ge=40, le=99, description="Overall do jogador")
    price: int = Field(..., gt=0, description="Preço observado em coins")
    type: str = Field("buy_now", description="'buy_now', 'bid' ou 'sale_estimate'")
    position: str | None = None
    rarity: str | None = None
    league: str | None = None
    club: str | None = None
    nation: str | None = None
    observed_at: datetime | None = None


class PriceObservationRead(BaseModel):
    id: UUID
    player_id: UUID
    price: int
    observation_type: str
    source: str
    observed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Market Opportunity Schemas ---
class OpportunityAnalysis(BaseModel):
    player_id: UUID
    player_name: str
    rating: int
    observed_price: int
    market_price: int | None
    max_buy_price: int
    target_sell_price: int
    expected_profit: int
    expected_roi: float
    confidence: str
    liquidity_score: int
    opportunity_score: float
    recommendation: str
    reason: str


class ObservationBatchResponse(BaseModel):
    processed_count: int
    analyses: list[OpportunityAnalysis]


class MarketOpportunityRead(BaseModel):
    id: UUID
    player_id: UUID
    player: PlayerRead | None = None
    observed_price: int
    market_price: int
    max_buy_price: int
    target_sell_price: int
    estimated_profit: int
    roi: float
    confidence: str
    liquidity_score: int
    opportunity_score: float
    detected_at: datetime
    expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Trade Schemas ---
class TradeCreate(BaseModel):
    player_id: UUID
    buy_price: int = Field(..., gt=0)
    is_paper_trade: bool = True
    bought_at: datetime | None = None


class TradeClose(BaseModel):
    sell_price: int = Field(..., gt=0)
    sold_at: datetime | None = None


class TradeRead(BaseModel):
    id: UUID
    player_id: UUID
    player: PlayerRead | None = None
    buy_price: int
    sell_price: int | None = None
    tax: int | None = None
    net_received: int | None = None
    profit: int | None = None
    roi: float | None = None
    bought_at: datetime
    sold_at: datetime | None = None
    status: str
    is_paper_trade: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Bankroll Schemas ---
class BankrollMilestone(BaseModel):
    target: int
    label: str
    achieved: bool
    progress_percentage: float


class BankrollSummary(BaseModel):
    balance: int
    initial_bankroll: int
    profit_today: int
    total_profit: int
    total_trades: int
    win_rate: float | None = None
    average_roi: float | None = None
    next_target: int
    milestones: list[BankrollMilestone]
    is_paper: bool = False
