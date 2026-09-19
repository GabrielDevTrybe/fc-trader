from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


# --- Player Schemas ---
class PlayerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    nation: str | None = None
    data_origin: str = "user"


class PlayerCreate(PlayerBase):
    pass


class PlayerRead(PlayerBase):
    id: UUID
    rating: int | None = None
    position: str | None = None
    rarity: str | None = None
    league: str | None = None
    club: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Card Version (PlayerCard) Schemas ---
class CardExternalIdBase(BaseModel):
    provider: str = Field(..., min_length=1, max_length=50, description="Nome do provedor de mercado autorizado")
    external_id: str = Field(..., min_length=1, max_length=100, description="Identificador no provedor externo")


class CardExternalIdCreate(CardExternalIdBase):
    card_id: UUID


class CardExternalIdRead(CardExternalIdBase):
    id: UUID
    card_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlayerCardBase(BaseModel):
    player_id: UUID
    game_version: str = "FC27"
    rating: int = Field(..., ge=40, le=99)
    position: str | None = None
    rarity: str | None = None  # Gold Rare, Gold Common, TOTW, Hero, etc.
    club: str | None = None
    league: str | None = None
    nation: str | None = None
    is_active: bool = True
    data_origin: str = "user"


class PlayerCardCreate(PlayerCardBase):
    pass


class PlayerCardRead(PlayerCardBase):
    id: UUID
    player_name: str | None = None
    external_ids: list[CardExternalIdRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Observation Schemas ---
class ObservationBatchItem(BaseModel):
    player: str = Field(..., description="Nome do jogador")
    rating: int = Field(..., ge=40, le=99, description="Overall do jogador")
    price: int = Field(..., gt=0, description="Preço observado em coins")
    type: str = Field("buy_now", description="'buy_now', 'bid' ou 'sale_estimate'")
    platform: str = Field("console", description="Plataforma de mercado ('console', 'pc')")
    position: str | None = None
    rarity: str | None = None
    league: str | None = None
    club: str | None = None
    nation: str | None = None
    card_id: UUID | None = Field(None, description="UUID da CardVersion se já conhecido")
    external_card_id: str | None = Field(None, description="ID externo no provedor se fornecido")
    provider: str = Field("manual", description="Provedor ou fonte da cotação")
    data_origin: str = "user"
    observed_at: datetime | None = None


class PriceObservationRead(BaseModel):
    id: UUID
    card_id: UUID
    player_id: UUID | None = None
    price: int
    observation_type: str
    platform: str
    source: str
    data_origin: str
    observed_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Market Opportunity Schemas ---
class OpportunityAnalysis(BaseModel):
    card_id: UUID
    player_id: UUID
    player_name: str
    rating: int
    version_name: str | None = None
    club: str | None = None
    platform: str = "console"
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


class MarketSnapshotRead(BaseModel):
    id: UUID
    card_id: UUID
    platform: str = "console"
    sample_count: int
    valid_sample_count: int
    min_price: int | None = None
    max_price: int | None = None
    median_price: int | None = None
    p20_price: int | None = None
    p80_price: int | None = None
    robust_mean: float | None = None
    std_dev: float
    dispersion_ratio: float
    estimated_market_price: int | None = None
    conservative_buy_price: int | None = None
    conservative_sell_price: int | None = None
    confidence_score: float
    confidence_level: str
    freshness_status: str
    newest_observation_age_seconds: int | None = None
    trend: str = "NEUTRAL"
    data_quality: str = "OK"
    calculated_at: datetime
    expires_at: datetime | None = None
    data_origin: str = "user"

    model_config = ConfigDict(from_attributes=True)


class MarketOpportunityRead(BaseModel):
    id: UUID
    card_id: UUID
    player_id: UUID | None = None
    card: PlayerCardRead | None = None
    player: PlayerRead | None = None
    platform: str = "console"
    observed_price: int
    market_price: int
    max_buy_price: int
    target_sell_price: int
    estimated_profit: int
    roi: float
    confidence: str
    liquidity_score: int
    opportunity_score: float
    strategy_type: str = "QUICK_FLIP"
    capital_efficiency: float | None = None
    expected_holding_time_minutes: int | None = None
    data_origin: str = "user"
    detected_at: datetime
    expires_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Trade Schemas ---
class TradeCreate(BaseModel):
    card_id: UUID | None = None
    player_id: UUID | None = None
    buy_price: int = Field(..., gt=0)
    is_paper_trade: bool = True
    trading_goal_id: UUID | None = None
    action_recommendation_id: UUID | None = None
    data_origin: str = "user"
    bought_at: datetime | None = None


class TradeClose(BaseModel):
    sell_price: int = Field(..., gt=0)
    sold_at: datetime | None = None


class TradeRead(BaseModel):
    id: UUID
    card_id: UUID
    player_id: UUID | None = None
    card: PlayerCardRead | None = None
    player: PlayerRead | None = None
    trading_goal_id: UUID | None = None
    action_recommendation_id: UUID | None = None
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
    data_origin: str = "user"
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


class BankrollCapitalSummary(BaseModel):
    total_equity: int
    cash_balance: int
    available_cash: int
    inventory_cost: int
    open_positions_count: int
    total_trading_profit: int
    total_external_rewards: int = 0
    total_external_expenses: int = 0
    total_reconciliations: int = 0
    total_external_adjustments: int = 0
    is_configured: bool = True
    is_paper: bool = False


class BankrollAdjustmentCreate(BaseModel):
    amount: int = Field(..., description="Valor positivo para crédito ou negativo para débito")
    adjustment_type: str = Field(..., description="reward, external_purchase, manual_correction")
    reason: str = Field(..., min_length=2, max_length=100)
    is_paper: bool = False


class BankrollOnboardingCreate(BaseModel):
    cash_balance: int = Field(..., gt=0, description="Quantas coins você possui atualmente")
    target_balance: int = Field(..., gt=0, description="Qual sua meta de coins")

    @model_validator(mode="after")
    def validate_target_greater_than_cash(self):
        if self.target_balance <= self.cash_balance:
            raise ValueError("A meta de coins deve ser estritamente maior que o saldo inicial")
        return self


class BankrollSyncCreate(BaseModel):
    current_actual_balance: int = Field(..., ge=0, description="Saldo real atual verificado no jogo")
    reason: str = Field("Sincronização manual de saldo", max_length=100)
    is_paper: bool = False


# --- Phase 2: Trading Goals Schemas ---
class TradingGoalCreate(BaseModel):
    target_balance: int = Field(..., gt=0, description="Alvo em coins para o ciclo")
    starting_balance: int | None = Field(None, description="Saldo inicial. Se omitido, utiliza o total_equity atual")
    is_paper: bool = False


class TradingGoalRead(BaseModel):
    id: UUID
    starting_balance: int
    target_balance: int
    current_balance: int
    status: str  # ACTIVE, COMPLETED, CLOSED
    is_paper: bool
    data_origin: str
    started_at: datetime
    completed_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    progress_percentage: float = 0.0
    trades_count: int = 0
    profit_in_goal: int = 0
    win_rate: float | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Phase 2: Action Engine & Feedback Schemas ---
class PurchaseItem(BaseModel):
    buy_price: int = Field(..., gt=0, description="Preço efetivamente pago nesta carta individual")


class ActionFeedbackCreate(BaseModel):
    recommendation_id: UUID
    action_result: str = Field(..., description="BOUGHT, MISSED, CANCELLED")
    purchases: list[PurchaseItem] = Field(default_factory=list, description="Lista de compras com preços individuais")
    missed_reason: str | None = Field(None, description="price_rose, no_cards_found, lost_bids, given_up, other")
    notes: str | None = None


class ActionRecommendationRead(BaseModel):
    id: UUID
    card_id: UUID
    player_id: UUID | None = None
    trading_goal_id: UUID | None = None
    opportunity_id: UUID | None = None
    market_snapshot_id: UUID | None = None
    action_type: str
    strategy_name: str
    strategy_type: str = "QUICK_FLIP"
    player_name: str
    player_rating: int

    # Identidade Inequívoca da Versão da Carta
    card_version_name: str | None = None
    card_club: str | None = None
    card_league: str | None = None
    card_position: str | None = None
    card_platform: str | None = None

    max_buy_price: int
    target_sell_price: int
    recommended_quantity: int
    capital_limit: int
    estimated_profit_per_card: int
    estimated_total_profit: int
    estimated_roi: float
    profit_at_max_buy: int | None = Field(None, description="Lucro líquido mínimo estimado comprando pelo teto max_buy")
    roi_at_max_buy: float | None = Field(None, description="ROI líquido mínimo estimado comprando pelo teto max_buy")
    capital_efficiency: float | None = None
    expected_holding_time_minutes: int | None = None
    snapshot_market_price: int
    snapshot_observed_price: int
    snapshot_liquidity_score: int
    snapshot_confidence: str
    snapshot_opportunity_score: float
    snapshot_sample_count: int
    snapshot_available_cash: int
    market_data_age_seconds: int | None = None
    no_action_reason_code: str | None = None
    why_explanation: str
    urgency: str
    status: str
    is_paper: bool
    data_origin: str
    created_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurrentActionResponse(BaseModel):
    has_action: bool
    status: str  # ACTION_AVAILABLE, NO_ACTION, GOAL_INACTIVE, BANKROLL_NOT_CONFIGURED, INSUFFICIENT_DATA
    action: ActionRecommendationRead | None = None
    title: str | None = None
    message: str | None = None
    suggestion: str | None = None
    no_action_reason_code: str | None = None


class CsvBatchUploadRequest(BaseModel):
    csv_content: str = Field(..., description="Conteúdo CSV em texto puro com cabeçalho")
    data_origin: str = Field("user", description="Isolamento de dados: 'user' ou 'test'")
