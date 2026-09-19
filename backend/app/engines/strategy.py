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
    strategy_type: str = "QUICK_FLIP"
    recommended_quantity: int = 0
    capital_limit: int = 0
    estimated_profit_per_card: int = 0
    estimated_total_profit: int = 0
    estimated_roi: float = 0.0
    capital_efficiency: float = 0.0
    expected_holding_time_minutes: int | None = None
    tier_percentage_applied: float = 0.0
    max_capital_allocation: int = 0
    urgency: str = "NORMAL"
    reason: str = ""
    no_action_reason_code: str | None = None


class StrategyEngine:
    """Motor de Estratégia Determinístico com Avaliação de Risco Multidimensional.

    Opera unicamente sobre oportunidades já validadas quantitativamente pelos motores de mercado.
    Desacoplado de qualquer jogador ou carta fixa.
    Aplica:
    1. Teto por Faixa Patrimonial (Micro, Pequena, Média, Grande) como política inicial.
    2. Modificadores multidimensionais de risco: Confiança, Liquidez e Tipo de Estratégia.
    3. Teto Global de Estoque (máx 70% de total_equity).
    4. Concentração Máxima por Carta e por Atleta (máx 25% de total_equity e 3 posições abertas).
    5. recommended_quantity dimensionada estritamente sem nunca elevar max_buy_price.
    6. Emissão de no_action_reason_code estruturado quando não houver operação viável.
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
        if available_cash <= 0:
            return StrategyDecision(
                has_action=False,
                reason="Sem capital disponível livre para novas operações",
                no_action_reason_code="CAPITAL_EXCEEDED",
            )

        if not valid_opportunities:
            return StrategyDecision(
                has_action=False,
                reason="Não há oportunidades vigentes validadas pelos motores de mercado",
                no_action_reason_code="NO_PROFITABLE_OPPORTUNITY",
            )

        positions_count = open_positions_by_player or {}
        positions_cost = open_positions_cost_by_player or {}
        card_positions_count = open_positions_by_card or {}

        # 1. Teto por Faixa de Banca (Parâmetros iniciais configuráveis)
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
                no_action_reason_code="INVENTORY_LIMIT_REACHED",
            )

        # 3. Teto por Jogador / Carta (máx 25% da equity)
        player_cap = math.floor(total_equity * settings.PLAYER_MAX_CONCENTRATION_PERCENTAGE)

        candidates: list[dict] = []
        disqualify_reasons: set[str] = set()

        for opp in valid_opportunities:
            if opp.max_buy_price > available_cash or opp.max_buy_price <= 0:
                disqualify_reasons.add("CAPITAL_EXCEEDED")
                continue

            card_key = getattr(opp, "card_id", None) or opp.player_id
            player_key = getattr(opp, "player_id", None) or card_key

            if card_positions_count.get(card_key, 0) >= settings.MAX_OPEN_POSITIONS_PER_PLAYER:
                disqualify_reasons.add("CONCENTRATION_LIMIT_REACHED")
                continue
            if positions_count.get(player_key, 0) >= (settings.MAX_OPEN_POSITIONS_PER_PLAYER * 2):
                disqualify_reasons.add("CONCENTRATION_LIMIT_REACHED")
                continue

            player_current_cost = positions_cost.get(player_key, 0)
            player_remaining_cap = max(0, player_cap - player_current_cost)
            if player_remaining_cap < opp.max_buy_price:
                disqualify_reasons.add("CONCENTRATION_LIMIT_REACHED")
                continue

            # Modificadores de Risco Multidimensionais
            conf = (opp.confidence or "LOW").upper()
            if conf == "HIGH":
                conf_mod = 1.0
            elif conf == "MEDIUM":
                conf_mod = 0.75
            else:
                disqualify_reasons.add("LOW_CONFIDENCE")
                continue

            liq = opp.liquidity_score or 0
            if liq >= 75:
                liq_mod = 1.0
            elif liq >= 60:
                liq_mod = 0.80
            else:
                liq_mod = 0.50

            strat_type = getattr(opp, "strategy_type", "QUICK_FLIP") or "QUICK_FLIP"
            if strat_type == "QUICK_FLIP":
                strat_mod = 1.0
            elif strat_type == "SWING":
                strat_mod = 0.85
            else:
                strat_mod = 0.65

            # Orçamento da Operação com modulação multidimensional
            op_budget = math.floor(available_cash * tier_pct * conf_mod * liq_mod * strat_mod)
            max_alloc = min(op_budget, remaining_inventory_capacity, player_remaining_cap)

            qty = max_alloc // opp.max_buy_price
            if qty < 1:
                disqualify_reasons.add("CAPITAL_EXCEEDED")
                continue

            # Classificação da Ação
            if liq >= settings.MASS_BIDDING_MIN_LIQUIDITY and conf in ("MEDIUM", "HIGH"):
                action_type = "MASS_BID"
                strategy_name = "Mass Bidding"
                qty = min(qty, settings.MASS_BIDDING_MAX_QUANTITY)
                urgency = "NORMAL"
            elif opp.roi >= settings.SNIPING_MIN_ROI:
                action_type = "SNIPE_BUY_NOW"
                strategy_name = "Sniping"
                qty = 1
                urgency = "HIGH"
            else:
                action_type = "CONSERVATIVE_FLIP"
                strategy_name = "Flip Conservador"
                qty = min(qty, 2)
                urgency = "NORMAL"

            capital_limit = qty * opp.max_buy_price
            total_profit = qty * opp.estimated_profit
            cap_eff = getattr(opp, "capital_efficiency", None) or (
                round(opp.estimated_profit / float(opp.max_buy_price), 4) if opp.max_buy_price > 0 else 0.0
            )

            # Contribuição para a Meta Ativa
            if active_goal_target and active_goal_current:
                remaining_goal = max(100, active_goal_target - active_goal_current)
                goal_contrib = min(1.0, total_profit / float(remaining_goal)) * 30.0
            else:
                goal_contrib = 15.0

            opp_score_pts = (min(100.0, opp.opportunity_score) / 100.0) * 40.0
            liq_pts = (liq / 100.0) * 30.0
            composite_rank = opp_score_pts + goal_contrib + liq_pts

            candidates.append({
                "composite_rank": composite_rank,
                "opportunity": opp,
                "action_type": action_type,
                "strategy_name": strategy_name,
                "strategy_type": strat_type,
                "quantity": qty,
                "capital_limit": capital_limit,
                "profit_per_card": opp.estimated_profit,
                "total_profit": total_profit,
                "roi": opp.roi,
                "capital_efficiency": cap_eff,
                "holding_time": getattr(opp, "expected_holding_time_minutes", None),
                "urgency": urgency,
            })

        if not candidates:
            # Determina o código de descarte principal
            code = "NO_PROFITABLE_OPPORTUNITY"
            if "LOW_CONFIDENCE" in disqualify_reasons:
                code = "LOW_CONFIDENCE"
            elif "INVENTORY_LIMIT_REACHED" in disqualify_reasons:
                code = "INVENTORY_LIMIT_REACHED"
            elif "CAPITAL_EXCEEDED" in disqualify_reasons:
                code = "CAPITAL_EXCEEDED"
            elif "CONCENTRATION_LIMIT_REACHED" in disqualify_reasons:
                code = "CONCENTRATION_LIMIT_REACHED"

            return StrategyDecision(
                has_action=False,
                reason="Nenhuma oportunidade atende aos critérios de segurança e risco da banca atual",
                no_action_reason_code=code,
            )

        candidates.sort(key=lambda x: x["composite_rank"], reverse=True)
        best = candidates[0]

        return StrategyDecision(
            has_action=True,
            opportunity=best["opportunity"],
            action_type=best["action_type"],
            strategy_name=best["strategy_name"],
            strategy_type=best["strategy_type"],
            recommended_quantity=best["quantity"],
            capital_limit=best["capital_limit"],
            estimated_profit_per_card=best["profit_per_card"],
            estimated_total_profit=best["total_profit"],
            estimated_roi=best["roi"],
            capital_efficiency=best["capital_efficiency"],
            expected_holding_time_minutes=best["holding_time"],
            tier_percentage_applied=tier_pct,
            max_capital_allocation=best["capital_limit"],
            urgency=best["urgency"],
            reason="Melhor alocação determinística de risco e capital encontrada",
            no_action_reason_code=None,
        )
