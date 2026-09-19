from dataclasses import dataclass
from uuid import UUID
from app.core.config import settings
from app.engines.strategy import StrategyDecision
from app.engines.tax import calculate_tax, calculate_net_sale, calculate_profit, calculate_roi


@dataclass(frozen=True)
class ActionPresentation:
    action_type: str
    strategy_name: str
    strategy_type: str
    player_name: str
    player_rating: int
    card_version_name: str | None
    card_club: str | None
    card_league: str | None
    card_position: str | None
    card_platform: str | None
    headline: str
    buy_instruction: str
    sell_instruction: str
    capital_instruction: str
    profit_instruction: str
    max_buy_price: int
    target_sell_price: int
    recommended_quantity: int
    capital_limit: int
    estimated_profit_per_card: int
    estimated_total_profit: int
    estimated_roi: float
    capital_efficiency: float
    expected_holding_time_minutes: int | None
    confidence: str
    urgency: str
    why_explanation: str
    market_data_age_seconds: int | None = None
    market_snapshot_id: UUID | None = None
    profit_at_max_buy: int = 0
    roi_at_max_buy: float = 0.0
    snapshot_observed_price: int | None = None


class ActionEngine:
    """Motor de Ação Determinístico.

    Transforma a decisão quantitativa do StrategyEngine em instruções humanas diretas,
    assegurando identificação inequívoca da CardVersion e justificativas estritamente factuais.
    """

    def format_action(
        self,
        decision: StrategyDecision,
        sample_count: int,
        available_cash: int,
        market_data_age_seconds: int | None = None,
        market_snapshot_id: UUID | None = None,
    ) -> ActionPresentation:
        if not decision.has_action or not decision.opportunity:
            raise ValueError("Não é possível formatar uma ação para uma decisão sem oportunidade ativa")

        opp = decision.opportunity
        card = getattr(opp, "card", None)
        player = getattr(opp, "player", None)

        player_name = (card.player.name if (card and card.player) else None) or (player.name if player else "Jogador")
        player_rating = (card.rating if card else None) or (player.rating if player else 0)
        card_version_name = card.rarity if card else None
        card_club = card.club if card else None
        card_league = card.league if card else None
        card_position = card.position if card else None
        card_platform = getattr(opp, "platform", "console") or "console"

        qty = decision.recommended_quantity
        max_buy = opp.max_buy_price
        target_sell = opp.target_sell_price
        tax = calculate_tax(target_sell, settings.TRADING_TAX_RATE)
        net_sale = calculate_net_sale(target_sell, settings.TRADING_TAX_RATE)

        # Cálculo rigoroso via TaxEngine para o cenário no teto (conservador)
        profit_at_max_buy = calculate_profit(max_buy, target_sell, settings.TRADING_TAX_RATE)
        roi_at_max_buy = calculate_roi(max_buy, target_sell, settings.TRADING_TAX_RATE)

        observed_price = getattr(opp, "observed_price", None) or getattr(opp, "snapshot_observed_price", None) or max_buy

        specs_str = f"({player_rating} • {card_version_name or 'Gold'} • {card_position or 'N/A'})"

        max_buy_str = f"{max_buy:,}".replace(",", ".")
        target_sell_str = f"{target_sell:,}".replace(",", ".")
        market_price_str = f"{opp.market_price:,}".replace(",", ".")
        net_sale_str = f"{net_sale:,}".replace(",", ".")
        tax_str = f"{tax:,}".replace(",", ".")
        capital_limit_str = f"{decision.capital_limit:,}".replace(",", ".")
        obs_price_str = f"{observed_price:,}".replace(",", ".")
        profit_obs_str = f"{decision.estimated_profit_per_card:,}".replace(",", ".")
        profit_max_str = f"{profit_at_max_buy:,}".replace(",", ".")
        total_profit_max_str = f"{(profit_at_max_buy * qty):,}".replace(",", ".")

        if decision.action_type == "MASS_BID":
            headline = f"Dê lance em até {qty} cartas de {player_name} {specs_str}"
            buy_instruction = f"Não pague mais que {max_buy_str} coins por carta"
        elif decision.action_type == "SNIPE_BUY_NOW":
            headline = f"Compre já 1 carta de {player_name} {specs_str}"
            buy_instruction = f"Comprar Já até {max_buy_str} coins"
        else:
            headline = f"Compre até {qty} cartas de {player_name} {specs_str}"
            buy_instruction = f"Preço máximo de compra: {max_buy_str} coins"

        sell_instruction = f"Se arrematar, anuncie por {target_sell_str} coins"
        capital_instruction = f"Capital máximo recomendado: {capital_limit_str} coins"
        profit_instruction = (
            f"Lucro mínimo estimado no teto: +{profit_max_str} por carta "
            f"(Total estimado no teto: +{total_profit_max_str} coins)"
        )

        free_cash_retained_pct = 0
        if available_cash > 0:
            free_cash_retained_pct = int(max(0, (available_cash - decision.capital_limit) / available_cash * 100))

        club_info = f" ({card_club})" if card_club else ""
        platform_info = f" na plataforma {card_platform.upper()}" if card_platform else ""

        age_text = ""
        if market_data_age_seconds is not None:
            if market_data_age_seconds < 60:
                age_text = f", com cotação atualizada há {market_data_age_seconds}s"
            else:
                age_text = f", com cotação atualizada há {market_data_age_seconds // 60}m"

        roi_obs_str = f"{decision.estimated_roi * 100:.1f}%".replace(".", ",")
        roi_max_str = f"{roi_at_max_buy * 100:.1f}%".replace(".", ",")

        if observed_price < max_buy:
            profit_rationale = (
                f"Na cotação recente de {obs_price_str} coins, o lucro estimado é +{profit_obs_str} coins (ROI {roi_obs_str}). "
                f"O teto de compra é {max_buy_str} coins; comprando exatamente no teto, o lucro mínimo estimado é +{profit_max_str} coins (ROI ~{roi_max_str}), "
                f"considerando venda por {target_sell_str} coins e a taxa configurada."
            )
        else:
            profit_rationale = (
                f"O teto de compra é {max_buy_str} coins; comprando no teto, o lucro mínimo estimado é +{profit_max_str} coins (ROI ~{roi_max_str}), "
                f"considerando venda por {target_sell_str} coins e a taxa configurada."
            )

        why_parts = [
            f"Preço justo de mercado estimado em {market_price_str} coins para a versão {card_version_name or 'Gold'} {player_rating} de {player_name}{club_info}{platform_info}, baseado em {sample_count} observações recentes{age_text}.",
            f"Venda por {target_sell_str} coins gera {net_sale_str} coins líquidos após a taxa oficial de 5% da EA ({tax_str} coins retidos).",
            profit_rationale,
            f"Operação dimensionada para {qty} unidades ({capital_limit_str} coins), preservando {free_cash_retained_pct}% do seu saldo livre para gestão de risco.",
        ]
        why_explanation = " ".join(why_parts)

        return ActionPresentation(
            action_type=decision.action_type,
            strategy_name=decision.strategy_name,
            strategy_type=decision.strategy_type,
            player_name=player_name,
            player_rating=player_rating,
            card_version_name=card_version_name,
            card_club=card_club,
            card_league=card_league,
            card_position=card_position,
            card_platform=card_platform,
            headline=headline,
            buy_instruction=buy_instruction,
            sell_instruction=sell_instruction,
            capital_instruction=capital_instruction,
            profit_instruction=profit_instruction,
            max_buy_price=max_buy,
            target_sell_price=target_sell,
            recommended_quantity=qty,
            capital_limit=decision.capital_limit,
            estimated_profit_per_card=decision.estimated_profit_per_card,
            estimated_total_profit=decision.estimated_total_profit,
            estimated_roi=decision.estimated_roi,
            capital_efficiency=decision.capital_efficiency,
            expected_holding_time_minutes=decision.expected_holding_time_minutes,
            confidence=opp.confidence,
            urgency=decision.urgency,
            why_explanation=why_explanation,
            market_data_age_seconds=market_data_age_seconds,
            market_snapshot_id=market_snapshot_id,
            profit_at_max_buy=profit_at_max_buy,
            roi_at_max_buy=roi_at_max_buy,
            snapshot_observed_price=observed_price,
        )
