from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.entities import TradingGoal, Trade, BankrollHistory
from app.schemas.schemas import TradingGoalCreate, TradingGoalRead


class GoalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_goal(self, payload: TradingGoalCreate, current_total_equity: int, data_origin: str = "user") -> TradingGoal:
        # 1. Verifica se já existe meta ACTIVE para a modalidade (REAL ou PAPER) e data_origin
        active = (
            self.db.query(TradingGoal)
            .filter(
                TradingGoal.is_paper == payload.is_paper,
                TradingGoal.status == "ACTIVE",
                TradingGoal.data_origin == data_origin,
            )
            .first()
        )
        if active:
            mode_str = "Paper Trading" if payload.is_paper else "Banca Real"
            raise ValueError(
                f"Já existe uma meta ativa ({active.starting_balance:,} -> {active.target_balance:,} coins) "
                f"em {mode_str}. Encerre ou conclua a meta atual antes de iniciar um novo ciclo."
            )

        starting = payload.starting_balance if payload.starting_balance is not None else current_total_equity
        if payload.target_balance <= starting:
            raise ValueError(
                f"O alvo ({payload.target_balance:,} coins) deve ser estritamente maior que o saldo inicial ({starting:,} coins)."
            )

        now = datetime.now(timezone.utc)
        goal = TradingGoal(
            starting_balance=starting,
            target_balance=payload.target_balance,
            current_balance=starting,
            status="ACTIVE",
            is_paper=payload.is_paper,
            data_origin=data_origin,
            started_at=now,
        )
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def get_active_goal(self, is_paper: bool = False, data_origin: str = "user") -> TradingGoal | None:
        goal = (
            self.db.query(TradingGoal)
            .filter(
                TradingGoal.is_paper == is_paper,
                TradingGoal.status == "ACTIVE",
                TradingGoal.data_origin == data_origin,
            )
            .first()
        )
        if goal:
            self._sync_goal_balance(goal)
        return goal

    def get_goal_read(self, goal: TradingGoal) -> TradingGoalRead:
        trades = (
            self.db.query(Trade)
            .filter(
                Trade.trading_goal_id == goal.id,
                Trade.data_origin == goal.data_origin,
            )
            .all()
        )
        sold_trades = [t for t in trades if t.status == "sold"]
        profit_in_goal = sum(t.profit for t in sold_trades if t.profit is not None)
        total_trades = len(sold_trades)
        wins = [t for t in sold_trades if (t.profit or 0) > 0]
        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else None

        target_delta = goal.target_balance - goal.starting_balance
        achieved_delta = goal.current_balance - goal.starting_balance
        progress_pct = 0.0
        if target_delta > 0:
            progress_pct = min(100.0, max(0.0, (achieved_delta / float(target_delta)) * 100.0))

        return TradingGoalRead(
            id=goal.id,
            starting_balance=goal.starting_balance,
            target_balance=goal.target_balance,
            current_balance=goal.current_balance,
            status=goal.status,
            is_paper=goal.is_paper,
            data_origin=goal.data_origin,
            started_at=goal.started_at,
            completed_at=goal.completed_at,
            closed_at=goal.closed_at,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
            progress_percentage=round(progress_pct, 1),
            trades_count=len(trades),
            profit_in_goal=profit_in_goal,
            win_rate=round(win_rate, 1) if win_rate is not None else None,
        )

    def list_goals(self, is_paper: bool | None = None, data_origin: str = "user") -> list[TradingGoalRead]:
        q = self.db.query(TradingGoal).filter(TradingGoal.data_origin == data_origin)
        if is_paper is not None:
            q = q.filter(TradingGoal.is_paper == is_paper)
        goals = q.order_by(TradingGoal.created_at.desc()).all()
        return [self.get_goal_read(g) for g in goals]

    def complete_goal(self, goal_id: UUID) -> TradingGoal:
        goal = self.db.query(TradingGoal).filter(TradingGoal.id == goal_id).first()
        if not goal:
            raise ValueError(f"Meta com ID {goal_id} não encontrada")
        if goal.status != "ACTIVE":
            raise ValueError(f"Meta não está com status ACTIVE (status atual: {goal.status})")

        self._sync_goal_balance(goal)
        now = datetime.now(timezone.utc)
        goal.status = "COMPLETED"
        goal.completed_at = now
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def close_goal(self, goal_id: UUID) -> TradingGoal:
        goal = self.db.query(TradingGoal).filter(TradingGoal.id == goal_id).first()
        if not goal:
            raise ValueError(f"Meta com ID {goal_id} não encontrada")
        if goal.status != "ACTIVE":
            raise ValueError(f"Meta não está com status ACTIVE (status atual: {goal.status})")

        self._sync_goal_balance(goal)
        now = datetime.now(timezone.utc)
        goal.status = "CLOSED"
        goal.closed_at = now
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def _sync_goal_balance(self, goal: TradingGoal) -> None:
        """Sincroniza current_balance da meta somando lucros de trade e deltas externos/reconciliações."""
        trades = (
            self.db.query(Trade)
            .filter(
                Trade.trading_goal_id == goal.id,
                Trade.status == "sold",
                Trade.data_origin == goal.data_origin,
            )
            .all()
        )
        trading_profit = sum(t.profit for t in trades if t.profit is not None)

        adjustments = (
            self.db.query(BankrollHistory)
            .filter(
                BankrollHistory.trading_goal_id == goal.id,
                BankrollHistory.data_origin == goal.data_origin,
                BankrollHistory.entry_type.in_(["external_adjustment", "manual_reconciliation"]),
            )
            .all()
        )
        external_delta = sum(a.amount for a in adjustments if a.amount is not None)

        goal.current_balance = goal.starting_balance + trading_profit + external_delta
        self.db.commit()
