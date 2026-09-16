from datetime import datetime, timezone
from app.engines.liquidity import LiquidityAnalyzer
from app.engines.market_price import PriceDataPoint


def test_liquidity_empty_observations():
    analyzer = LiquidityAnalyzer()
    res = analyzer.analyze([])
    assert res.score == 0
    assert res.confidence == "LOW"


def test_liquidity_high_frequency_and_recency():
    analyzer = LiquidityAnalyzer()
    now = datetime.now(timezone.utc)
    # 10 observações recentes com preços estáveis em torno de 1000
    obs = [
        PriceDataPoint(price=1000, observed_at=now),
        PriceDataPoint(price=1050, observed_at=now),
        PriceDataPoint(price=1000, observed_at=now),
        PriceDataPoint(price=1050, observed_at=now),
        PriceDataPoint(price=1000, observed_at=now),
        PriceDataPoint(price=1000, observed_at=now),
        PriceDataPoint(price=1050, observed_at=now),
        PriceDataPoint(price=1000, observed_at=now),
        PriceDataPoint(price=1050, observed_at=now),
        PriceDataPoint(price=1000, observed_at=now),
    ]
    res = analyzer.analyze(obs, reference_time=now)
    assert res.score >= 75
    assert res.confidence == "HIGH"
