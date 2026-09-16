from app.engines.opportunity_score import OpportunityScoreEngine


def test_opportunity_score_capital_efficiency():
    """Valida o princípio do requisito:

    Com banca de 5.000 coins:
    Trade A: Buy 500, Sell 750 (compra representa 10% da banca, lucro +212, ROI 42%)
    Trade B: Buy 4000, Sell 4500 (compra representa 80% da banca, lucro +275, ROI 6.8%)
    Trade A deve pontuar significativamente melhor devido à eficiência e menor risco de capital.
    """
    engine = OpportunityScoreEngine()
    bankroll = 5000

    # Trade A: Ágil, baixo comprometimento de capital
    score_a = engine.calculate(
        expected_roi=0.42,
        expected_profit=212,
        buy_price=500,
        liquidity_score=80,
        confidence="HIGH",
        bankroll=bankroll,
        age_minutes=5.0,
    )

    # Trade B: Trava 80% da banca para pouco ROI
    score_b = engine.calculate(
        expected_roi=0.068,
        expected_profit=275,
        buy_price=4000,
        liquidity_score=80,
        confidence="HIGH",
        bankroll=bankroll,
        age_minutes=5.0,
    )

    assert score_a.capital_efficiency_multiplier == 1.20
    assert score_b.capital_efficiency_multiplier == 0.60
    assert score_a.score > score_b.score


def test_opportunity_score_zero_for_loss():
    engine = OpportunityScoreEngine()
    res = engine.calculate(
        expected_roi=-0.05,
        expected_profit=-50,
        buy_price=1000,
        liquidity_score=80,
        confidence="HIGH",
        bankroll=5000,
    )
    assert res.score == 0.0
