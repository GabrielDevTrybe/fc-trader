from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass(frozen=True)
class ProviderPricePoint:
    price: int
    observation_type: str  # "buy_now", "bid", "sale_estimate"
    platform: str          # "console", "pc"
    observed_at: datetime
    provider: str          # authorized/stable market data provider identifier


@dataclass(frozen=True)
class ProviderCardItem:
    external_id: str
    player_name: str
    rating: int
    game_version: str
    position: str | None = None
    rarity: str | None = None
    club: str | None = None
    league: str | None = None
    nation: str | None = None


class MarketDataProvider(ABC):
    """Contrato abstrato para futuros provedores de mercado autorizados e estáveis (Fase 3).

    Garante que a obtenção de dados de mercado permaneça isolada da camada de domínio do trader.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Identificador canônico do provedor (ex: 'official_partner_feed', 'authorized_api')."""
        pass

    @abstractmethod
    def fetch_card_prices(self, external_id: str, platform: str = "console") -> list[ProviderPricePoint]:
        """Obtém cotações recentes para uma carta específica em um mercado específico."""
        pass

    @abstractmethod
    def fetch_catalog_cards(self, query: str | None = None) -> list[ProviderCardItem]:
        """Varre o catálogo de cartas disponibilizado pelo provedor."""
        pass
