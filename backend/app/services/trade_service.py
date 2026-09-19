from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import Trade, BankrollHistory, TradingGoal, PlayerCard, Player
from app.schemas.schemas import TradeCreate, TradeClose
from app.engines.tax import calculate_tax, calculate_net_sale, calculate_profit, calculate_roi


class TradeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def open_trade(self, payload: TradeCreate) -> Trade:
        now = datetime.now(timezone.utc)
        bought_at = payload.bought_at or now

        # 1. Resolução canônica de card_id e player_id
        card_id = payload.card_id
        player_id = payload.player_id

        if card_id:
            card = self.db.query(PlayerCard).filter(PlayerCard.id == card_id).first()
            if not card:
                raise ValueError(f"CardVersion com id {card_id} não encontrada")
            player_id = card.player_id
        elif player_id:
            # Compatibilidade: se enviado apenas player_id, busca ou cria uma CardVersion padrão
            card = self.db.query(PlayerCard).filter(PlayerCard.player_id == player_id).first()
            if not card:
                player = self.db.query(Player).filter(Player.id == player_id).first()
                if not player:
                    raise ValueError(f"Jogador com id {player_id} não encontrado")
                card = PlayerCard(
                    player_id=player.id,
                    game_version="FC27",
                    rating=player.rating or 80,
                    position=player.position,
                    rarity=player.rarity or "Gold",
                    club=player.club,
                    league=player.league,
                    nation=player.nation,
                    data_origin=payload.data_origin,
                )
                self.db.add(card)
                self.db.flush()
            card_id = card.id
        else:
            raise ValueError("É obrigatório informar card_id ou player_id para abrir um trade")

        # 2. Se não fornecido trading_goal_id, busca a meta ativa para este modo e data_origin
        goal_id = payload.trading_goal_id
        if not goal_id:
            active_goal = (
                self.db.query(TradingGoal)
                .filter(
                    TradingGoal.is_paper == payload.is_paper_trade,
                    TradingGoal.status == "ACTIVE",
                    TradingGoal.data_origin == payload.data_origin,
                )
                .first()
            )
            if active_goal:
                goal_id = active_goal.id

        trade = Trade(
            card_id=card_id,
            player_id=player_id,
            buy_price=payload.buy_price,
            bought_at=bought_at,
            status="open",
            is_paper_trade=payload.is_paper_trade,
            trading_goal_id=goal_id,
            action_recommendation_id=payload.action_recommendation_id,
            data_origin=payload.data_origin,
        )
        self.db.add(trade)

        # 3. Deduz o custo da carta do saldo de caixa (cash_balance)
        latest_balance = self._get_latest_balance(is_paper=payload.is_paper_trade, data_origin=payload.data_origin)
        new_balance = latest_balance - payload.buy_price
        self.db.add(
            BankrollHistory(
                balance=new_balance,
                amount=-payload.buy_price,
                entry_type="trade",
                reason=f"Compra trade {str(card_id)[:8]} ({payload.buy_price:,} coins)",
                is_paper=payload.is_paper_trade,
                trading_goal_id=goal_id,
                data_origin=payload.data_origin,
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

        # Credita o valor líquido recebido no saldo de caixa
        latest_balance = self._get_latest_balance(is_paper=trade.is_paper_trade, data_origin=trade.data_origin)
        new_balance = latest_balance + net_received
        self.db.add(
            BankrollHistory(
                balance=new_balance,
                amount=+net_received,
                entry_type="trade",
                reason=f"Venda trade {str(trade.card_id)[:8]} (+{net_received:,} coins, lucro {profit:+,})",
                is_paper=trade.is_paper_trade,
                trading_goal_id=trade.trading_goal_id,
                data_origin=trade.data_origin,
                recorded_at=now,
            )
        )

        # Se houver meta vinculada, atualiza o saldo da meta
        if trade.trading_goal_id:
            goal = (
                self.db.query(TradingGoal)
                .filter(
                    TradingGoal.id == trade.trading_goal_id,
                    TradingGoal.data_origin == trade.data_origin,
                )
                .first()
            )
            if goal:
                goal.current_balance += profit

        self.db.commit()
        self.db.refresh(trade)
        return trade

    def list_trades(
        self,
        is_paper: bool | None = None,
        goal_id: UUID | None = None,
        status: str | None = None,
        data_origin: str = "user",
        limit: int = 50,
    ) -> list[Trade]:
        query = self.db.query(Trade).filter(Trade.data_origin == data_origin)
        if is_paper is not None:
            query = query.filter(Trade.is_paper_trade == is_paper)
        if goal_id is not None:
            query = query.filter(Trade.trading_goal_id == goal_id)
        if status is not None:
            query = query.filter(Trade.status == status)
        return query.order_by(Trade.bought_at.desc()).limit(limit).all()

    def _get_latest_balance(self, is_paper: bool, data_origin: str = "user") -> int:
        latest = (
            self.db.query(BankrollHistory)
            .filter(
                BankrollHistory.is_paper == is_paper,
                BankrollHistory.data_origin == data_origin,
            )
            .order_by(BankrollHistory.recorded_at.desc())
            .first()
        )
        if latest:
            return latest.balance
        return settings.INITIAL_BANKROLL if is_paper else 0
