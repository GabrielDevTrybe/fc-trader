from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import BankrollHistory, Trade
from app.schemas.schemas import BankrollSummary, BankrollMilestone

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

    def get_summary(self, is_paper: bool = False) -> BankrollSummary:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. Saldo atual
        latest = (
            self.db.query(BankrollHistory)
            .filter(BankrollHistory.is_paper == is_paper)
            .order_by(BankrollHistory.recorded_at.desc())
            .first()
        )
        balance = latest.balance if latest else settings.INITIAL_BANKROLL

        # 2. Trades fechados
        trades = (
            self.db.query(Trade)
            .filter(
                Trade.is_paper_trade == is_paper,
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

        # 3. Metas / Milestones
        milestones: list[BankrollMilestone] = []
        next_target = MILESTONE_TARGETS[-1][0]
        found_next = False

        for target, label in MILESTONE_TARGETS:
            achieved = balance >= target
            if not achieved and not found_next:
                next_target = target
                found_next = True

            # Progresso percentual para a meta
            pct = min(100.0, max(0.0, (balance / float(target)) * 100.0))
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
            initial_bankroll=settings.INITIAL_BANKROLL,
            profit_today=profit_today,
            total_profit=total_profit,
            total_trades=total_trades,
            win_rate=round(win_rate, 1) if win_rate is not None else None,
            average_roi=round(avg_roi, 1) if avg_roi is not None else None,
            next_target=next_target,
            milestones=milestones,
            is_paper=is_paper,
        )
