from app.engines.trading import TradingEngine
from app.engines.market_price import MarketPriceResult
from app.engines.liquidity import LiquidityResult


def test_trading_engine_palhinha_opportunity():
    """Valida o cenário de negócio:

    Preço de mercado estimado: 1050
    Observação recebida: 600 (bid)
    Banca: 5000
    Deve recomendar BUY, com max_buy calculado, lucro estimado positivo e ROI superior a 15%.
    """
    engine = TradingEngine(
        tax_rate=0.05,
        minimum_profit=100,
        minimum_roi=0.15,
        maximum_bankroll_percentage=0.20,
    )

    market_stats = MarketPriceResult(
        market_price=1050,
        sample_count=6,
        valid_sample_count=6,
        outliers=[],
        clean_prices=[1000, 1000, 1050, 1050, 1050, 1100],
        median_price=1050,
        trimmed_mean=1041.67,
        std_dev=34.16,
        confidence="HIGH",
        has_sufficient_data=True,
        reason="OK",
    )

    liquidity = LiquidityResult(
        score=82,
        observation_count=6,
        newest_observation_age_minutes=5.0,
        price_spread_percentage=10.0,
        confidence="HIGH",
        reason="OK",
    )

    decision = engine.evaluate(
        observed_price=600,
        market_stats=market_stats,
        liquidity=liquidity,
        bankroll=5000,
    )

    assert decision.is_opportunity
    assert decision.recommendation == "BUY"
    assert decision.target_sell_price == 1050
    # Net sale = floor(1050 * 0.95) = 997
    # Profit = 997 - 600 = 397
    assert decision.expected_profit == 397
    assert decision.expected_roi > 0.60
    assert decision.max_buy_price >= 600


def test_trading_engine_negative_profit_rejected():
    """Operações onde o lucro após 5% seria nulo ou negativo devem ser categorizadas como PASS."""
    engine = TradingEngine()
    market_stats = MarketPriceResult(
        market_price=1000,
        sample_count=5,
        valid_sample_count=5,
        outliers=[],
        clean_prices=[1000, 1000, 1000, 1000, 1000],
        median_price=1000,
        trimmed_mean=1000.0,
        std_dev=0.0,
        confidence="HIGH",
        has_sufficient_data=True,
        reason="OK",
    )
    liquidity = LiquidityResult(
        score=70,
        observation_count=5,
        newest_observation_age_minutes=2.0,
        price_spread_percentage=0.0,
        confidence="HIGH",
        reason="OK",
    )

    # Preço observado 980 em mercado de 1000 (líquido 950 -> prejuízo de 30)
    decision = engine.evaluate(
        observed_price=980,
        market_stats=market_stats,
        liquidity=liquidity,
        bankroll=5000,
    )
    assert not decision.is_opportunity
    assert decision.recommendation == "PASS"
    assert decision.expected_profit < 0


def test_trading_engine_bankroll_exceeded():
    """Se o preço observado ultrapassar o saldo total da banca, deve ser PASS."""
    engine = TradingEngine()
    market_stats = MarketPriceResult(
        market_price=10000,
        sample_count=5,
        valid_sample_count=5,
        outliers=[],
        clean_prices=[10000] * 5,
        median_price=10000,
        trimmed_mean=10000.0,
        std_dev=0.0,
        confidence="HIGH",
        has_sufficient_data=True,
        reason="OK",
    )
    liquidity = LiquidityResult(
        score=70,
        observation_count=5,
        newest_observation_age_minutes=2.0,
        price_spread_percentage=0.0,
        confidence="HIGH",
        reason="OK",
    )

    decision = engine.evaluate(
        observed_price=7000,
        market_stats=market_stats,
        liquidity=liquidity,
        bankroll=5000,
    )
    assert not decision.is_opportunity
    assert decision.recommendation == "PASS"
    assert "excede o saldo da banca" in decision.reason
