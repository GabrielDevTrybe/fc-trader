from dataclasses import dataclass
from app.engines.tax import (
    calculate_max_buy_price,
    calculate_net_sale,
    calculate_profit,
    calculate_roi,
)
from app.engines.market_price import MarketPriceResult
from app.engines.liquidity import LiquidityResult


@dataclass(frozen=True)
class TradingDecision:
    recommendation: str  # "BUY", "WATCH", "PASS", "INSUFFICIENT_DATA"
    is_opportunity: bool
    observed_price: int
    market_price: int | None
    max_buy_price: int
    target_sell_price: int
    expected_profit: int
    expected_roi: float
    confidence: str
    reason: str


class TradingEngine:
    """Motor de tomada de decisão analítica de trading para o EA FC 27.

    Avalia se um preço observado em leilão (bid) ou compra imediata (buy_now)
    configura uma oportunidade de compra lucrativa em relação ao preço justo de mercado estimado,
    obedecendo a taxa EA de 5%, limites de risco de banca e filtros mínimos de lucro e ROI.
    """

    def __init__(
        self,
        tax_rate: float = 0.05,
        minimum_profit: int = 100,
        minimum_roi: float = 0.15,
        maximum_bankroll_percentage: float = 0.20,
        minimum_confidence: float = 0.60,
    ) -> None:
        self.tax_rate = tax_rate
        self.minimum_profit = minimum_profit
        self.minimum_roi = minimum_roi
        self.maximum_bankroll_percentage = maximum_bankroll_percentage
        self.minimum_confidence = minimum_confidence

    def evaluate(
        self,
        observed_price: int,
        market_stats: MarketPriceResult,
        liquidity: LiquidityResult,
        bankroll: int = 5000,
    ) -> TradingDecision:
        # 1. Checagem de dados suficientes
        if not market_stats.has_sufficient_data or market_stats.market_price is None:
            return TradingDecision(
                recommendation="INSUFFICIENT_DATA",
                is_opportunity=False,
                observed_price=observed_price,
                market_price=None,
                max_buy_price=0,
                target_sell_price=0,
                expected_profit=0,
                expected_roi=0.0,
                confidence="LOW",
                reason=market_stats.reason or "Dados insuficientes de mercado",
            )

        market_price = market_stats.market_price
        target_sell_price = market_price

        # 2. Cálculo do Preço Máximo Viável de Compra
        max_buy = calculate_max_buy_price(
            target_sell_price=target_sell_price,
            min_profit=self.minimum_profit,
            min_roi=self.minimum_roi,
            bankroll=bankroll,
            max_bankroll_percentage=self.maximum_bankroll_percentage,
            tax_rate=self.tax_rate,
        )

        # 3. Métricas da operação com o preço observado
        profit = calculate_profit(observed_price, target_sell_price, self.tax_rate)
        roi = calculate_roi(observed_price, target_sell_price, self.tax_rate)

        # 4. Avaliação de elegibilidade
        confidence = market_stats.confidence

        # Se o preço observado ultrapassa o saldo total da banca
        if observed_price > bankroll:
            return TradingDecision(
                recommendation="PASS",
                is_opportunity=False,
                observed_price=observed_price,
                market_price=market_price,
                max_buy_price=max_buy,
                target_sell_price=target_sell_price,
                expected_profit=profit,
                expected_roi=roi,
                confidence=confidence,
                reason=f"Preço de compra ({observed_price}) excede o saldo da banca ({bankroll})",
            )

        # Se o lucro líquido após 5% for negativo ou nulo
        if profit <= 0:
            return TradingDecision(
                recommendation="PASS",
                is_opportunity=False,
                observed_price=observed_price,
                market_price=market_price,
                max_buy_price=max_buy,
                target_sell_price=target_sell_price,
                expected_profit=profit,
                expected_roi=roi,
                confidence=confidence,
                reason=f"Operação deficitária após dedução de 5% de taxa (Lucro: {profit} coins)",
            )

        # Se atende a todos os critérios (lucro mínimo, ROI mínimo e preço <= max_buy)
        if observed_price <= max_buy and profit >= self.minimum_profit and roi >= self.minimum_roi:
            recommendation = "BUY"
            is_opp = True
            reason = (
                f"Oportunidade identificada! Compra a {observed_price} <= {max_buy}, "
                f"Venda alvo a {target_sell_price}, Lucro Líquido: +{profit} coins ({roi * 100:.1f}% ROI)"
            )
        else:
            recommendation = "WATCH" if profit > 0 else "PASS"
            is_opp = False
            reasons: list[str] = []
            if observed_price > max_buy:
                reasons.append(f"Preço ({observed_price}) acima do teto recomendado ({max_buy})")
            if profit < self.minimum_profit:
                reasons.append(f"Lucro (+{profit}) abaixo do mínimo ({self.minimum_profit})")
            if roi < self.minimum_roi:
                reasons.append(f"ROI ({roi * 100:.1f}%) abaixo do mínimo ({self.minimum_roi * 100:.0f}%)")
            reason = "; ".join(reasons)

        return TradingDecision(
            recommendation=recommendation,
            is_opportunity=is_opp,
            observed_price=observed_price,
            market_price=market_price,
            max_buy_price=max_buy,
            target_sell_price=target_sell_price,
            expected_profit=profit,
            expected_roi=roi,
            confidence=confidence,
            reason=reason,
        )
