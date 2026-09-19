from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import BankrollHistory, Trade, TradingGoal
from app.schemas.schemas import (
    BankrollSummary,
    BankrollMilestone,
    BankrollCapitalSummary,
    BankrollAdjustmentCreate,
    BankrollOnboardingCreate,
    BankrollSyncCreate,
)

MILESTONE_TARGETS = [
    (10_000, "10k"),
    (25_000, "25k"),
    (50_000, "50k"),
    (100_000, "100k"),
    (250_000, "250k"),
    (500_000, "500k"),
    (1_000_000, "1M"),
]


class BankrollService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_capital_summary(self, is_paper: bool = False, data_origin: str = "user") -> BankrollCapitalSummary:
        """Calcula as métricas patrimoniais contábeis sem dupla dedução, garantindo isolamento total."""
        # 1. Moedas líquidas disponíveis em caixa (cash_balance)
        latest = (
            self.db.query(BankrollHistory)
            .filter(
                BankrollHistory.is_paper == is_paper,
                BankrollHistory.data_origin == data_origin,
            )
            .order_by(BankrollHistory.recorded_at.desc())
            .first()
        )

        if not is_paper:
            # Em modo REAL, se o usuário ainda não cadastrou sua banca, NÃO fazemos fallback artificial!
            if not latest:
                return BankrollCapitalSummary(
                    total_equity=0,
                    cash_balance=0,
                    available_cash=0,
                    inventory_cost=0,
                    open_positions_count=0,
                    total_trading_profit=0,
                    total_external_rewards=0,
                    total_external_expenses=0,
                    total_reconciliations=0,
                    total_external_adjustments=0,
                    is_configured=False,
                    is_paper=False,
                )
            cash_balance = latest.balance
            is_configured = True
        else:
            cash_balance = latest.balance if latest else settings.INITIAL_BANKROLL
            is_configured = True

        # 2. Custo de estoque das cartas abertas (inventory_cost) pertencentes à modalidade e data_origin
        open_trades = (
            self.db.query(Trade)
            .filter(
                Trade.is_paper_trade == is_paper,
                Trade.data_origin == data_origin,
                Trade.status == "open",
            )
            .all()
        )
        inventory_cost = sum(t.buy_price for t in open_trades)

        # 3. Patrimônio Total = caixa líquido + estoque
        total_equity = cash_balance + inventory_cost

        # 4. Moedas disponíveis para novas compras = exatamente cash_balance (já deduzido na compra)
        available_cash = max(0, cash_balance)

        # 5. Lucro realizado acumulado em trades (estritamente operações de trade)
        sold_trades = (
            self.db.query(Trade)
            .filter(
                Trade.is_paper_trade == is_paper,
                Trade.data_origin == data_origin,
                Trade.status == "sold",
            )
            .all()
        )
        total_trading_profit = sum(t.profit for t in sold_trades if t.profit is not None)

        # 6. Histórico contábil externo e reconciliações
        all_hist = (
            self.db.query(BankrollHistory)
            .filter(
                BankrollHistory.is_paper == is_paper,
                BankrollHistory.data_origin == data_origin,
            )
            .all()
        )

        total_external_rewards = sum(
            h.amount for h in all_hist
            if h.amount and (h.adjustment_type == "reward" or (h.entry_type == "external_adjustment" and h.amount > 0))
        )
        total_external_expenses = sum(
            h.amount for h in all_hist
            if h.amount and (h.adjustment_type == "external_purchase" or (h.entry_type == "external_adjustment" and h.amount < 0))
        )
        total_reconciliations = sum(
            h.amount for h in all_hist
            if h.amount and (h.entry_type == "manual_reconciliation" or h.adjustment_type == "reconciliation")
        )
        total_external_adjustments = total_external_rewards + total_external_expenses + total_reconciliations

        return BankrollCapitalSummary(
            total_equity=total_equity,
            cash_balance=cash_balance,
            available_cash=available_cash,
            inventory_cost=inventory_cost,
            open_positions_count=len(open_trades),
            total_trading_profit=total_trading_profit,
            total_external_rewards=total_external_rewards,
            total_external_expenses=total_external_expenses,
            total_reconciliations=total_reconciliations,
            total_external_adjustments=total_external_adjustments,
            is_configured=is_configured,
            is_paper=is_paper,
        )

    def onboard_bankroll(self, payload: BankrollOnboardingCreate, data_origin: str = "user") -> BankrollCapitalSummary:
        """Configura a banca inicial REAL e a meta inicial do ciclo sem inferência artificial com garantia atômica."""
        if payload.target_balance <= payload.cash_balance:
            raise ValueError("A meta de coins deve ser estritamente maior que o saldo inicial")

        now = datetime.now(timezone.utc)

        try:
            # Registra o depósito inicial de banca
            entry = BankrollHistory(
                balance=payload.cash_balance,
                amount=payload.cash_balance,
                entry_type="initial_deposit",
                reason="Banca Inicial Configurada",
                is_paper=False,
                data_origin=data_origin,
                recorded_at=now,
            )
            self.db.add(entry)

            # Cria ou atualiza a meta ativa
            existing_goal = (
                self.db.query(TradingGoal)
                .filter(
                    TradingGoal.is_paper == False,
                    TradingGoal.status == "ACTIVE",
                    TradingGoal.data_origin == data_origin,
                )
                .first()
            )
            if existing_goal:
                existing_goal.starting_balance = payload.cash_balance
                existing_goal.target_balance = payload.target_balance
                existing_goal.current_balance = payload.cash_balance
            else:
                goal = TradingGoal(
                    starting_balance=payload.cash_balance,
                    target_balance=payload.target_balance,
                    current_balance=payload.cash_balance,
                    status="ACTIVE",
                    is_paper=False,
                    data_origin=data_origin,
                    started_at=now,
                )
                self.db.add(goal)

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return self.get_capital_summary(is_paper=False, data_origin=data_origin)

    def sync_balance(self, payload: BankrollSyncCreate, data_origin: str = "user") -> BankrollHistory:
        """Sincroniza/reconcilia o saldo real informado sem jamais transformar diferença em lucro de trading."""
        now = datetime.now(timezone.utc)
        cap = self.get_capital_summary(is_paper=payload.is_paper, data_origin=data_origin)
        delta = payload.current_actual_balance - cap.cash_balance

        # Localiza meta ativa se houver
        active_goal = (
            self.db.query(TradingGoal)
            .filter(
                TradingGoal.is_paper == payload.is_paper,
                TradingGoal.status == "ACTIVE",
                TradingGoal.data_origin == data_origin,
            )
            .first()
        )

        entry = BankrollHistory(
            balance=payload.current_actual_balance,
            amount=delta,
            entry_type="manual_reconciliation",
            adjustment_type="reconciliation",
            reason=payload.reason or f"Sincronização de saldo: {cap.cash_balance:,} -> {payload.current_actual_balance:,}",
            is_paper=payload.is_paper,
            trading_goal_id=active_goal.id if active_goal else None,
            data_origin=data_origin,
            recorded_at=now,
        )
        self.db.add(entry)

        # Sincroniza a meta ativa com o delta real do usuário
        if active_goal:
            active_goal.current_balance += delta

        self.db.commit()
        self.db.refresh(entry)
        return entry

    def record_adjustment(self, payload: BankrollAdjustmentCreate, data_origin: str = "user") -> BankrollHistory:
        """Registra ajuste externo de moedas sem poluir métricas de lucro de trading."""
        now = datetime.now(timezone.utc)
        cap = self.get_capital_summary(is_paper=payload.is_paper, data_origin=data_origin)
        new_balance = cap.cash_balance + payload.amount

        if new_balance < 0:
            raise ValueError(
                f"Saldo insuficiente ({cap.cash_balance:,} coins) para debitar {abs(payload.amount):,} coins."
            )

        active_goal = (
            self.db.query(TradingGoal)
            .filter(
                TradingGoal.is_paper == payload.is_paper,
                TradingGoal.status == "ACTIVE",
                TradingGoal.data_origin == data_origin,
            )
            .first()
        )

        entry = BankrollHistory(
            balance=new_balance,
            amount=payload.amount,
            entry_type="external_adjustment",
            adjustment_type=payload.adjustment_type,
            reason=payload.reason,
            is_paper=payload.is_paper,
            trading_goal_id=active_goal.id if active_goal else None,
            data_origin=data_origin,
            recorded_at=now,
        )
        self.db.add(entry)

        if active_goal:
            active_goal.current_balance += payload.amount

        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_summary(self, is_paper: bool = False, data_origin: str = "user") -> BankrollSummary:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        cap = self.get_capital_summary(is_paper=is_paper, data_origin=data_origin)
        balance = cap.cash_balance

        trades = (
            self.db.query(Trade)
            .filter(
                Trade.is_paper_trade == is_paper,
                Trade.data_origin == data_origin,
                Trade.status == "sold",
            )
            .all()
        )

        total_profit = sum(t.profit for t in trades if t.profit is not None)

        trades_today = []
        for t in trades:
            if t.sold_at:
                s_at = t.sold_at if t.sold_at.tzinfo is not None else t.sold_at.replace(tzinfo=timezone.utc)
                if s_at >= today_start:
                    trades_today.append(t)
        profit_today = sum(t.profit for t in trades_today if t.profit is not None)

        total_trades = len(trades)
        wins = [t for t in trades if (t.profit or 0) > 0]
        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else None

        rois = [t.roi for t in trades if t.roi is not None]
        avg_roi = (sum(rois) / len(rois) * 100.0) if rois else None

        milestones: list[BankrollMilestone] = []
        next_target = MILESTONE_TARGETS[-1][0]
        found_next = False

        for target, label in MILESTONE_TARGETS:
            achieved = balance >= target
            if not achieved and not found_next:
                next_target = target
                found_next = True

            pct = min(100.0, max(0.0, (balance / float(target)) * 100.0)) if target > 0 else 0.0
            milestones.append(
                BankrollMilestone(
                    target=target,
                    label=label,
                    achieved=achieved,
                    progress_percentage=round(pct, 1),
                )
            )

        return BankrollSummary(
            balance=balance,
            initial_bankroll=settings.INITIAL_BANKROLL if is_paper else balance,
            profit_today=profit_today,
            total_profit=total_profit,
            total_trades=total_trades,
            win_rate=round(win_rate, 1) if win_rate is not None else None,
            average_roi=round(avg_roi, 1) if avg_roi is not None else None,
            next_target=next_target,
            milestones=milestones,
            is_paper=is_paper,
        )
