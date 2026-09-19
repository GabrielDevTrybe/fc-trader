from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Sequence
from uuid import UUID

from app.core.config import settings
from app.models.entities import MarketOpportunity


@dataclass(frozen=True)
class StrategyDecision:
    has_action: bool
    opportunity: MarketOpportunity | None = None
    action_type: str = ""       # MASS_BID, SNIPE_BUY_NOW, CONSERVATIVE_FLIP
    strategy_name: str = ""     # Mass Bidding, Sniping, Flip Conservador
    recommended_quantity: int = 0
    capital_limit: int = 0
    estimated_profit_per_card: int = 0
    estimated_total_profit: int = 0
    estimated_roi: float = 0.0
    tier_percentage_applied: float = 0.0
    max_capital_allocation: int = 0
    urgency: str = "NORMAL"
    reason: str = ""


class StrategyEngine:
    """Motor de Estratégia Determinístico com Política Paramétrica de Risco de Capital.

    Opera unicamente sobre oportunidades já validadas quantitativamente pelos motores de mercado.
    Desacoplado de qualquer jogador ou carta fixa.
    Calcula:
    1. Teto por Faixa Patrimonial (Micro, Pequena, Média, Grande)
    2. Modificadores de Liquidez e Confiança
    3. Teto Global de Estoque (máx 70% de total_equity)
    4. Concentração Máxima por Carta e por Jogador (máx 25% de total_equity e 3 posições abertas)
    5. recommended_quantity sem nunca elevar max_buy_price
    """

    def evaluate_best_action(
        self,
        available_cash: int,
        total_equity: int,
        inventory_cost: int,
        valid_opportunities: Sequence[MarketOpportunity],
        open_positions_by_player: dict[UUID, int] | None = None,
        open_positions_cost_by_player: dict[UUID, int] | None = None,
        open_positions_by_card: dict[UUID, int] | None = None,
        active_goal_target: int | None = None,
        active_goal_current: int | None = None,
    ) -> StrategyDecision:
        if available_cash <= 0 or not valid_opportunities:
            return StrategyDecision(
                has_action=False,
                reason="Sem capital disponível livre ou sem oportunidades ativas no mercado",
            )

        positions_count = open_positions_by_player or {}
        positions_cost = open_positions_cost_by_player or {}
        card_positions_count = open_positions_by_card or {}

        # 1. Teto por Faixa de Banca
        if total_equity < 10_000:
            tier_pct = settings.TIER_MICRO_MAX_PERCENTAGE
        elif total_equity < 50_000:
            tier_pct = settings.TIER_SMALL_MAX_PERCENTAGE
        elif total_equity < 200_000:
            tier_pct = settings.TIER_MEDIUM_MAX_PERCENTAGE
        else:
            tier_pct = settings.TIER_LARGE_MAX_PERCENTAGE

        # 2. Teto Global de Estoque do Portfólio (máx 70% da equity)
        max_portfolio_inventory = math.floor(total_equity * settings.PORTFOLIO_MAX_INVENTORY_PERCENTAGE)
        remaining_inventory_capacity = max(0, max_portfolio_inventory - inventory_cost)
        if remaining_inventory_capacity <= 0:
            return StrategyDecision(
                has_action=False,
                reason=f"Limite de estoque do portfólio atingido ({inventory_cost}/{max_portfolio_inventory} coins)",
            )

        # 3. Teto por Jogador / Carta (máx 25% da equity)
        player_cap = math.floor(total_equity * settings.PLAYER_MAX_CONCENTRATION_PERCENTAGE)

        candidates: list[tuple[float, MarketOpportunity, str, str, int, int, int, int, float, str]] = []

        for opp in valid_opportunities:
            if opp.max_buy_price > available_cash or opp.max_buy_price <= 0:
                continue

            # Proteção de concentração: máximo de cartas abertas da mesma versão de carta
            card_key = getattr(opp, "card_id", None) or opp.player_id
            player_key = getattr(opp, "player_id", None) or card_key

            if card_positions_count.get(card_key, 0) >= settings.MAX_OPEN_POSITIONS_PER_PLAYER:
                continue
            if positions_count.get(player_key, 0) >= (settings.MAX_OPEN_POSITIONS_PER_PLAYER * 2):
                continue

            player_current_cost = positions_cost.get(player_key, 0)
            player_remaining_cap = max(0, player_cap - player_current_cost)
            if player_remaining_cap < opp.max_buy_price:
                continue

            # Modificadores qualitativos
            conf = (opp.confidence or "LOW").upper()
            if conf == "HIGH":
                conf_mod = 1.0
            elif conf == "MEDIUM":
                conf_mod = 0.75
            else:
                continue  # Confiança LOW não gera ação proativa

            liq = opp.liquidity_score or 0
            if liq >= 75:
                liq_mod = 1.0
            elif liq >= 60:
                liq_mod = 0.80
            else:
                liq_mod = 0.50

            # Orçamento da Operação
            op_budget = math.floor(available_cash * tier_pct * conf_mod * liq_mod)
            max_alloc = min(op_budget, remaining_inventory_capacity, player_remaining_cap)

            qty = max_alloc // opp.max_buy_price
            if qty < 1:
                continue

            # Classificação de Estratégia
            if liq >= settings.MASS_BIDDING_MIN_LIQUIDITY and conf in ("MEDIUM", "HIGH"):
                strat_type = "MASS_BID"
                strat_name = "Mass Bidding"
                qty = min(qty, settings.MASS_BIDDING_MAX_QUANTITY)
                urgency = "NORMAL"
            elif opp.roi >= settings.SNIPING_MIN_ROI:
                strat_type = "SNIPE_BUY_NOW"
                strat_name = "Sniping"
                qty = 1
                urgency = "HIGH"
            else:
                strat_type = "CONSERVATIVE_FLIP"
                strat_name = "Flip Conservador"
                qty = min(qty, 2)
                urgency = "NORMAL"

            capital_limit = qty * opp.max_buy_price
            total_profit = qty * opp.estimated_profit

            # Ranking Multicritério da Ação
            if active_goal_target and active_goal_current:
                remaining_goal = max(100, active_goal_target - active_goal_current)
                goal_contrib = min(1.0, total_profit / float(remaining_goal)) * 35.0
            else:
                goal_contrib = 20.0

            opp_score_pts = (min(100.0, opp.opportunity_score) / 100.0) * 35.0
            liq_pts = (liq / 100.0) * 30.0

            composite_rank = goal_contrib + opp_score_pts + liq_pts

            candidates.append((
                composite_rank,
                opp,
                strat_type,
                strat_name,
                qty,
                capital_limit,
                opp.estimated_profit,
                total_profit,
                opp.roi,
                urgency,
            ))

        if not candidates:
            return StrategyDecision(
                has_action=False,
                reason="Nenhuma oportunidade atende aos critérios de segurança e risco da banca atual",
            )

        candidates.sort(key=lambda x: x[0], reverse=True)
        best = candidates[0]

        return StrategyDecision(
            has_action=True,
            opportunity=best[1],
            action_type=best[2],
            strategy_name=best[3],
            recommended_quantity=best[4],
            capital_limit=best[5],
            estimated_profit_per_card=best[6],
            estimated_total_profit=best[7],
            estimated_roi=best[8],
            tier_percentage_applied=tier_pct,
            max_capital_allocation=best[5],
            urgency=best[9],
            reason="Melhor alocação determinística de risco e capital encontrada",
        )
