import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.entities import (
    Player,
    PlayerCard,
    MarketOpportunity,
    ActionRecommendation,
    TradingGoal,
    BankrollHistory,
    Trade,
)
from app.engines.strategy import StrategyEngine
from app.engines.action import ActionEngine
from app.services.action_service import ActionService
from app.schemas.schemas import ActionFeedbackCreate, PurchaseItem


def test_strategy_engine_tier_and_budget():
    strategy_engine = StrategyEngine()
    player_id = uuid.uuid4()
    card_id = uuid.uuid4()

    # Cenário Banca Micro (< 10.000): Teto 30% = 1.500 coins para banca de 5.000
    # Oportunidade com max_buy = 650 -> cabe no máximo 2 cartas (1.300 <= 1.500)
    opp = MarketOpportunity(
        id=uuid.uuid4(),
        card_id=card_id,
        player_id=player_id,
        observed_price=600,
        market_price=1040,
        max_buy_price=600,
        target_sell_price=1040,
        estimated_profit=388,
        roi=0.60,
        confidence="HIGH",
        liquidity_score=80,
        opportunity_score=90.0,
    )

    decision = strategy_engine.evaluate_best_action(
        available_cash=5000,
        total_equity=5000,
        inventory_cost=0,
        valid_opportunities=[opp],
    )

    assert decision.has_action is True
    assert decision.action_type == "MASS_BID"
    assert decision.recommended_quantity == 2
    assert decision.capital_limit == 1200  # 2 * 600
    assert decision.tier_percentage_applied == 0.30


def test_strategy_engine_inventory_cap_block():
    strategy_engine = StrategyEngine()
    player_id = uuid.uuid4()
    card_id = uuid.uuid4()

    # Banca de 10.000, teto de estoque 70% = 7.000.
    # Se inventory_cost já for 7.000, deve recusar novas compras.
    opp = MarketOpportunity(
        id=uuid.uuid4(),
        card_id=card_id,
        player_id=player_id,
        observed_price=600,
        market_price=1040,
        max_buy_price=650,
        target_sell_price=1040,
        estimated_profit=338,
        roi=0.52,
        confidence="HIGH",
        liquidity_score=80,
        opportunity_score=90.0,
    )

    decision = strategy_engine.evaluate_best_action(
        available_cash=3000,
        total_equity=10000,
        inventory_cost=7000,
        valid_opportunities=[opp],
    )

    assert decision.has_action is False
    assert "Limite de estoque do portfólio atingido" in decision.reason


def test_strategy_engine_player_concentration_block():
    strategy_engine = StrategyEngine()
    player_id = uuid.uuid4()
    card_id = uuid.uuid4()

    opp = MarketOpportunity(
        id=uuid.uuid4(),
        card_id=card_id,
        player_id=player_id,
        observed_price=600,
        market_price=1040,
        max_buy_price=650,
        target_sell_price=1040,
        estimated_profit=338,
        roi=0.52,
        confidence="HIGH",
        liquidity_score=80,
        opportunity_score=90.0,
    )

    # 3 cartas já em aberto desta carta/jogador
    decision = strategy_engine.evaluate_best_action(
        available_cash=5000,
        total_equity=5000,
        inventory_cost=1950,
        valid_opportunities=[opp],
        open_positions_by_player={player_id: 3},
        open_positions_by_card={card_id: 3},
    )

    assert decision.has_action is False


def test_action_engine_formatting_and_factual_why():
    strategy_engine = StrategyEngine()
    action_engine = ActionEngine()

    player = Player(id=uuid.uuid4(), name="Atleta Teste", rating=82)
    card = PlayerCard(id=uuid.uuid4(), player=player, player_id=player.id, rating=82, position="CDM", rarity="Gold", club="Benfica")

    opp = MarketOpportunity(
        id=uuid.uuid4(),
        card=card,
        card_id=card.id,
        player=player,
        player_id=player.id,
        platform="console",
        observed_price=600,
        market_price=1040,
        max_buy_price=650,
        target_sell_price=1040,
        estimated_profit=338,
        roi=0.52,
        confidence="HIGH",
        liquidity_score=80,
        opportunity_score=90.0,
    )

    decision = strategy_engine.evaluate_best_action(
        available_cash=10000,
        total_equity=10000,
        inventory_cost=0,
        valid_opportunities=[opp],
    )
    presentation = action_engine.format_action(
        decision=decision,
        sample_count=8,
        available_cash=10000,
    )

    assert "Atleta Teste" in presentation.headline
    assert "82" in presentation.headline
    assert "650" in presentation.buy_instruction
    assert "1.040" in presentation.sell_instruction
    assert "8 observações recentes" in presentation.why_explanation
    assert "5% da EA" in presentation.why_explanation
    assert "minutos" not in presentation.why_explanation.lower()
    assert "rápido" not in presentation.why_explanation.lower()


def test_action_service_bought_feedback_with_multiple_prices(db_session: Session):
    """Testa o feedback BOUGHT com compras parciais e preços variados (ex: 600, 625, 650)."""
    action_service = ActionService(db_session)
    player = Player(name="Atleta Fixture", rating=82, data_origin="test")
    db_session.add(player)
    db_session.flush()

    card = PlayerCard(
        player_id=player.id,
        game_version="FC27",
        rating=82,
        position="CDM",
        rarity="Gold",
        club="Benfica",
        data_origin="test",
    )
    db_session.add(card)
    db_session.flush()

    goal = TradingGoal(
        starting_balance=5000,
        target_balance=10000,
        current_balance=5000,
        status="ACTIVE",
        is_paper=True,
        data_origin="test",
    )
    db_session.add(goal)
    db_session.flush()

    rec = ActionRecommendation(
        trading_goal_id=goal.id,
        card_id=card.id,
        player_id=player.id,
        action_type="MASS_BID",
        strategy_name="Mass Bidding",
        player_name=player.name,
        player_rating=82,
        max_buy_price=650,
        target_sell_price=1040,
        recommended_quantity=3,
        capital_limit=1950,
        estimated_profit_per_card=338,
        estimated_total_profit=1014,
        estimated_roi=0.52,
        snapshot_market_price=1040,
        snapshot_observed_price=600,
        snapshot_liquidity_score=75,
        snapshot_confidence="HIGH",
        snapshot_opportunity_score=90.0,
        snapshot_sample_count=8,
        snapshot_available_cash=5000,
        why_explanation="Auditoria factual",
        urgency="NORMAL",
        status="active",
        is_paper=True,
        data_origin="test",
        expires_at=datetime.now(timezone.utc),
    )
    db_session.add(rec)
    db_session.commit()

    feedback_payload = ActionFeedbackCreate(
        recommendation_id=rec.id,
        action_result="BOUGHT",
        purchases=[
            PurchaseItem(buy_price=600),
            PurchaseItem(buy_price=620),
            PurchaseItem(buy_price=650),
        ],
        notes="3 cartas arrematadas abaixo do teto de 650",
    )

    feedback = action_service.record_feedback(feedback_payload, data_origin="test")
    assert feedback.action_result == "BOUGHT"
    assert feedback.quantity_bought == 3
    assert feedback.effective_price == (600 + 620 + 650) // 3  # 623 coins médio

    # Verifica se a recomendação foi para executed
    db_session.refresh(rec)
    assert rec.status == "executed"


def test_action_service_concentration_with_existing_inventory(db_session: Session):
    """Regressão: quando há estoque/posições em aberto ocupando o limite,
    deve manter reason code CONCENTRATION_LIMIT_REACHED e sugerir aguardar a venda das cartas em aberto."""
    now = datetime.now(timezone.utc)
    action_service = ActionService(db=db_session)

    player = Player(name="Gabriel Martinelli", rating=84, data_origin="test")
    db_session.add(player)
    db_session.flush()

    card = PlayerCard(
        player_id=player.id,
        game_version="FC27",
        rating=84,
        position="LW",
        rarity="Gold",
        club="Arsenal",
        data_origin="test",
        is_active=True,
    )
    db_session.add(card)
    db_session.flush()

    # Banca de 7.640 coins com posições abertas
    db_session.add(
        BankrollHistory(
            balance=5690,
            is_paper=True,
            reason="initial",
            entry_type="initial_deposit",
            data_origin="test",
            recorded_at=now,
        )
    )

    # 3 posições abertas deste jogador (atinge MAX_OPEN_POSITIONS_PER_PLAYER)
    for _ in range(3):
        trade = Trade(
            card_id=card.id,
            player_id=player.id,
            buy_price=650,
            status="open",
            is_paper_trade=True,
            data_origin="test",
            bought_at=now,
        )
        db_session.add(trade)

    opp = MarketOpportunity(
        id=uuid.uuid4(),
        card_id=card.id,
        player_id=player.id,
        observed_price=650,
        market_price=1000,
        max_buy_price=650,
        target_sell_price=1000,
        estimated_profit=300,
        roi=0.46,
        confidence="HIGH",
        liquidity_score=80,
        opportunity_score=90.0,
        data_origin="test",
        detected_at=now,
        expires_at=now + timedelta(minutes=30),
    )
    db_session.add(opp)
    db_session.commit()

    resp = action_service.verify_market(is_paper=True, data_origin="test")

    assert resp.has_action is False
    assert resp.status == "NO_ACTION"
    assert resp.no_action_reason_code == "CONCENTRATION_LIMIT_REACHED"
    assert "Aguarde a venda de cartas em aberto para liberar margem de exposição." in (resp.suggestion or "")
    assert "Gabriel Martinelli" in (resp.message or "") or "concentração" in (resp.message or "").lower()


def test_action_service_concentration_with_zero_inventory_expensive_card(db_session: Session):
    """Regressão: quando inventory_cost = 0, open_positions = 0 e a oportunidade excede o limite de concentração,
    deve manter reason code CONCENTRATION_LIMIT_REACHED, explicar que a carta é cara demais para a banca
    e NÃO sugerir aguardar a venda de cartas em aberto."""
    now = datetime.now(timezone.utc)
    action_service = ActionService(db=db_session)

    player = Player(name="Gabriel Martinelli", rating=84, data_origin="test")
    db_session.add(player)
    db_session.flush()

    card = PlayerCard(
        player_id=player.id,
        game_version="FC27",
        rating=84,
        position="LW",
        rarity="Gold",
        club="Arsenal",
        data_origin="test",
        is_active=True,
    )
    db_session.add(card)
    db_session.flush()

    # Banca de 7.640 coins, sem nenhuma posição aberta (inventory_cost = 0, open_positions = 0)
    db_session.add(
        BankrollHistory(
            balance=7640,
            is_paper=True,
            reason="initial",
            entry_type="initial_deposit",
            data_origin="test",
            recorded_at=now,
        )
    )

    # Oportunidade com max_buy_price = 3.500 coins.
    # 3.500 / 7.640 = ~45.8% da banca, excedendo o teto de 25% (1.910 coins)
    opp = MarketOpportunity(
        id=uuid.uuid4(),
        card_id=card.id,
        player_id=player.id,
        observed_price=3500,
        market_price=4500,
        max_buy_price=3500,
        target_sell_price=4500,
        estimated_profit=775,
        roi=0.22,
        confidence="HIGH",
        liquidity_score=80,
        opportunity_score=85.0,
        data_origin="test",
        detected_at=now,
        expires_at=now + timedelta(minutes=30),
    )
    db_session.add(opp)
    db_session.commit()

    resp = action_service.verify_market(is_paper=True, data_origin="test")

    assert resp.has_action is False
    assert resp.status == "NO_ACTION"
    assert resp.no_action_reason_code == "CONCENTRATION_LIMIT_REACHED"
    # Sugestão NÃO deve ser a de aguardar venda
    assert "Aguarde a venda de cartas em aberto" not in (resp.suggestion or "")
    # Deve sugerir procurar oportunidade mais barata / menor valor ou aumentar a banca
    assert "Procure uma oportunidade mais barata compatível com sua banca" in (resp.suggestion or "")
    assert "aumente a sua banca" in (resp.suggestion or "")
    # Explicação factual com valores derivados do pipeline (3.500 coins, 45,8%, 25%)
    assert "3.500" in (resp.message or "")
    assert "45,8%" in (resp.message or "")
    assert "25%" in (resp.message or "")


def test_get_current_action_is_strictly_read_only_and_does_not_create_recommendation(client, db_session: Session):
    """Prova A, B e C:
    A. GET /actions/current não cria ActionRecommendation.
    B. GET /actions/current não executa mutação/persistência quando não existe recomendação ativa.
    C. POST /actions/verify continua gerando/reavaliando recommendation.
    """
    from fastapi.testclient import TestClient
    from app.models.entities import PriceObservation

    now = datetime.now(timezone.utc)

    # 1. Configura banca Paper
    db_session.add(
        BankrollHistory(
            balance=50000,
            is_paper=True,
            reason="initial",
            entry_type="initial_deposit",
            data_origin="test",
            recorded_at=now,
        )
    )
    db_session.commit()
    t0 = now - timedelta(seconds=30)
    t1 = now
    batch_obs = [
        {"player": "Declan Rice", "rating": 83, "price": 1000, "type": "buy_now", "position": "CDM", "club": "Arsenal", "data_origin": "test", "observed_at": t0.isoformat()},
        {"player": "Declan Rice", "rating": 83, "price": 1050, "type": "buy_now", "position": "CDM", "club": "Arsenal", "data_origin": "test", "observed_at": t0.isoformat()},
        {"player": "Declan Rice", "rating": 83, "price": 1000, "type": "buy_now", "position": "CDM", "club": "Arsenal", "data_origin": "test", "observed_at": t0.isoformat()},
        {"player": "Declan Rice", "rating": 83, "price": 600, "type": "bid", "position": "CDM", "club": "Arsenal", "data_origin": "test", "observed_at": t1.isoformat()},
    ]
    resp_obs = client.post("/api/v1/observations", json=batch_obs)
    assert resp_obs.status_code == 200

    # Antes de qualquer chamada: 0 recomendações no banco
    assert db_session.query(ActionRecommendation).filter(ActionRecommendation.data_origin == "test").count() == 0

    # Chamada A: GET /actions/current deve ser estritamente read-only
    get_res = client.get("/api/v1/actions/current?is_paper=true&data_origin=test")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["has_action"] is False
    assert get_data["status"] == "NO_ACTION"

    # Confirma que NENHUMA ActionRecommendation foi criada pelo GET
    assert db_session.query(ActionRecommendation).filter(ActionRecommendation.data_origin == "test").count() == 0

    # Chamada B: POST /actions/verify realiza a reanálise explícita e gera a ActionRecommendation
    verify_res = client.post("/api/v1/actions/verify?is_paper=true&data_origin=test")
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["has_action"] is True
    assert verify_data["status"] == "ACTION_AVAILABLE"
    rec_payload = verify_data["action"]
    assert rec_payload is not None
    assert rec_payload["player_name"] == "Declan Rice"
    assert rec_payload["profit_at_max_buy"] is not None
    assert rec_payload["roi_at_max_buy"] is not None
    assert rec_payload["profit_at_max_buy"] > 0
    assert rec_payload["roi_at_max_buy"] > 0

    # Confirma que agora existe exatamente 1 ActionRecommendation persistida
    assert db_session.query(ActionRecommendation).filter(ActionRecommendation.data_origin == "test").count() == 1

    # Chamada C: GET /actions/current subsequente agora retorna a recomendação ativa sem criar duplicatas
    get_res2 = client.get("/api/v1/actions/current?is_paper=true&data_origin=test")
    assert get_res2.status_code == 200
    get_data2 = get_res2.json()
    assert get_data2["has_action"] is True
    assert get_data2["action"]["id"] == rec_payload["id"]
    assert get_data2["action"]["profit_at_max_buy"] == rec_payload["profit_at_max_buy"]
    assert get_data2["action"]["roi_at_max_buy"] == rec_payload["roi_at_max_buy"]

    # Contagem no banco permanece estritamente 1
    assert db_session.query(ActionRecommendation).filter(ActionRecommendation.data_origin == "test").count() == 1


def test_profit_and_roi_at_max_buy_exact_calculations_and_why_explanation():
    """Prova F, G, H, J:
    F. cálculo de profit_at_max_buy
    G. cálculo de roi_at_max_buy
    H. exemplo equivalente dos requisitos:
       observed=1000, max_buy=1175, target_sell=1500, tax=5%
       observed profit=425, observed ROI=42,5%
       max-buy profit=250, max-buy ROI~=21,28%
    J. 'Por que isso?' não atribui lucro observado ao max_buy e distingue claramente os cenários.
    """
    from app.engines.tax import calculate_profit, calculate_roi
    from app.engines.strategy import StrategyDecision

    # 1. Validação matemática pura do TaxEngine
    observed_price = 1000
    max_buy_price = 1175
    target_sell_price = 1500
    tax_rate = 0.05

    # net_sale = floor(1500 * 0.95) = 1425
    # Cenário A: Preço observado
    profit_observed = calculate_profit(observed_price, target_sell_price, tax_rate)
    roi_observed = calculate_roi(observed_price, target_sell_price, tax_rate)
    assert profit_observed == 425
    assert roi_observed == 0.425  # 42,5%

    # Cenário B: Preço no teto (max_buy)
    profit_max_buy = calculate_profit(max_buy_price, target_sell_price, tax_rate)
    roi_max_buy = calculate_roi(max_buy_price, target_sell_price, tax_rate)
    assert profit_max_buy == 250
    expected_roi = 250.0 / 1175.0  # ~= 0.212765957... (21,28%)
    assert abs(roi_max_buy - expected_roi) < 1e-6
    assert f"{roi_max_buy * 100:.2f}%" == "21.28%"

    # 2. Formatação no ActionEngine
    action_engine = ActionEngine()

    opp = MarketOpportunity(
        id=uuid.uuid4(),
        card_id=uuid.uuid4(),
        player_id=uuid.uuid4(),
        observed_price=observed_price,
        market_price=target_sell_price,
        max_buy_price=max_buy_price,
        target_sell_price=target_sell_price,
        estimated_profit=profit_observed,
        roi=roi_observed,
        confidence="HIGH",
        liquidity_score=80,
        opportunity_score=85.0,
        platform="console",
        data_origin="test",
    )

    decision = StrategyDecision(
        has_action=True,
        opportunity=opp,
        action_type="CONSERVATIVE_FLIP",
        strategy_name="Flip Conservador",
        strategy_type="QUICK_FLIP",
        recommended_quantity=2,
        capital_limit=max_buy_price * 2,
        estimated_profit_per_card=profit_observed,
        estimated_total_profit=profit_observed * 2,
        estimated_roi=roi_observed,
        capital_efficiency=1.5,
        urgency="NORMAL",
    )

    presentation = action_engine.format_action(
        decision=decision,
        sample_count=8,
        available_cash=10000,
    )

    # Campos estruturados preservados
    assert presentation.profit_at_max_buy == 250
    assert abs(presentation.roi_at_max_buy - expected_roi) < 1e-6
    assert presentation.estimated_profit_per_card == 425
    assert presentation.estimated_roi == 0.425
    assert presentation.snapshot_observed_price == 1000

    # Instrução de lucro destaca o teto de compra conservador
    assert "250" in presentation.profit_instruction
    assert "500" in presentation.profit_instruction  # 250 * 2

    # "Por que isso?" distingue com exatidão os cenários:
    why = presentation.why_explanation
    # Não deve afirmar que pagando 1.175 assegura 425
    assert "Pagando até 1.175 coins, a margem líquida assegura +425" not in why
    assert "assegura +425" not in why
    assert "garantido" not in why.lower()
    assert "garantida" not in why.lower()

    # Deve conter a cotação recente e seu lucro
    assert "Na cotação recente de 1.000 coins, o lucro estimado é +425 coins (ROI 42,5%)" in why
    # Deve conter o teto e seu lucro mínimo estimado
    assert "O teto de compra é 1.175 coins; comprando exatamente no teto, o lucro mínimo estimado é +250 coins (ROI ~21,3%)" in why


