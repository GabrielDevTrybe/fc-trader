import pytest
from sqlalchemy.orm import Session
from app.models.entities import Player, PlayerCard, BankrollHistory, TradingGoal
from app.schemas.schemas import (
    TradingGoalCreate,
    TradeCreate,
    TradeClose,
    BankrollAdjustmentCreate,
    BankrollOnboardingCreate,
    BankrollSyncCreate,
)
from app.services.goal_service import GoalService
from app.services.bankroll_service import BankrollService
from app.services.trade_service import TradeService


def test_accounting_transitions_and_goals(db_session: Session):
    goal_service = GoalService(db_session)
    bankroll_service = BankrollService(db_session)
    trade_service = TradeService(db_session)

    # 1. Estado inicial sem onboarding no modo REAL deve ser is_configured=False e saldo 0
    cap_initial = bankroll_service.get_capital_summary(is_paper=False, data_origin="test")
    assert cap_initial.is_configured is False
    assert cap_initial.cash_balance == 0

    # 2. Onboarding explícito: 5.000 saldo inicial -> 10.000 meta
    cap_onboarded = bankroll_service.onboard_bankroll(
        BankrollOnboardingCreate(cash_balance=5000, target_balance=10000),
        data_origin="test",
    )
    assert cap_onboarded.is_configured is True
    assert cap_onboarded.cash_balance == 5000
    assert cap_onboarded.total_equity == 5000
    assert cap_onboarded.inventory_cost == 0
    assert cap_onboarded.available_cash == 5000

    goal = goal_service.get_active_goal(is_paper=False, data_origin="test")
    assert goal is not None
    assert goal.status == "ACTIVE"
    assert goal.starting_balance == 5000
    assert goal.target_balance == 10000
    assert goal.current_balance == 5000

    # 3. Tentativa de criar segunda meta ACTIVE na mesma modalidade deve falhar
    with pytest.raises(ValueError) as exc:
        goal_service.create_goal(
            TradingGoalCreate(target_balance=15000, starting_balance=5000, is_paper=False),
            current_total_equity=5000,
            data_origin="test",
        )
    assert "Já existe uma meta ativa" in str(exc.value)

    # 4. Cria jogador e carta para trade
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
    db_session.commit()

    # 5. Comprar 1 carta por 600 coins
    # Regra contábil: cash_balance diminui em 600, inventory_cost aumenta em 600.
    # total_equity permanece exatamente 5.000 (permutação patrimonial).
    trade = trade_service.open_trade(
        TradeCreate(
            card_id=card.id,
            player_id=player.id,
            buy_price=600,
            is_paper_trade=False,
            data_origin="test",
        )
    )
    assert trade.trading_goal_id == goal.id

    cap_after_buy = bankroll_service.get_capital_summary(is_paper=False, data_origin="test")
    assert cap_after_buy.cash_balance == 4400
    assert cap_after_buy.inventory_cost == 600
    assert cap_after_buy.total_equity == 5000
    assert cap_after_buy.available_cash == 4400  # Sem dupla dedução!

    # 6. Vender a carta por 1.000 coins
    # EA 5% tax: net = floor(1000 * 0.95) = 950 coins.
    # Custo = 600 -> Lucro realizado = 350 coins.
    # cash_balance = 4400 + 950 = 5350 coins.
    # inventory_cost = 0.
    # total_equity = 5350 coins (+350).
    trade_service.close_trade(trade.id, TradeClose(sell_price=1000))

    cap_after_sell = bankroll_service.get_capital_summary(is_paper=False, data_origin="test")
    assert cap_after_sell.cash_balance == 5350
    assert cap_after_sell.inventory_cost == 0
    assert cap_after_sell.total_equity == 5350
    assert cap_after_sell.total_trading_profit == 350

    # Meta sincronizada com lucro do ciclo
    goal_active = goal_service.get_active_goal(is_paper=False, data_origin="test")
    assert goal_active is not None
    assert goal_active.current_balance == 5350
    goal_dto = goal_service.get_goal_read(goal_active)
    assert goal_dto.profit_in_goal == 350
    # Progresso: (5350 - 5000) / (10000 - 5000) = 350 / 5000 = 7.0%
    assert goal_dto.progress_percentage == 7.0

    # 7. Recompensa externa (+2.000 coins)
    # Regra contábil: cash_balance e total_equity sobem em 2000. Lucro de trading NÃO se altera.
    bankroll_service.record_adjustment(
        BankrollAdjustmentCreate(
            amount=2000,
            adjustment_type="reward",
            reason="Squad Battles Reward",
            is_paper=False,
        ),
        data_origin="test",
    )
    cap_after_reward = bankroll_service.get_capital_summary(is_paper=False, data_origin="test")
    assert cap_after_reward.cash_balance == 7350
    assert cap_after_reward.total_equity == 7350
    assert cap_after_reward.total_trading_profit == 350  # Intacto!
    assert cap_after_reward.total_external_rewards == 2000

    # 8. Sincronização manual de saldo: usuário informa que tem 7.500 (+150 de correção)
    # Regra contábil: delta de +150 entra em reconciliações e JAMAIS afeta total_trading_profit!
    sync_entry = bankroll_service.sync_balance(
        BankrollSyncCreate(current_actual_balance=7500, reason="Reconciliação manual no console", is_paper=False),
        data_origin="test",
    )
    assert sync_entry.amount == 150
    cap_after_sync = bankroll_service.get_capital_summary(is_paper=False, data_origin="test")
    assert cap_after_sync.cash_balance == 7500
    assert cap_after_sync.total_equity == 7500
    assert cap_after_sync.total_trading_profit == 350  # Rigorosamente intacto!
    assert cap_after_sync.total_reconciliations == 150


def test_onboarding_positive_integers_and_validation(db_session: Session):
    bankroll_service = BankrollService(db_session)

    # Aceita qualquer inteiro positivo: 10000 -> 25000
    res1 = bankroll_service.onboard_bankroll(
        BankrollOnboardingCreate(cash_balance=10000, target_balance=25000),
        data_origin="test_positive_int",
    )
    assert res1.is_configured is True
    assert res1.cash_balance == 10000

    # Aceita valores como 100000 -> 123456
    res2 = bankroll_service.onboard_bankroll(
        BankrollOnboardingCreate(cash_balance=100000, target_balance=123456),
        data_origin="test_positive_int_2",
    )
    assert res2.is_configured is True
    assert res2.cash_balance == 100000

    # Validação de negócio: target_balance deve ser estritamente maior que starting_balance
    with pytest.raises(ValueError) as exc:
        BankrollOnboardingCreate(cash_balance=50000, target_balance=50000)
    assert "estritamente maior" in str(exc.value).lower()

    with pytest.raises(ValueError) as exc:
        BankrollOnboardingCreate(cash_balance=50000, target_balance=40000)
    assert "estritamente maior" in str(exc.value).lower()


def test_onboarding_atomicity_guarantee(db_session: Session):
    from unittest.mock import patch
    bankroll_service = BankrollService(db_session)

    origin = "test_atomicity_check"

    # Simular falha durante o commit
    with patch.object(db_session, "commit", side_effect=RuntimeError("Simulated DB commit error")):
        with pytest.raises(RuntimeError):
            bankroll_service.onboard_bankroll(
                BankrollOnboardingCreate(cash_balance=12345, target_balance=54321),
                data_origin=origin,
            )

    # Verificar que o rollback garantiu atomicidade:
    # NENHUM registro de BankrollHistory foi persistido
    hist_entries = (
        db_session.query(BankrollHistory)
        .filter(BankrollHistory.data_origin == origin)
        .all()
    )
    assert len(hist_entries) == 0

    # NENHUM registro de TradingGoal foi persistido
    goals = (
        db_session.query(TradingGoal)
        .filter(TradingGoal.data_origin == origin)
        .all()
    )
    assert len(goals) == 0

    # Quando sucede, ambos são persistidos juntos
    res = bankroll_service.onboard_bankroll(
        BankrollOnboardingCreate(cash_balance=12345, target_balance=54321),
        data_origin=origin,
    )
    assert res.is_configured is True
    assert res.cash_balance == 12345

    hist_entries_after = (
        db_session.query(BankrollHistory)
        .filter(BankrollHistory.data_origin == origin)
        .all()
    )
    assert len(hist_entries_after) == 1
    assert hist_entries_after[0].balance == 12345

    goals_after = (
        db_session.query(TradingGoal)
        .filter(TradingGoal.data_origin == origin)
        .all()
    )
    assert len(goals_after) == 1
    assert goals_after[0].target_balance == 54321

