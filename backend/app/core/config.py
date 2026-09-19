from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = Field(
        default="",
        description="PostgreSQL / Supabase connection string",
    )

    # Core App
    APP_ENV: str = "development"
    APP_NAME: str = "FC Trader"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"

    # Trading Engine Rules
    TRADING_TAX_RATE: float = 0.05
    INITIAL_BANKROLL: int = 5000
    MINIMUM_PROFIT: int = 100
    MINIMUM_ROI: float = 0.15
    MAX_BANKROLL_PERCENTAGE_PER_TRADE: float = 0.20
    MINIMUM_CONFIDENCE: float = 0.60

    # Phase 2 & 3: Action Engine & Risk Policy Configuration
    ACTION_RECOMMENDATION_TTL_MINUTES: int = 15
    SNAPSHOT_VALIDITY_MINUTES: int = 15
    MARKET_PRICE_SHIFT_INVALIDATION_THRESHOLD: float = 0.05
    PORTFOLIO_MAX_INVENTORY_PERCENTAGE: float = 0.70
    PLAYER_MAX_CONCENTRATION_PERCENTAGE: float = 0.25
    MAX_OPEN_POSITIONS_PER_PLAYER: int = 3

    # Observation Freshness Windows (Minutes)
    OBSERVATION_FRESH_MINUTES: int = 15
    OBSERVATION_STALE_MINUTES: int = 60
    OBSERVATION_HISTORICAL_HOURS: int = 24

    # Strategy-Dependent ROI & Profit Thresholds (Configurable initial baselines)
    MINIMUM_ROI_QUICK_FLIP: float = 0.08      # 8% ROI for rapid turnover / sniping
    MINIMUM_PROFIT_QUICK_FLIP: int = 100     # 100 coins net
    MINIMUM_ROI_SWING: float = 0.15           # 15% ROI for standard flips
    MINIMUM_PROFIT_SWING: int = 250          # 250 coins net
    MINIMUM_ROI_INVESTMENT: float = 0.25      # 25% ROI for tactical holdings
    MINIMUM_PROFIT_INVESTMENT: int = 500     # 500 coins net

    # Market Intelligence & Confidence Scoring Parameters
    MARKET_PRICE_IQR_MULTIPLIER: float = 1.5
    MARKET_PRICE_MIN_SAMPLES: int = 3
    MARKET_PRICE_MIN_SAMPLES_FOR_OUTLIERS: int = 5
    CONFIDENCE_WEIGHT_SAMPLES: float = 0.30
    CONFIDENCE_WEIGHT_FRESHNESS: float = 0.30
    CONFIDENCE_WEIGHT_DISPERSION: float = 0.25
    CONFIDENCE_WEIGHT_STABILITY: float = 0.15
    MINIMUM_CONFIDENCE_FOR_ACTION: float = 0.50

    # Bankroll Tier Risk Allocation Percentages
    TIER_MICRO_MAX_PERCENTAGE: float = 0.30     # < 10.000 coins
    TIER_SMALL_MAX_PERCENTAGE: float = 0.25     # 10.000 - 50.000 coins
    TIER_MEDIUM_MAX_PERCENTAGE: float = 0.20    # 50.000 - 200.000 coins
    TIER_LARGE_MAX_PERCENTAGE: float = 0.15     # > 200.000 coins

    # Strategy Parameters
    MASS_BIDDING_MAX_QUANTITY: int = 5
    MASS_BIDDING_MIN_LIQUIDITY: int = 60
    SNIPING_MIN_ROI: float = 0.25

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
