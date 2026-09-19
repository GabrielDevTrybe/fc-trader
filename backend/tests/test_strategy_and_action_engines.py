import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.entities import Player, PlayerCard, MarketOpportunity, ActionRecommendation, TradingGoal
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
