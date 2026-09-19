from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import (
    ActionRecommendation,
    ActionFeedback,
    MarketOpportunity,
    Trade,
    TradingGoal,
    Player,
    PlayerCard,
    PriceObservation,
)
from app.schemas.schemas import (
    ActionFeedbackCreate,
    ActionRecommendationRead,
    CurrentActionResponse,
    TradeCreate,
)
from app.engines.strategy import StrategyEngine
from app.engines.action import ActionEngine
from app.services.bankroll_service import BankrollService
from app.services.trade_service import TradeService


class ActionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.strategy_engine = StrategyEngine()
        self.action_engine = ActionEngine()
        self.bankroll_service = BankrollService(db)
        self.trade_service = TradeService(db)

    def get_current_action(self, is_paper: bool = False, data_origin: str = "user") -> CurrentActionResponse:
        now = datetime.now(timezone.utc)
        cap = self.bankroll_service.get_capital_summary(is_paper=is_paper, data_origin=data_origin)

        # 1. Bloqueio Obrigatório: no modo REAL, se a banca não foi configurada, nenhuma ação pode existir!
        if not is_paper and not cap.is_configured:
            return CurrentActionResponse(
                has_action=False,
                status="BANKROLL_NOT_CONFIGURED",
                title="Configure sua banca",
                message="Defina quantas coins você possui atualmente e qual sua meta para iniciar o trading.",
                suggestion="Informe seu saldo e meta para que o algoritmo recomende operações compatíveis com o seu capital.",
            )

        # 2. Busca contexto de meta ativa
        active_goal = (
            self.db.query(TradingGoal)
            .filter(
                TradingGoal.is_paper == is_paper,
                TradingGoal.status == "ACTIVE",
                TradingGoal.data_origin == data_origin,
            )
            .first()
        )

        # 3. Verifica se já existe recomendação ativa e válida (Snapshot Auditável com TTL)
        active_rec = (
            self.db.query(ActionRecommendation)
            .filter(
                ActionRecommendation.is_paper == is_paper,
                ActionRecommendation.status == "active",
                ActionRecommendation.data_origin == data_origin,
                ActionRecommendation.expires_at > now,
            )
            .order_by(ActionRecommendation.created_at.desc())
            .first()
        )

        if active_rec:
            goal_mismatch = (
                (active_goal and active_rec.trading_goal_id != active_goal.id)
                or (not active_goal and active_rec.trading_goal_id is not None)
            )
            if cap.available_cash < active_rec.max_buy_price or goal_mismatch:
                active_rec.status = "expired"
                self.db.commit()
            else:
                return CurrentActionResponse(
                    has_action=True,
                    status="ACTION_AVAILABLE",
                    action=ActionRecommendationRead.model_validate(active_rec),
                    title="Oportunidade de Ação Imediata",
                    message="Execute a operação conforme as diretrizes quantitativas abaixo.",
                )

        # 4. Mapeia posições abertas por carta e por jogador
        open_trades = (
            self.db.query(Trade)
            .filter(
                Trade.is_paper_trade == is_paper,
                Trade.data_origin == data_origin,
                Trade.status == "open",
            )
            .all()
        )
        open_positions_by_player: dict[UUID, int] = {}
        open_positions_cost_by_player: dict[UUID, int] = {}
        open_positions_by_card: dict[UUID, int] = {}

        for t in open_trades:
            if t.player_id:
                open_positions_by_player[t.player_id] = open_positions_by_player.get(t.player_id, 0) + 1
                open_positions_cost_by_player[t.player_id] = open_positions_cost_by_player.get(t.player_id, 0) + t.buy_price
            if t.card_id:
                open_positions_by_card[t.card_id] = open_positions_by_card.get(t.card_id, 0) + 1

        # 5. Busca oportunidades vigentes não expiradas
        valid_opps = (
            self.db.query(MarketOpportunity)
            .filter(
                MarketOpportunity.data_origin == data_origin,
                (MarketOpportunity.expires_at.is_(None)) | (MarketOpportunity.expires_at > now),
            )
            .all()
        )

        if not valid_opps:
            return CurrentActionResponse(
                has_action=False,
                status="NO_ACTION",
                title="Nenhuma operação segura no momento",
                message="Não há oportunidades vigentes validadas pelos motores de mercado.",
                suggestion="Insira novas observações de preços ou aguarde movimentações no mercado.",
            )

        # 6. Executa o StrategyEngine com a política paramétrica de risco
        decision = self.strategy_engine.evaluate_best_action(
            available_cash=cap.available_cash,
            total_equity=cap.total_equity,
            inventory_cost=cap.inventory_cost,
            valid_opportunities=valid_opps,
            open_positions_by_player=open_positions_by_player,
            open_positions_cost_by_player=open_positions_cost_by_player,
            open_positions_by_card=open_positions_by_card,
            active_goal_target=active_goal.target_balance if active_goal else None,
            active_goal_current=active_goal.current_balance if active_goal else None,
        )

        if not decision.has_action or not decision.opportunity:
            return CurrentActionResponse(
                has_action=False,
                status="NO_ACTION",
                title="Nenhuma operação segura no momento",
                message=decision.reason or "Critérios de gestão de risco ou capital insuficiente.",
                suggestion="Aguarde novas oportunidades de mercado com boa liquidez ou encerre posições abertas.",
            )

        # 7. Conta amostras recentes comprovadas para auditoria factual
        opp = decision.opportunity
        sample_count = (
            self.db.query(PriceObservation)
            .filter(PriceObservation.card_id == opp.card_id)
            .count()
        )

        # 8. Formata via ActionEngine
        presentation = self.action_engine.format_action(
            decision=decision,
            sample_count=sample_count,
            available_cash=cap.available_cash,
        )

        # 9. Persiste Snapshot Auditável com TTL centralizado
        expires_at = now + timedelta(minutes=settings.ACTION_RECOMMENDATION_TTL_MINUTES)
        rec = ActionRecommendation(
            trading_goal_id=active_goal.id if active_goal else None,
            opportunity_id=opp.id,
            card_id=opp.card_id,
            player_id=opp.player_id,
            action_type=presentation.action_type,
            strategy_name=presentation.strategy_name,
            player_name=presentation.player_name,
            player_rating=presentation.player_rating,
            card_version_name=presentation.card_version_name,
            card_club=presentation.card_club,
            card_league=presentation.card_league,
            card_position=presentation.card_position,
            card_platform=presentation.card_platform,
            max_buy_price=presentation.max_buy_price,
            target_sell_price=presentation.target_sell_price,
            recommended_quantity=presentation.recommended_quantity,
            capital_limit=presentation.capital_limit,
            estimated_profit_per_card=presentation.estimated_profit_per_card,
            estimated_total_profit=presentation.estimated_total_profit,
            estimated_roi=presentation.estimated_roi,
            snapshot_market_price=opp.market_price,
            snapshot_observed_price=opp.observed_price,
            snapshot_liquidity_score=opp.liquidity_score,
            snapshot_confidence=opp.confidence,
            snapshot_opportunity_score=opp.opportunity_score,
            snapshot_sample_count=sample_count,
            snapshot_available_cash=cap.available_cash,
            why_explanation=presentation.why_explanation,
            urgency=presentation.urgency,
            status="active",
            is_paper=is_paper,
            data_origin=opp.data_origin or data_origin,
            created_at=now,
            expires_at=expires_at,
        )
        self.db.add(rec)
        self.db.commit()
        self.db.refresh(rec)

        return CurrentActionResponse(
            has_action=True,
            status="ACTION_AVAILABLE",
            action=ActionRecommendationRead.model_validate(rec),
            title="Oportunidade de Ação Imediata",
            message="Execute a operação conforme as diretrizes quantitativas abaixo.",
        )

    def record_feedback(self, payload: ActionFeedbackCreate, data_origin: str = "user") -> ActionFeedback:
        now = datetime.now(timezone.utc)
        rec = (
            self.db.query(ActionRecommendation)
            .filter(ActionRecommendation.id == payload.recommendation_id)
            .first()
        )
        if not rec:
            raise ValueError(f"Recomendação {payload.recommendation_id} não encontrada")

        effective_price = None
        quantity_bought = None

        if payload.action_result.upper() == "BOUGHT":
            rec.status = "executed"
            purchases = payload.purchases

            if not purchases:
                purchases = [{"buy_price": rec.max_buy_price}]

            quantity_bought = len(purchases)
            total_spent = sum(p.buy_price if hasattr(p, "buy_price") else p["buy_price"] for p in purchases)
            effective_price = int(total_spent / quantity_bought)

            for p in purchases:
                p_price = p.buy_price if hasattr(p, "buy_price") else p["buy_price"]
                self.trade_service.open_trade(
                    TradeCreate(
                        card_id=rec.card_id,
                        player_id=rec.player_id,
                        buy_price=p_price,
                        is_paper_trade=rec.is_paper,
                        trading_goal_id=rec.trading_goal_id,
                        action_recommendation_id=rec.id,
                        data_origin=rec.data_origin,
                    )
                )
        else:
            rec.status = "missed"

        feedback = ActionFeedback(
            recommendation_id=rec.id,
            action_result=payload.action_result.upper(),
            effective_price=effective_price,
            quantity_bought=quantity_bought,
            missed_reason=payload.missed_reason,
            notes=payload.notes,
            data_origin=rec.data_origin,
            created_at=now,
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback
