from datetime import datetime, timedelta, timezone
from app.engines.market_price import MarketPriceEngine, PriceDataPoint


def test_insufficient_data():
    engine = MarketPriceEngine(min_samples=3)
    # Apenas 2 observações
    obs = [
        PriceDataPoint(price=1000),
        PriceDataPoint(price=1050),
    ]
    res = engine.calculate_fair_price(obs)
    assert not res.has_sufficient_data
    assert res.market_price is None
    assert res.confidence == "LOW"
    assert "Dados insuficientes" in res.reason


def test_outlier_detection_example_from_requirements():
    """Valida o exemplo exato citado nos requisitos do usuário:

    650, 1000, 1000, 1050, 1050, 1100, 10000 -> 10.000 é outlier.
    """
    engine = MarketPriceEngine(min_samples=3)
    prices = [650, 1000, 1000, 1050, 1050, 1100, 10000]
    obs = [PriceDataPoint(price=p) for p in prices]

    res = engine.calculate_fair_price(obs)
    assert res.has_sufficient_data
    # 10.000 deve ser identificado e isolado como outlier
    assert 10000 in res.outliers
    # O preço de mercado estimado deve ficar próximo ao agrupamento real (~1000-1050), nunca puxado por 10.000
    assert res.market_price is not None
    assert 900 <= res.market_price <= 1100


def test_recency_weighting():
    engine = MarketPriceEngine(min_samples=3, decay_half_life_hours=6.0)
    now = datetime.now(timezone.utc)

    # 3 observações antigas de 1000 (há 24h) e 1 recente de 2000 (agora)
    obs = [
        PriceDataPoint(price=1000, observed_at=now - timedelta(hours=24)),
        PriceDataPoint(price=1000, observed_at=now - timedelta(hours=24)),
        PriceDataPoint(price=1000, observed_at=now - timedelta(hours=24)),
        PriceDataPoint(price=1500, observed_at=now),
    ]
    res = engine.calculate_fair_price(obs, reference_time=now)
    # Com decaimento, o preço recente de 1500 deve puxar a média para cima em relação a uma média simples
    assert res.market_price is not None
    assert res.market_price > 1150
