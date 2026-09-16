from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import Trade, BankrollHistory
from app.schemas.schemas import TradeCreate, TradeClose
from app.engines.tax import calculate_tax, calculate_net_sale, calculate_profit, calculate_roi


class TradeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def open_trade(self, payload: TradeCreate) -> Trade:
        now = datetime.now(timezone.utc)
        bought_at = payload.bought_at or now

        trade = Trade(
            player_id=payload.player_id,
            buy_price=payload.buy_price,
            bought_at=bought_at,
            status="open",
            is_paper_trade=payload.is_paper_trade,
        )
        self.db.add(trade)

        # Se for trade real (não-paper), deduz da banca
        if not payload.is_paper_trade:
            latest_balance = self._get_latest_balance(is_paper=False)
            new_balance = latest_balance - payload.buy_price
            self.db.add(
                BankrollHistory(
                    balance=new_balance,
                    reason=f"Buy trade {trade.id} ({payload.buy_price} coins)",
                    is_paper=False,
                    recorded_at=now,
                )
            )

        self.db.commit()
        self.db.refresh(trade)
        return trade

    def close_trade(self, trade_id: UUID, payload: TradeClose) -> Trade:
        trade = self.db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            raise ValueError(f"Trade com id {trade_id} não encontrado")
        if trade.status != "open":
            raise ValueError(f"Trade {trade_id} já se encontra com status '{trade.status}'")

        now = datetime.now(timezone.utc)
        sold_at = payload.sold_at or now

        tax = calculate_tax(payload.sell_price, settings.TRADING_TAX_RATE)
        net_received = calculate_net_sale(payload.sell_price, settings.TRADING_TAX_RATE)
        profit = calculate_profit(trade.buy_price, payload.sell_price, settings.TRADING_TAX_RATE)
        roi = calculate_roi(trade.buy_price, payload.sell_price, settings.TRADING_TAX_RATE)

        trade.sell_price = payload.sell_price
        trade.tax = tax
        trade.net_received = net_received
        trade.profit = profit
        trade.roi = roi
        trade.sold_at = sold_at
        trade.status = "sold"

        # Se for trade real (não-paper), credita o valor líquido na banca
        if not trade.is_paper_trade:
            latest_balance = self._get_latest_balance(is_paper=False)
            new_balance = latest_balance + net_received
            self.db.add(
                BankrollHistory(
                    balance=new_balance,
                    reason=f"Sold trade {trade.id} (+{net_received} coins, lucro {profit})",
                    is_paper=False,
                    recorded_at=now,
                )
            )

        self.db.commit()
        self.db.refresh(trade)
        return trade

    def list_trades(self, is_paper: bool | None = None, limit: int = 50) -> list[Trade]:
        query = self.db.query(Trade)
        if is_paper is not None:
            query = query.filter(Trade.is_paper_trade == is_paper)
        return query.order_by(Trade.bought_at.desc()).limit(limit).all()

    def _get_latest_balance(self, is_paper: bool) -> int:
        latest = (
            self.db.query(BankrollHistory)
            .filter(BankrollHistory.is_paper == is_paper)
            .order_by(BankrollHistory.recorded_at.desc())
            .first()
        )
        return latest.balance if latest else settings.INITIAL_BANKROLL
