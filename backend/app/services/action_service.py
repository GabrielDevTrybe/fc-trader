import math
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import (
    ActionRecommendation,
    ActionFeedback,
    MarketOpportunity,
    MarketSnapshot,
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
from app.engines.opportunity_discovery import OpportunityDiscoveryEngine
from app.services.bankroll_service import BankrollService
from app.services.trade_service import TradeService


class ActionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.strategy_engine = StrategyEngine()
        self.action_engine = ActionEngine()
        self.discovery_engine = OpportunityDiscoveryEngine(db=db)
        self.bankroll_service = BankrollService(db)
        self.trade_service = TradeService(db)

    def get_current_action(
        self,
        is_paper: bool = False,
        data_origin: str = "user",
    ) -> CurrentActionResponse:
        """Consulta puramente READ-ONLY da recomendação atual ativa.

        GET deve ser consulta pura:
        - Retorna recomendação ativa válida existente em cache/banco.
        - Retorna estado NO ACTION / expirado correspondente.
        - NÃO executa OpportunityDiscovery.
        - NÃO cria ActionRecommendation.
        - NÃO realiza commit de nova recomendação ou mutação de estado.
        """
        now = datetime.now(timezone.utc)
        cap = self.bankroll_service.get_capital_summary(is_paper=is_paper, data_origin=data_origin)

        # 1. Bloqueio Obrigatório: no modo REAL, se a banca não foi configurada, nenhuma ação pode existir
        if not is_paper and not cap.is_configured:
            return CurrentActionResponse(
                has_action=False,
                status="BANKROLL_NOT_CONFIGURED",
                no_action_reason_code="BANKROLL_NOT_CONFIGURED",
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

        # 3. Busca recomendação ativa existente no banco
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
            if cap.available_cash >= active_rec.max_buy_price and not goal_mismatch:
                return CurrentActionResponse(
                    has_action=True,
                    status="ACTION_AVAILABLE",
                    action=ActionRecommendationRead.model_validate(active_rec),
                    title="Oportunidade de Ação Imediata",
                    message="Execute a operação conforme as diretrizes quantitativas abaixo.",
                )

        # 4. Sem recomendação ativa válida: retorna NO_ACTION estritamente read-only (sem mutações nem commits)
        return self._build_no_action_response(
            available_cash=cap.available_cash,
            total_equity=cap.total_equity,
            inventory_cost=cap.inventory_cost,
        )

    def verify_market(self, is_paper: bool = False, data_origin: str = "user") -> CurrentActionResponse:
        """Executa reanálise explícita e determinística do mercado:

        Market Intelligence -> Discovery -> Strategy -> ActionRecommendation (persistida).
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Executando verificação determinística de mercado (is_paper={is_paper}, data_origin={data_origin})"
        )

        now = datetime.now(timezone.utc)
        cap = self.bankroll_service.get_capital_summary(is_paper=is_paper, data_origin=data_origin)

        # 1. Bloqueio Obrigatório: no modo REAL, se a banca não foi configurada
        if not is_paper and not cap.is_configured:
            return CurrentActionResponse(
                has_action=False,
                status="BANKROLL_NOT_CONFIGURED",
                no_action_reason_code="BANKROLL_NOT_CONFIGURED",
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

        # 3. Busca recomendação ativa anterior para substituição segura
        active_rec = (
            self.db.query(ActionRecommendation)
            .filter(
                ActionRecommendation.is_paper == is_paper,
                ActionRecommendation.status == "active",
                ActionRecommendation.data_origin == data_origin,
            )
            .order_by(ActionRecommendation.created_at.desc())
            .first()
        )

        # 4. Mapeia posições abertas por carta e por atleta
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

        # 5. Executa pipeline de descoberta no catálogo ativo
        active_cards = self.db.query(PlayerCard).filter(PlayerCard.is_active.is_(True)).all()
        valid_opps: list[MarketOpportunity] = []
        if active_cards:
            valid_opps = self.discovery_engine.discover_opportunities_for_universe(
                cards=active_cards,
                platform="console",
                available_cash=cap.available_cash,
                total_equity=cap.total_equity,
                inventory_cost=cap.inventory_cost,
                open_positions_by_player=open_positions_by_player,
                open_positions_by_card=open_positions_by_card,
                data_origin=data_origin,
                reference_time=now,
            )

        # Se não descobriu via catálogo, verifica se existem oportunidades ativas pré-persistidas
        if not valid_opps:
            valid_opps = (
                self.db.query(MarketOpportunity)
                .filter(
                    MarketOpportunity.data_origin == data_origin,
                    (MarketOpportunity.expires_at.is_(None)) | (MarketOpportunity.expires_at > now),
                )
                .all()
            )

        if not valid_opps:
            if active_rec:
                active_rec.status = "expired"
                self.db.commit()
            return self._build_no_action_response(
                available_cash=cap.available_cash,
                total_equity=cap.total_equity,
                inventory_cost=cap.inventory_cost,
                open_positions_by_player=open_positions_by_player,
                open_positions_cost_by_player=open_positions_cost_by_player,
                open_positions_by_card=open_positions_by_card,
            )

        # 6. Executa o StrategyEngine com a política multidimensional de risco
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
            if active_rec:
                active_rec.status = "expired"
                self.db.commit()
            return self._build_no_action_response(
                available_cash=cap.available_cash,
                decision_reason=decision.reason,
                decision_code=decision.no_action_reason_code,
                total_equity=cap.total_equity,
                inventory_cost=cap.inventory_cost,
                open_positions_by_player=open_positions_by_player,
                open_positions_cost_by_player=open_positions_cost_by_player,
                open_positions_by_card=open_positions_by_card,
                valid_opportunities=valid_opps,
            )

        # 7. Conta amostras recentes e calcula a idade dos dados de mercado
        opp = decision.opportunity
        recent_obs = (
            self.db.query(PriceObservation)
            .filter(
                PriceObservation.card_id == opp.card_id,
                PriceObservation.platform == opp.platform,
            )
            .order_by(PriceObservation.observed_at.desc())
            .all()
        )
        sample_count = len(recent_obs)
        market_data_age_seconds: int | None = None
        if recent_obs:
            latest_time = recent_obs[0].observed_at
            if latest_time.tzinfo is None:
                latest_time = latest_time.replace(tzinfo=timezone.utc)
            market_data_age_seconds = max(0, int((now - latest_time).total_seconds()))

        # Busca snapshot correspondente
        snapshot = (
            self.db.query(MarketSnapshot)
            .filter(
                MarketSnapshot.card_id == opp.card_id,
                MarketSnapshot.platform == opp.platform,
            )
            .order_by(MarketSnapshot.calculated_at.desc())
            .first()
        )

        # 8. Formata via ActionEngine
        presentation = self.action_engine.format_action(
            decision=decision,
            sample_count=sample_count,
            available_cash=cap.available_cash,
            market_data_age_seconds=market_data_age_seconds,
            market_snapshot_id=snapshot.id if snapshot else None,
        )

        # 9. Invalida recomendação anterior e persiste a nova
        if active_rec:
            active_rec.status = "expired"

        expires_at = now + timedelta(minutes=settings.ACTION_RECOMMENDATION_TTL_MINUTES)
        rec = ActionRecommendation(
            trading_goal_id=active_goal.id if active_goal else None,
            opportunity_id=opp.id,
            card_id=opp.card_id,
            player_id=opp.player_id,
            market_snapshot_id=snapshot.id if snapshot else None,
            market_data_age_seconds=market_data_age_seconds,
            action_type=presentation.action_type,
            strategy_name=presentation.strategy_name,
            strategy_type=presentation.strategy_type,
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
            profit_at_max_buy=presentation.profit_at_max_buy,
            roi_at_max_buy=presentation.roi_at_max_buy,
            capital_efficiency=presentation.capital_efficiency,
            expected_holding_time_minutes=presentation.expected_holding_time_minutes,
            snapshot_market_price=opp.market_price,
            snapshot_observed_price=presentation.snapshot_observed_price or opp.observed_price,
            snapshot_liquidity_score=opp.liquidity_score,
            snapshot_confidence=opp.confidence,
            snapshot_opportunity_score=opp.opportunity_score,
            snapshot_sample_count=sample_count,
            snapshot_available_cash=cap.available_cash,
            no_action_reason_code=None,
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

    def _build_no_action_response(
        self,
        available_cash: int,
        decision_reason: str | None = None,
        decision_code: str | None = None,
        total_equity: int | None = None,
        inventory_cost: int = 0,
        open_positions_by_player: dict[UUID, int] | None = None,
        open_positions_cost_by_player: dict[UUID, int] | None = None,
        open_positions_by_card: dict[UUID, int] | None = None,
        valid_opportunities: list[MarketOpportunity] | None = None,
    ) -> CurrentActionResponse:
        """Constrói resposta humanamente explicável a partir dos fatos matemáticos de OpportunityDiagnosis."""
        diagnoses = self.discovery_engine.get_latest_diagnoses()
        equity = total_equity if (total_equity is not None and total_equity > 0) else available_cash

        def fmt_c(val: int | None) -> str:
            if val is None:
                return "N/A"
            return f"{val:,}".replace(",", ".")

        # 1. Tratamento específico para Limite de Concentração por Atleta
        if decision_code == "CONCENTRATION_LIMIT_REACHED" or (
            diagnoses and any(d.reason_code == "CONCENTRATION_LIMIT_REACHED" for d in diagnoses)
        ):
            target_equity = equity if equity > 0 else 1
            player_cap = math.floor(target_equity * settings.PLAYER_MAX_CONCENTRATION_PERCENTAGE)
            pos_count_map = open_positions_by_player or {}
            pos_cost_map = open_positions_cost_by_player or {}
            card_count_map = open_positions_by_card or {}

            target_opp = None
            if valid_opportunities:
                for opp in valid_opportunities:
                    card_key = getattr(opp, "card_id", None) or opp.player_id
                    player_key = getattr(opp, "player_id", None) or card_key
                    p_cost = pos_cost_map.get(player_key, 0)
                    rem_cap = max(0, player_cap - p_cost)
                    if (
                        card_count_map.get(card_key, 0) >= settings.MAX_OPEN_POSITIONS_PER_PLAYER
                        or pos_count_map.get(player_key, 0) >= (settings.MAX_OPEN_POSITIONS_PER_PLAYER * 2)
                        or rem_cap < opp.max_buy_price
                    ):
                        target_opp = opp
                        break
                if not target_opp and valid_opportunities:
                    target_opp = valid_opportunities[0]

            target_diag = None
            if diagnoses:
                if target_opp:
                    for d in diagnoses:
                        if d.card_id == target_opp.card_id or (target_opp.player_id and d.player_id == target_opp.player_id):
                            target_diag = d
                            break
                if not target_diag:
                    for d in diagnoses:
                        if d.reason_code == "CONCENTRATION_LIMIT_REACHED":
                            target_diag = d
                            break
                if not target_diag and diagnoses:
                    target_diag = diagnoses[0]

            req_price = (
                (target_opp.max_buy_price if target_opp and target_opp.max_buy_price else None)
                or (target_diag.max_buy_price if target_diag and target_diag.max_buy_price else None)
                or (target_diag.observed_recent_price if target_diag and target_diag.observed_recent_price else None)
                or 0
            )

            p_name = None
            rating = None
            if target_diag and target_diag.player_name:
                p_name = target_diag.player_name
                rating = target_diag.rating
            elif target_opp and getattr(target_opp, "player", None) and target_opp.player:
                p_name = target_opp.player.name
                rating = target_opp.card.rating if getattr(target_opp, "card", None) else None
            elif target_opp and target_opp.player_id and self.db:
                player_ent = self.db.query(Player).filter(Player.id == target_opp.player_id).first()
                if player_ent:
                    p_name = player_ent.name
                    rating = player_ent.rating

            player_key = (
                (target_opp.player_id if target_opp else None)
                or (target_diag.player_id if target_diag else None)
                or (target_opp.card_id if target_opp else None)
                or (target_diag.card_id if target_diag else None)
            )
            card_key = (
                (target_opp.card_id if target_opp else None)
                or (target_diag.card_id if target_diag else None)
            )

            player_positions = pos_count_map.get(player_key, 0) if player_key else 0
            card_positions = card_count_map.get(card_key, 0) if card_key else 0
            player_cost = pos_cost_map.get(player_key, 0) if player_key else 0
            total_open_positions = sum(pos_count_map.values()) if pos_count_map else (
                sum(card_count_map.values()) if card_count_map else 0
            )

            has_existing_positions = (
                player_positions > 0
                or card_positions > 0
                or player_cost > 0
                or total_open_positions > 0
                or inventory_cost > 0
            )
            unit_price_exceeds = (req_price > player_cap)

            if not has_existing_positions and unit_price_exceeds:
                # Cenário 2: Sem posições abertas e preço unitário da oportunidade excede sozinho o limite permitido
                equity_pct = (req_price / target_equity) * 100
                buy_str = fmt_c(req_price)
                pct_str = f"{equity_pct:.1f}%".replace(".", ",")
                max_pct_str = f"{settings.PLAYER_MAX_CONCENTRATION_PERCENTAGE:.0%}"

                return CurrentActionResponse(
                    has_action=False,
                    status="NO_ACTION",
                    no_action_reason_code="CONCENTRATION_LIMIT_REACHED",
                    title="Limite de concentração por atleta atingido",
                    message=(
                        f"Esta oportunidade exige {buy_str} coins, cerca de {pct_str} da sua banca atual. "
                        f"A política de risco permite no máximo {max_pct_str} da equity por jogador."
                    ),
                    suggestion="Procure uma oportunidade mais barata compatível com sua banca ou aumente a sua banca.",
                )
            else:
                # Cenário 1: Já existem posições daquele jogador/ativo ocupando o limite
                p_desc = f"{p_name} ({rating})" if p_name and rating else (p_name or "este atleta")
                return CurrentActionResponse(
                    has_action=False,
                    status="NO_ACTION",
                    no_action_reason_code="CONCENTRATION_LIMIT_REACHED",
                    title="Limite de concentração por atleta atingido",
                    message=(
                        f"Limite máximo de concentração para {p_desc} atingido conforme política de risco."
                        if p_name
                        else "Limite máximo de estoque ou concentração por atleta atingido conforme política de risco."
                    ),
                    suggestion="Aguarde a venda de cartas em aberto para liberar margem de exposição.",
                )

        # 2. Tratamento específico para Limite Global de Estoque do Portfólio
        if decision_code == "INVENTORY_LIMIT_REACHED" or (
            diagnoses and any(d.reason_code == "INVENTORY_LIMIT_REACHED" for d in diagnoses)
        ):
            return CurrentActionResponse(
                has_action=False,
                status="NO_ACTION",
                no_action_reason_code="INVENTORY_LIMIT_REACHED",
                title="Limite de estoque do portfólio atingido",
                message=decision_reason or "Limite máximo de estoque do portfólio atingido conforme política de risco.",
                suggestion="Aguarde a venda de cartas em aberto para liberar margem de exposição.",
            )

        if diagnoses:
            # Seleciona o diagnóstico mais relevante (prioriza cartas com cotações e maior amostragem/confiança)
            sorted_diags = sorted(
                diagnoses,
                key=lambda d: (
                    d.reason_code == "INSUFFICIENT_MARGIN",
                    d.sample_count > 0,
                    d.confidence_score,
                    d.sample_count,
                    d.observed_recent_price is not None,
                ),
                reverse=True,
            )
            diag = sorted_diags[0]

            p_desc = f"{diag.player_name} ({diag.rating})" if diag.player_name else "esta carta"

            if diag.reason_code == "INSUFFICIENT_MARGIN":
                min_str = fmt_c(diag.observed_min_price)
                rec_str = fmt_c(diag.observed_recent_price)
                mkt_str = fmt_c(diag.estimated_market_price)
                buy_str = fmt_c(diag.max_buy_price)
                tax_str = fmt_c(diag.estimated_tax)

                return CurrentActionResponse(
                    has_action=False,
                    status="NO_ACTION",
                    no_action_reason_code="INSUFFICIENT_MARGIN",
                    title=f"Nenhuma compra recomendada para {p_desc}",
                    message=(
                        f"Preço justo estimado em {mkt_str} coins com base em {diag.sample_count} observações. "
                        f"Com os preços observados no mercado (mínimo: {min_str} coins, recente: {rec_str} coins), "
                        f"o teto seguro de compra é de {buy_str} coins. "
                        f"Não há margem segura de lucro após a taxa de 5% da EA ({tax_str} coins)."
                    ),
                    suggestion=f"Aguarde uma cotação abaixo de {buy_str} coins ou registre novas observações de mercado.",
                )

            if diag.reason_code == "INSUFFICIENT_OBSERVATIONS":
                return CurrentActionResponse(
                    has_action=False,
                    status="NO_ACTION",
                    no_action_reason_code="INSUFFICIENT_OBSERVATIONS",
                    title=f"Amostragem insuficiente para {diag.player_name or 'catálogo'}",
                    message=(
                        f"São necessárias pelo menos {settings.MARKET_PRICE_MIN_SAMPLES} observações recentes para estimar "
                        f"o preço justo com rigor estatístico. Atualmente existem {diag.sample_count}."
                    ),
                    suggestion="Insira novas observações de mercado via Verificação Rápida ou CSV para viabilizar a análise.",
                )

            if diag.reason_code == "INSUFFICIENT_CONFIDENCE":
                return CurrentActionResponse(
                    has_action=False,
                    status="NO_ACTION",
                    no_action_reason_code="INSUFFICIENT_CONFIDENCE",
                    title=f"Confiança estatística insuficiente para {diag.player_name or 'esta carta'}",
                    message=(
                        f"O nível de confiança ({diag.confidence_score:.0%}) está abaixo do limiar "
                        f"mínimo de segurança ({settings.MINIMUM_CONFIDENCE_FOR_ACTION:.0%}) devido à dispersão de preços ou antiguidade dos dados."
                    ),
                    suggestion="Registre novas observações recentes para elevar a confiabilidade estatística.",
                )

            if diag.reason_code == "STALE_DATA":
                return CurrentActionResponse(
                    has_action=False,
                    status="NO_ACTION",
                    no_action_reason_code="STALE_DATA",
                    title="Dados de mercado desatualizados",
                    message=f"As observações de preço para {diag.player_name or 'o catálogo'} são históricas e expiraram.",
                    suggestion="Atualize as cotações com preços recentes para reativar a recomendação de operações.",
                )

            if diag.reason_code == "CAPITAL_INSUFFICIENT" or decision_code == "CAPITAL_EXCEEDED":
                buy_str = f"{diag.max_buy_price:,}" if diag.max_buy_price else "necessário"
                return CurrentActionResponse(
                    has_action=False,
                    status="NO_ACTION",
                    no_action_reason_code="CAPITAL_EXCEEDED",
                    title="Capital livre insuficiente",
                    message=f"O capital necessário ({buy_str} coins) excede o saldo livre disponível na banca ({available_cash:,} coins).",
                    suggestion="Aguarde oportunidades de menor valor ou libere saldo encerrando posições abertas.",
                )

        # Fallback genérico quando não há diagnósticos específicos
        return CurrentActionResponse(
            has_action=False,
            status="NO_ACTION",
            no_action_reason_code=decision_code or "NO_PROFITABLE_OPPORTUNITY",
            title="Nenhuma operação segura no momento",
            message=decision_reason or "Não há oportunidades vigentes validadas pelos motores de mercado.",
            suggestion="Insira novas observações de preços ou aguarde novas movimentações.",
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
