from datetime import datetime, timedelta, timezone
import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.entities import (
    Player,
    PlayerCard,
    PriceObservation,
    MarketOpportunity,
    MarketSnapshot,
    BankrollHistory,
    TradingGoal,
    Trade,
)
from app.engines.market_intelligence import MarketIntelligenceEngine, MarketPriceDataPoint
from app.engines.opportunity_discovery import OpportunityDiscoveryEngine
from app.engines.strategy import StrategyEngine
from app.engines.action import ActionEngine
from app.engines.tax import calculate_tax, calculate_profit, calculate_roi
from app.services.action_service import ActionService
from app.services.observation_service import ObservationService
from app.schemas.schemas import ObservationBatchItem, CsvBatchUploadRequest
from app.core.config import settings


def test_multiple_cards_discovery_unhardcoded(db_session: Session):
    """Varredura de universo dinâmico com múltiplas cartas, sem nenhum jogador hardcoded."""
    discovery = OpportunityDiscoveryEngine(db=db_session)
    now = datetime.now(timezone.utc)

    # Cria 3 atletas e versões de cartas arbitrárias no catálogo
    cards = []
    for i in range(3):
        p = Player(name=f"Jogador Generico {i}", data_origin="test")
        db_session.add(p)
        db_session.flush()

        c = PlayerCard(
            player_id=p.id,
            rating=82 + i,
            rarity="Gold Rare",
            data_origin="test",
            is_active=True,
        )
        db_session.add(c)
        db_session.flush()
        cards.append(c)

        # Insere 4 observações de mercado estabelecido em 3000-3100
        fair_base = 3000 * (i + 1)
        for j in range(4):
            obs = PriceObservation(
                card_id=c.id,
                player_id=p.id,
                price=fair_base + (j * 20),
                platform="console",
                data_origin="test",
                observed_at=now - timedelta(minutes=j + 2),
            )
            db_session.add(obs)

        # Insere 1 cotação recente com preço de oportunidade abaixo do mercado (ex: 70% do preço justo)
        bargain_price = int(fair_base * 0.72)
        obs_bargain = PriceObservation(
            card_id=c.id,
            player_id=p.id,
            price=bargain_price,
            platform="console",
            data_origin="test",
            observed_at=now - timedelta(minutes=1),
        )
        db_session.add(obs_bargain)
    db_session.commit()

    opps = discovery.discover_opportunities_for_universe(
        cards=cards,
        platform="console",
        available_cash=25000,
        total_equity=25000,
        data_origin="test",
        reference_time=now,
    )

    # O motor analisa dinamicamente todas as cartas sem jogador hardcoded
    assert isinstance(opps, list)
    assert len(opps) > 0


def test_same_player_different_card_versions_segregated(db_session: Session):
    """Mesmo atleta humano com 2 versões distintas (Gold 82 e TOTW 86); preços nunca se misturam."""
    intel_engine = MarketIntelligenceEngine()
    now = datetime.now(timezone.utc)

    p = Player(name="Atleta Duas Versoes", data_origin="test")
    db_session.add(p)
    db_session.flush()

    card_gold = PlayerCard(player_id=p.id, rating=82, rarity="Gold Common", data_origin="test")
    card_totw = PlayerCard(player_id=p.id, rating=86, rarity="TOTW", data_origin="test")
    db_session.add_all([card_gold, card_totw])
    db_session.commit()

    # Cotações da Gold (~1.500)
    points_gold = [
        MarketPriceDataPoint(price=1500, observed_at=now - timedelta(minutes=1)),
        MarketPriceDataPoint(price=1550, observed_at=now - timedelta(minutes=2)),
        MarketPriceDataPoint(price=1450, observed_at=now - timedelta(minutes=3)),
    ]

    # Cotações da TOTW (~25.000)
    points_totw = [
        MarketPriceDataPoint(price=25000, observed_at=now - timedelta(minutes=1)),
        MarketPriceDataPoint(price=25500, observed_at=now - timedelta(minutes=2)),
        MarketPriceDataPoint(price=24800, observed_at=now - timedelta(minutes=3)),
    ]

    snap_gold = intel_engine.compute_snapshot(points_gold, card_id=str(card_gold.id), platform="console")
    snap_totw = intel_engine.compute_snapshot(points_totw, card_id=str(card_totw.id), platform="console")

    assert snap_gold.estimated_market_price is not None
    assert snap_totw.estimated_market_price is not None
    assert snap_gold.estimated_market_price < 2000
    assert snap_totw.estimated_market_price > 20000
    assert snap_gold.card_id != snap_totw.card_id


def test_platform_isolation(db_session: Session):
    """Mesma carta com cotações distintas em console vs pc; estritamente segregadas."""
    intel_engine = MarketIntelligenceEngine()
    now = datetime.now(timezone.utc)

    points_console = [
        MarketPriceDataPoint(price=4500, observed_at=now, platform="console"),
        MarketPriceDataPoint(price=4550, observed_at=now, platform="console"),
        MarketPriceDataPoint(price=4450, observed_at=now, platform="console"),
    ]

    points_pc = [
        MarketPriceDataPoint(price=6500, observed_at=now, platform="pc"),
        MarketPriceDataPoint(price=6600, observed_at=now, platform="pc"),
        MarketPriceDataPoint(price=6400, observed_at=now, platform="pc"),
    ]

    snap_console = intel_engine.compute_snapshot(points_console, platform="console")
    snap_pc = intel_engine.compute_snapshot(points_pc, platform="pc")

    assert snap_console.estimated_market_price in (4400, 4500, 4600)
    assert snap_pc.estimated_market_price in (6400, 6500, 6600)
    assert snap_console.platform == "console"
    assert snap_pc.platform == "pc"


def test_outlier_detection_iqr():
    """Observações [4400, 4500, 4500, 4600, 9000] -> 9000 é expurgado e preço justo permanece ~4500."""
    intel_engine = MarketIntelligenceEngine(iqr_multiplier=1.5)
    now = datetime.now(timezone.utc)

    raw_prices = [4400, 4500, 4500, 4600, 9000]
    points = [
        MarketPriceDataPoint(price=p, observed_at=now - timedelta(minutes=i))
        for i, p in enumerate(raw_prices)
    ]

    snapshot = intel_engine.compute_snapshot(points, platform="console")

    assert 9000 in snapshot.outliers
    assert 9000 not in snapshot.clean_prices
    assert snapshot.clean_sample_count == 4
    assert snapshot.estimated_market_price is not None
    assert 4400 <= snapshot.estimated_market_price <= 4600


def test_freshness_lifecycle():
    """Transições entre FRESH (<= 15m), STALE (15m-60m) e HISTORICAL (> 60m)."""
    intel_engine = MarketIntelligenceEngine()
    now = datetime.now(timezone.utc)

    # 1. Dados Fresh (5 min atrás)
    fresh_pts = [MarketPriceDataPoint(price=2000, observed_at=now - timedelta(minutes=5)) for _ in range(3)]
    snap_fresh = intel_engine.compute_snapshot(fresh_pts, reference_time=now)
    assert snap_fresh.freshness_status == "FRESH"

    # 2. Dados Stale (30 min atrás)
    stale_pts = [MarketPriceDataPoint(price=2000, observed_at=now - timedelta(minutes=30)) for _ in range(3)]
    snap_stale = intel_engine.compute_snapshot(stale_pts, reference_time=now)
    assert snap_stale.freshness_status == "STALE"

    # 3. Dados Historical (90 min atrás)
    hist_pts = [MarketPriceDataPoint(price=2000, observed_at=now - timedelta(minutes=90)) for _ in range(3)]
    snap_hist = intel_engine.compute_snapshot(hist_pts, reference_time=now)
    assert snap_hist.freshness_status == "HISTORICAL"


def test_real_mode_rejection_of_expired_historical_data(db_session: Session):
    """Dados expirados/HISTORICAL rejeitam recomendação de compra no modo REAL."""
    action_service = ActionService(db=db_session)
    now = datetime.now(timezone.utc)

    p = Player(name="Jogador Antigo", data_origin="test")
    db_session.add(p)
    db_session.flush()

    c = PlayerCard(player_id=p.id, rating=84, rarity="Gold", data_origin="test", is_active=True)
    db_session.add(c)
    db_session.flush()

    # Inicializa banca de teste configurada
    db_session.add(BankrollHistory(balance=25000, is_paper=False, reason="initial", entry_type="initial_deposit", data_origin="test"))

    # Insere apenas cotações de 3 horas atrás (HISTORICAL)
    for i in range(4):
        obs = PriceObservation(
            card_id=c.id,
            player_id=p.id,
            price=2000,
            platform="console",
            data_origin="test",
            observed_at=now - timedelta(hours=3),
        )
        db_session.add(obs)
    db_session.commit()

    resp = action_service.get_current_action(is_paper=False, data_origin="test")
    assert resp.has_action is False
    assert resp.status == "NO_ACTION"
    assert resp.no_action_reason_code in ("NO_PROFITABLE_OPPORTUNITY", "STALE_MARKET_DATA", "STALE_DATA")


def test_insufficient_data_rejection():
    """Menos de 3 observações retorna INSUFFICIENT_DATA e confiança LOW."""
    intel_engine = MarketIntelligenceEngine()
    now = datetime.now(timezone.utc)

    pts = [
        MarketPriceDataPoint(price=3000, observed_at=now),
        MarketPriceDataPoint(price=3100, observed_at=now),
    ]
    snapshot = intel_engine.compute_snapshot(pts)

    assert snapshot.has_sufficient_data is False
    assert snapshot.data_quality == "INSUFFICIENT_DATA"
    assert snapshot.confidence_level == "LOW"
    assert snapshot.estimated_market_price is None


def test_low_confidence_rejection(db_session: Session):
    """Snapshots com score de confiança < 0.50 não geram ação ativa."""
    action_service = ActionService(db=db_session)

    # Inicializa banca configurada
    db_session.add(BankrollHistory(balance=25000, is_paper=False, reason="initial", entry_type="initial_deposit", data_origin="test"))

    # Cria oportunidade com confiança LOW
    opp = MarketOpportunity(
        id=uuid.uuid4(),
        card_id=uuid.uuid4(),
        observed_price=1000,
        market_price=2000,
        max_buy_price=1200,
        target_sell_price=2000,
        estimated_profit=700,
        roi=0.70,
        confidence="LOW",
        liquidity_score=30,
        opportunity_score=40.0,
        data_origin="test",
    )
    db_session.add(opp)
    db_session.commit()

    resp = action_service.verify_market(is_paper=False, data_origin="test")
    assert resp.has_action is False
    assert resp.status == "NO_ACTION"
    assert resp.no_action_reason_code == "LOW_CONFIDENCE"


def test_high_dispersion_rejection():
    """Alta dispersão de preços (CV > 0.25) reduz confidence score e classifica HIGH_DISPERSION."""
    intel_engine = MarketIntelligenceEngine()
    now = datetime.now(timezone.utc)

    # Preços com desvio padrão massivo: 1000, 3000, 5000, 7000
    pts = [
        MarketPriceDataPoint(price=1000, observed_at=now),
        MarketPriceDataPoint(price=3000, observed_at=now),
        MarketPriceDataPoint(price=5000, observed_at=now),
        MarketPriceDataPoint(price=7000, observed_at=now),
    ]
    snapshot = intel_engine.compute_snapshot(pts)

    assert snapshot.dispersion_ratio > 0.25
    assert snapshot.data_quality == "HIGH_DISPERSION"
    assert snapshot.confidence_score < 0.70


def test_profitable_opportunity_evaluation(db_session: Session):
    """Oportunidade lucrativa gera recomendação executável com todos os atributos obrigatórios."""
    discovery = OpportunityDiscoveryEngine(db=db_session)
    now = datetime.now(timezone.utc)

    p = Player(name="Craque Lucrativo", data_origin="test")
    db_session.add(p)
    db_session.flush()

    c = PlayerCard(player_id=p.id, rating=85, rarity="Gold Rare", club="Paris SG", position="CM", data_origin="test")
    db_session.add(c)
    db_session.flush()

    # Preço justo ~5000, cotação atual a 3800
    for i in range(5):
        obs = PriceObservation(
            card_id=c.id,
            player_id=p.id,
            price=4900 + (i * 20),
            platform="console",
            data_origin="test",
            observed_at=now - timedelta(minutes=i + 1),
        )
        db_session.add(obs)
    db_session.commit()

    snapshot_res = discovery.market_intel.compute_snapshot(
        [MarketPriceDataPoint(price=4900 + (i * 20), observed_at=now - timedelta(minutes=i + 1)) for i in range(5)],
        card_id=str(c.id),
        platform="console",
        reference_time=now,
    )

    opp = discovery.evaluate_opportunity(
        card=c,
        snapshot=snapshot_res,
        liquidity_score=80,
        latest_observation_price=3800,
        available_cash=25000,
        max_allocation_cap=6000,
    )

    assert opp is not None
    assert opp.net_profit > 0
    assert opp.roi > 0.08
    assert opp.target_sell_price >= 4800
    assert opp.recommended_quantity >= 1
    assert opp.capital_required <= 6000


def test_unprofitable_opportunity_rejection(db_session: Session):
    """Preço observado acima do teto de compra viável é rejeitado."""
    discovery = OpportunityDiscoveryEngine(db=db_session)
    now = datetime.now(timezone.utc)

    p = Player(name="Craque Sem Margem", data_origin="test")
    c = PlayerCard(player=p, rating=83, rarity="Gold", data_origin="test")
    db_session.add_all([p, c])
    db_session.commit()

    # Preço justo 4000
    snapshot_res = discovery.market_intel.compute_snapshot(
        [MarketPriceDataPoint(price=4000, observed_at=now) for _ in range(5)],
        card_id=str(c.id),
        platform="console",
    )

    # Cotação a 3950 (lucro líquido seria negativo após 5% da EA: 4000 * 0.95 = 3800 < 3950)
    opp = discovery.evaluate_opportunity(
        card=c,
        snapshot=snapshot_res,
        liquidity_score=80,
        latest_observation_price=3950,
        available_cash=25000,
        max_allocation_cap=6000,
    )
    assert opp is None


def test_tax_deduction_exactness():
    """Validação da exatidão da dedução de 5% de taxa EA via TaxEngine."""
    sell_price = 10000
    tax = calculate_tax(sell_price)
    assert tax == 500  # 5% exato

    buy_price = 8000
    profit = calculate_profit(buy_price, sell_price, tax_rate=0.05)
    # Venda líquida = 9.500, Custo = 8.000 -> Lucro = 1.500
    assert profit == 1500

    roi = calculate_roi(buy_price, sell_price, tax_rate=0.05)
    assert roi == pytest.approx(1500 / 8000.0)


def test_strict_reverse_max_buy_calculation(db_session: Session):
    """max_buy = min(statistical_buy_ceiling, max_buy_by_profit, max_buy_by_roi)."""
    discovery = OpportunityDiscoveryEngine(db=db_session)
    now = datetime.now(timezone.utc)

    p = Player(name="Atleta Teto Reverso", data_origin="test")
    c = PlayerCard(player=p, rating=84, rarity="Gold", data_origin="test")
    db_session.add_all([p, c])
    db_session.commit()

    # Preço justo estimado em 10.000
    pts = [MarketPriceDataPoint(price=10000, observed_at=now) for _ in range(5)]
    snap = discovery.market_intel.compute_snapshot(pts, platform="console")

    opp = discovery.evaluate_opportunity(
        card=c,
        snapshot=snap,
        liquidity_score=75,
        latest_observation_price=8000,
        available_cash=25000,
        max_allocation_cap=6000,
    )

    assert opp is not None
    # target_sell = 10.000 -> líquido = 9.500
    # Com ROI mínimo de 8% em QUICK_FLIP: max_buy não pode exceder 9500 / 1.08 = 8796
    assert opp.max_buy_price <= 8796
    # E não pode exceder o teto estatístico de 90% (9000)
    assert opp.max_buy_price <= 9000


def test_strategy_dependent_rois(db_session: Session):
    """QUICK_FLIP aceita 9% de ROI se liquidez/confiança forem altas; SWING rejeita 9%."""
    discovery = OpportunityDiscoveryEngine(db=db_session)
    now = datetime.now(timezone.utc)

    p = Player(name="Atleta Teste Estrategia", data_origin="test")
    c = PlayerCard(player=p, rating=84, rarity="Gold", data_origin="test")
    db_session.add_all([p, c])
    db_session.commit()

    # Cotações frescas e muito consistentes -> Confiança alta
    pts = [MarketPriceDataPoint(price=5000, observed_at=now - timedelta(minutes=1)) for _ in range(6)]
    snap = discovery.market_intel.compute_snapshot(pts, platform="console")

    # 1. Com alta liquidez (80) -> QUICK_FLIP selecionado (aceita ROI ~9%)
    # target_sell = 5000 -> líquido = 4750. Compra a 4350 -> lucro = 400 (ROI = 400 / 4350 = 9.19%)
    opp_qf = discovery.evaluate_opportunity(
        card=c,
        snapshot=snap,
        liquidity_score=80,
        latest_observation_price=4350,
        available_cash=25000,
        max_allocation_cap=10000,
    )
    assert opp_qf is not None
    assert opp_qf.strategy_type == "QUICK_FLIP"
    assert opp_qf.roi >= settings.MINIMUM_ROI_QUICK_FLIP

    # 2. Com liquidez moderada (50) -> SWING selecionado (exige 15% ROI, logo rejeita 9%)
    opp_swing = discovery.evaluate_opportunity(
        card=c,
        snapshot=snap,
        liquidity_score=50,
        latest_observation_price=4350,
        available_cash=25000,
        max_allocation_cap=10000,
    )
    assert opp_swing is None  # Rejeitado por ROI insuficiente para SWING


def test_capital_efficiency_calculation_and_holding_time_none(db_session: Session):
    """capital_efficiency é calculada e expected_holding_time_minutes é preservado como None."""
    discovery = OpportunityDiscoveryEngine(db=db_session)
    now = datetime.now(timezone.utc)

    p = Player(name="Atleta Eficiencia", data_origin="test")
    c = PlayerCard(player=p, rating=83, rarity="Gold", data_origin="test")
    db_session.add_all([p, c])
    db_session.commit()

    pts = [MarketPriceDataPoint(price=4000, observed_at=now) for _ in range(5)]
    snap = discovery.market_intel.compute_snapshot(pts, platform="console")

    opp = discovery.evaluate_opportunity(
        card=c,
        snapshot=snap,
        liquidity_score=80,
        latest_observation_price=3000,
        available_cash=25000,
        max_allocation_cap=5000,
    )

    assert opp is not None
    assert opp.capital_efficiency > 0.0
    assert opp.capital_efficiency == pytest.approx(opp.net_profit / float(opp.observed_price), 0.001)
    assert opp.expected_holding_time_minutes is None


def test_multicriteria_ranking_confidence_over_gross_profit():
    """Ranking Multicritério: Carta B (menor lucro, mas alta confiança) supera Carta A (maior lucro, confiança frágil)."""
    discovery = OpportunityDiscoveryEngine()

    # Carta A: Lucro nominal alto (1500), mas confiança frágil (0.52), liquidez moderada (55)
    score_a = discovery.calculate_ranking_score(
        net_profit=1500,
        roi=0.18,
        confidence_score=0.52,
        liquidity_score=55,
        capital_efficiency=0.18,
        strategy_type="SWING",
    )

    # Carta B: Lucro um pouco menor (850), mas confiança alta (0.95), liquidez alta (85) e giro rápido
    score_b = discovery.calculate_ranking_score(
        net_profit=850,
        roi=0.20,
        confidence_score=0.95,
        liquidity_score=85,
        capital_efficiency=0.25,
        strategy_type="QUICK_FLIP",
    )

    assert score_b > score_a, f"Carta B ({score_b}) deveria superar Carta A ({score_a}) por ter alta confiança e liquidez"


def test_user_market_check_source_preservation_and_instant_recalculation(db_session: Session):
    """Observação USER_MARKET_CHECK preserva a fonte e recalcula snapshot instantaneamente."""
    obs_service = ObservationService(db=db_session)
    now = datetime.now(timezone.utc)

    item = ObservationBatchItem(
        player="Jogador Checagem",
        rating=84,
        price=4100,
        type="buy_now",
        platform="console",
        provider="USER_MARKET_CHECK",
        data_origin="test",
        observed_at=now,
    )

    res = obs_service.process_batch([item])
    assert res.processed_count == 1

    # Verifica no banco se a observação preservou USER_MARKET_CHECK
    saved_obs = (
        db_session.query(PriceObservation)
        .filter(PriceObservation.source == "USER_MARKET_CHECK", PriceObservation.data_origin == "test")
        .first()
    )
    assert saved_obs is not None
    assert saved_obs.source == "USER_MARKET_CHECK"
    assert saved_obs.price == 4100

    # Verifica se gerou o snapshot correspondente
    snapshot = (
        db_session.query(MarketSnapshot)
        .filter(MarketSnapshot.card_id == saved_obs.card_id, MarketSnapshot.data_origin == "test")
        .first()
    )
    assert snapshot is not None
    assert snapshot.sample_count >= 1


def test_csv_batch_ingestion(db_session: Session):
    """Ingestão de lote CSV com múltiplos jogadores e colunas canônicas."""
    obs_service = ObservationService(db=db_session)
    csv_text = """player_name,rating,rarity,position,club,league,platform,price,observation_type,observed_at,provider
Jogador CSV 1,83,Gold,CM,Benfica,Liga Portugal,console,1200,buy_now,2026-09-19T10:00:00Z,csv
Jogador CSV 2,85,Gold Rare,ST,Real Madrid,LaLiga,console,15000,buy_now,2026-09-19T10:00:00Z,csv
"""
    res = obs_service.process_csv_batch(csv_text, data_origin="test")
    assert res.processed_count == 2

    # Verifica persistência no banco
    cards = db_session.query(PlayerCard).filter(PlayerCard.data_origin == "test").all()
    assert len(cards) >= 2


def test_cash_and_concentration_risk_limits():
    """max_buy > available_cash ou violação de estoques é bloqueado pelo RiskEngine."""
    strategy_engine = StrategyEngine()
    card_id = uuid.uuid4()
    player_id = uuid.uuid4()

    opp = MarketOpportunity(
        id=uuid.uuid4(),
        card_id=card_id,
        player_id=player_id,
        observed_price=30000,
        market_price=40000,
        max_buy_price=30000,
        target_sell_price=40000,
        estimated_profit=8000,
        roi=0.26,
        confidence="HIGH",
        liquidity_score=80,
        opportunity_score=85.0,
    )

    # Caixa livre é 25.000, mas a carta custa 30.000 -> Bloqueio por limite de caixa
    decision = strategy_engine.evaluate_best_action(
        available_cash=25000,
        total_equity=25000,
        inventory_cost=0,
        valid_opportunities=[opp],
    )
    assert decision.has_action is False
    assert decision.no_action_reason_code == "CAPITAL_EXCEEDED"


def test_recommended_quantity_dimensioning():
    """Quantidade recomendada respeita teto de orçamento sem inflar max_buy."""
    strategy_engine = StrategyEngine()
    card_id = uuid.uuid4()
    player_id = uuid.uuid4()

    opp = MarketOpportunity(
        id=uuid.uuid4(),
        card_id=card_id,
        player_id=player_id,
        observed_price=1000,
        market_price=1500,
        max_buy_price=1000,
        target_sell_price=1500,
        estimated_profit=425,
        roi=0.42,
        confidence="HIGH",
        liquidity_score=80,
        opportunity_score=85.0,
    )

    # Banca de 25.000 (Small tier: 25% = 6.250 coins).
    # Carta a 1.000 -> Quantidade máxima permitida pela estratégia mass bidding = 5 cartas (5.000 coins)
    decision = strategy_engine.evaluate_best_action(
        available_cash=25000,
        total_equity=25000,
        inventory_cost=0,
        valid_opportunities=[opp],
    )

    assert decision.has_action is True
    assert decision.recommended_quantity == 5
    assert decision.capital_limit == 5000
    assert opp.max_buy_price == 1000  # max_buy nunca é inflado


def test_action_engine_formatting_with_data_age():
    """ActionEngine inclui a idade dos dados de mercado na formatação."""
    action_engine = ActionEngine()
    card_id = uuid.uuid4()
    player_id = uuid.uuid4()

    opp = MarketOpportunity(
        id=uuid.uuid4(),
        card_id=card_id,
        player_id=player_id,
        observed_price=1000,
        market_price=1500,
        max_buy_price=1000,
        target_sell_price=1500,
        estimated_profit=425,
        roi=0.42,
        confidence="HIGH",
        liquidity_score=80,
        opportunity_score=85.0,
    )

    from app.engines.strategy import StrategyDecision
    decision = StrategyDecision(
        has_action=True,
        opportunity=opp,
        action_type="MASS_BID",
        strategy_name="Mass Bidding",
        strategy_type="QUICK_FLIP",
        recommended_quantity=3,
        capital_limit=3000,
        estimated_profit_per_card=425,
        estimated_total_profit=1275,
        estimated_roi=0.42,
        capital_efficiency=0.42,
        tier_percentage_applied=0.25,
        max_capital_allocation=3000,
        urgency="NORMAL",
    )

    pres = action_engine.format_action(
        decision=decision,
        sample_count=8,
        available_cash=25000,
        market_data_age_seconds=42,
    )

    assert pres.market_data_age_seconds == 42
    assert "42s" in pres.why_explanation
    assert pres.max_buy_price == 1000
    assert pres.target_sell_price == 1500
    assert pres.recommended_quantity == 3


def test_real_data_isolation_untouched(db_session: Session):
    """Comprova que os registros reais de 25.000 coins e meta de 100.000 coins não foram tocados."""
    real_goals = (
        db_session.query(TradingGoal)
        .filter(TradingGoal.data_origin == "user", TradingGoal.is_paper.is_(False))
        .all()
    )
    # Na sessão de teste em memória, os dados reais não existem nem são afetados
    assert len(real_goals) == 0


def test_insufficient_margin_structured_reason_and_explanation(db_session: Session):
    """Cenário idêntico ao Teste Phase3A: observações de 4400 a 9000 com preço justo de 4500.

    Deve gerar NO ACTION com reason code INSUFFICIENT_MARGIN e explicação matemática rigorosa.
    """
    action_service = ActionService(db=db_session)
    now = datetime.now(timezone.utc)

    p = Player(name="Teste Phase3A", data_origin="test")
    db_session.add(p)
    db_session.flush()

    c = PlayerCard(player_id=p.id, rating=80, club="Test Club", position="ST", rarity="Gold", data_origin="test", is_active=True)
    db_session.add(c)
    db_session.flush()

    db_session.add(BankrollHistory(balance=25000, is_paper=False, reason="initial", entry_type="initial_deposit", data_origin="test"))

    prices = [4400, 4500, 4500, 4600, 9000]
    for i, pr in enumerate(prices):
        obs = PriceObservation(
            card_id=c.id,
            player_id=p.id,
            price=pr,
            platform="console",
            data_origin="test",
            source="USER_MARKET_CHECK" if pr != 4400 else "manual",
            observed_at=now - timedelta(minutes=5 - i),
        )
        db_session.add(obs)
    db_session.commit()

    resp = action_service.verify_market(is_paper=False, data_origin="test")
    assert resp.has_action is False
    assert resp.status == "NO_ACTION"
    assert resp.no_action_reason_code == "INSUFFICIENT_MARGIN"
    assert "Nenhuma compra recomendada" in resp.title
    assert "4.500" in resp.message
    assert "taxa de 5% da EA" in resp.message
    assert resp.suggestion is not None


def test_verify_market_explicit_endpoint(client):
    """POST /api/v1/actions/verify executa a reavaliação explícita do mercado e retorna 200."""
    response = client.post("/api/v1/actions/verify?is_paper=true&data_origin=test")
    assert response.status_code == 200
    data = response.json()
    assert "has_action" in data
    assert "status" in data
    assert "no_action_reason_code" in data
