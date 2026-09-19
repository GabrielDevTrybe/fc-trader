from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence
from app.engines.strategy import StrategyDecision


@dataclass(frozen=True)
class AIStrategistInput:
    goal_target: int
    goal_current: int
    available_cash: int
    inventory_cost: int
    candidate_decisions: Sequence[StrategyDecision]
    recent_feedback_summary: str | None = None


@dataclass(frozen=True)
class AIStrategistOutput:
    chosen_decision: StrategyDecision
    copilot_insight: str
    confidence_reasoning: str


class AIStrategist(ABC):
    """Interface abstrata de contrato para o futuro AI Strategist / Copilot.

    Guardrail Arquitetural Inviolável:
    A camada de IA opera exclusivamente como consultora/explicadora sobre candidatos
    previamente validados pelo StrategyEngine. A IA é estritamente proibida de aumentar
    max_buy_price, criar preços de venda fora do target_sell_price determinístico, alterar taxas
    ou dispensar limites de risco de capital da banca.
    """

    @abstractmethod
    def consult(self, context: AIStrategistInput) -> AIStrategistOutput:
        """Processa a consulta ao Copilot e retorna insight contextualizado sob guardrails rígidos."""
        pass
