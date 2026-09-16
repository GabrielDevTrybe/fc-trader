from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AlertNotification:
    player_name: str
    rating: int
    observed_price: int
    market_price: int
    expected_profit: int
    expected_roi: float
    confidence: str
    opportunity_score: float
    created_at: datetime


class AlertProvider(ABC):
    """Interface abstrata para canais de notificação de alertas de oportunidades."""

    @abstractmethod
    def send_alert(self, alert: AlertNotification) -> bool:
        """Envia ou registra um alerta para o usuário."""
        pass
