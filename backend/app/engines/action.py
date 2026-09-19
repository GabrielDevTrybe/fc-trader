from dataclasses import dataclass
from app.engines.strategy import StrategyDecision
from app.engines.tax import calculate_tax, calculate_net_sale


@dataclass(frozen=True)
class ActionPresentation:
    action_type: str
    strategy_name: str
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
    confidence: str
    urgency: str
    why_explanation: str


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
        tax = calculate_tax(target_sell)
        net_sale = calculate_net_sale(target_sell)

        specs_str = f"({player_rating} • {card_version_name or 'Gold'} • {card_position or 'N/A'})"

        if decision.action_type == "MASS_BID":
            headline = f"Dê lance em até {qty} cartas de {player_name} {specs_str}"
            buy_instruction = f"Não pague mais que {max_buy:,} coins por carta".replace(",", ".")
        elif decision.action_type == "SNIPE_BUY_NOW":
            headline = f"Compre já 1 carta de {player_name} {specs_str}"
            buy_instruction = f"Comprar Já até {max_buy:,} coins".replace(",", ".")
        else:
            headline = f"Compre até {qty} cartas de {player_name} {specs_str}"
            buy_instruction = f"Preço máximo de compra: {max_buy:,} coins".replace(",", ".")

        sell_instruction = f"Se arrematar, anuncie por {target_sell:,} coins".replace(",", ".")
        capital_instruction = f"Capital máximo recomendado: {decision.capital_limit:,} coins".replace(",", ".")
        profit_instruction = (
            f"Lucro líquido: +{decision.estimated_profit_per_card:,} por carta "
            f"(Total estimado: +{decision.estimated_total_profit:,} coins)"
        ).replace(",", ".")

        free_cash_retained_pct = 0
        if available_cash > 0:
            free_cash_retained_pct = int(max(0, (available_cash - decision.capital_limit) / available_cash * 100))

        club_info = f" ({card_club})" if card_club else ""
        platform_info = f" na plataforma {card_platform.upper()}" if card_platform else ""

        why_parts = [
            f"Preço justo de mercado estimado em {opp.market_price:,} coins para a versão {card_version_name or 'Gold'} {player_rating} de {player_name}{club_info}{platform_info}, baseado em {sample_count} observações recentes.".replace(",", "."),
            f"Venda por {target_sell:,} coins gera {net_sale:,} coins líquidos após a taxa oficial de 5% da EA ({tax:,} coins retidos).".replace(",", "."),
            f"Pagando até {max_buy:,} coins, a margem líquida assegura +{decision.estimated_profit_per_card:,} coins de lucro por carta (ROI de {decision.estimated_roi * 100:.1f}%).".replace(",", "."),
            f"Operação dimensionada para {qty} unidades ({decision.capital_limit:,} coins), preservando {free_cash_retained_pct}% do seu saldo livre para gestão de risco.".replace(",", "."),
        ]
        why_explanation = " ".join(why_parts)

        return ActionPresentation(
            action_type=decision.action_type,
            strategy_name=decision.strategy_name,
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
            confidence=opp.confidence,
            urgency=decision.urgency,
            why_explanation=why_explanation,
        )
