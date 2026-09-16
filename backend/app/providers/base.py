from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence


@dataclass
class RawObservation:
    player_name: str
    player_rating: int
    price: int
    observation_type: str  # "buy_now", "bid", "sale_estimate"
    position: str | None = None
    rarity: str | None = None
    league: str | None = None
    club: str | None = None
    nation: str | None = None
    observed_at: datetime | None = None


class MarketDataProvider(ABC):
    """Interface abstrata base para provedores de dados de mercado.

    Desacopla as fontes de entrada dos motores analíticos e de persistência.
    """

    @abstractmethod
    def fetch_observations(self, **kwargs) -> Sequence[RawObservation]:
        """Obtém observações de mercado a partir da fonte."""
        pass
