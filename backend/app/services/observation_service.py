from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import (
    Player,
    PlayerCard,
    CardExternalId,
    PriceObservation,
    MarketOpportunity,
    BankrollHistory,
)
from app.schemas.schemas import (
    ObservationBatchItem,
    ObservationBatchResponse,
    OpportunityAnalysis,
)
from app.engines.market_price import MarketPriceEngine, PriceDataPoint
from app.engines.liquidity import LiquidityAnalyzer
from app.engines.trading import TradingEngine
from app.engines.opportunity_score import OpportunityScoreEngine
from app.alerts.dashboard import DashboardAlertProvider
from app.alerts.base import AlertNotification


class ObservationService:
    def __init__(
        self,
        db: Session,
        alert_provider: DashboardAlertProvider | None = None,
    ) -> None:
        self.db = db
        self.alert_provider = alert_provider
        self.price_engine = MarketPriceEngine()
        self.liquidity_analyzer = LiquidityAnalyzer()
        self.trading_engine = TradingEngine(
            tax_rate=settings.TRADING_TAX_RATE,
            minimum_profit=settings.MINIMUM_PROFIT,
            minimum_roi=settings.MINIMUM_ROI,
            maximum_bankroll_percentage=settings.MAX_BANKROLL_PERCENTAGE_PER_TRADE,
            minimum_confidence=settings.MINIMUM_CONFIDENCE,
        )
        self.score_engine = OpportunityScoreEngine()

    def get_current_bankroll(self, data_origin: str = "user") -> int:
        """Obtém o saldo atual de banca ou inicial padrão respeitando o isolamento."""
        latest = (
            self.db.query(BankrollHistory)
            .filter(
                BankrollHistory.is_paper.is_(False),
                BankrollHistory.data_origin == data_origin,
            )
            .order_by(BankrollHistory.recorded_at.desc())
            .first()
        )
        return latest.balance if latest else settings.INITIAL_BANKROLL

    def process_batch(self, items: list[ObservationBatchItem]) -> ObservationBatchResponse:
        now = datetime.now(timezone.utc)
        analyses: list[OpportunityAnalysis] = []

        for item in items:
            obs_time = item.observed_at or now
            if obs_time.tzinfo is None:
                obs_time = obs_time.replace(tzinfo=timezone.utc)

            clean_name = item.player.strip()
            current_bankroll = self.get_current_bankroll(data_origin=item.data_origin)

            # 1. Localiza ou cadastra o Jogador (Atleta humano)
            player = (
                self.db.query(Player)
                .filter(Player.name.ilike(clean_name))
                .first()
            )
            if not player:
                player = Player(
                    name=clean_name,
                    nation=item.nation,
                    rating=item.rating,
                    position=item.position,
                    rarity=item.rarity,
                    league=item.league,
                    club=item.club,
                    data_origin=item.data_origin,
                )
                self.db.add(player)
                self.db.flush()

            # 2. Resolução Canônica da CardVersion (PlayerCard)
            card = None
            if item.card_id:
                card = self.db.query(PlayerCard).filter(PlayerCard.id == item.card_id).first()
            elif item.external_card_id:
                ext = (
                    self.db.query(CardExternalId)
                    .filter(
                        CardExternalId.provider == item.provider,
                        CardExternalId.external_id == item.external_card_id,
                    )
                    .first()
                )
                if ext:
                    card = ext.card

            if not card:
                # Busca por identidade completa de versão: player_id + rating + clube + raridade
                query = self.db.query(PlayerCard).filter(
                    PlayerCard.player_id == player.id,
                    PlayerCard.rating == item.rating,
                )
                if item.club:
                    query = query.filter(PlayerCard.club.ilike(item.club.strip()))
                if item.rarity:
                    query = query.filter(PlayerCard.rarity.ilike(item.rarity.strip()))

                card = query.first()

            if not card:
                card = PlayerCard(
                    player_id=player.id,
                    game_version="FC27",
                    rating=item.rating,
                    position=item.position or player.position,
                    rarity=item.rarity or player.rarity or "Gold",
                    club=item.club or player.club,
                    league=item.league or player.league,
                    nation=item.nation or player.nation,
                    data_origin=item.data_origin,
                )
                self.db.add(card)
                self.db.flush()

                # Se fornecido ID externo, registra na tabela especializada de provedores
                if item.external_card_id:
                    self.db.add(
                        CardExternalId(
                            card_id=card.id,
                            provider=item.provider,
                            external_id=item.external_card_id,
                        )
                    )
                    self.db.flush()

            # 3. Registra a observação vinculada à carta e à plataforma específica
            obs = PriceObservation(
                card_id=card.id,
                player_id=player.id,
                price=item.price,
                observation_type=item.type,
                platform=item.platform or "console",
                source=item.provider or "manual",
                data_origin=item.data_origin,
                observed_at=obs_time,
            )
            self.db.add(obs)
            self.db.flush()

            # 4. Carrega histórico de preços estritamente desta CardVersion nesta plataforma
            cutoff = now - timedelta(hours=48)
            existing_obs = (
                self.db.query(PriceObservation)
                .filter(
                    PriceObservation.card_id == card.id,
                    PriceObservation.platform == (item.platform or "console"),
                    PriceObservation.observed_at >= cutoff,
                )
                .order_by(PriceObservation.observed_at.desc())
                .limit(50)
                .all()
            )

            points = [
                PriceDataPoint(
                    price=o.price,
                    observed_at=o.observed_at,
                    observation_type=o.observation_type,
                )
                for o in existing_obs
            ]

            # 5. Executa Motores Quantitativos Determinísticos
            market_stats = self.price_engine.calculate_fair_price(points, reference_time=now)
            liquidity = self.liquidity_analyzer.analyze(points, reference_time=now)

            decision = self.trading_engine.evaluate(
                observed_price=item.price,
                market_stats=market_stats,
                liquidity=liquidity,
                bankroll=current_bankroll,
            )

            score_res = self.score_engine.calculate(
                expected_roi=decision.expected_roi,
                expected_profit=decision.expected_profit,
                buy_price=item.price,
                liquidity_score=liquidity.score,
                confidence=decision.confidence,
                bankroll=current_bankroll,
                age_minutes=0.0,
            )

            # 6. Atualiza ou cria Oportunidade vinculada à CardVersion e Plataforma
            if decision.is_opportunity and decision.market_price is not None:
                opp = (
                    self.db.query(MarketOpportunity)
                    .filter(
                        MarketOpportunity.card_id == card.id,
                        MarketOpportunity.platform == (item.platform or "console"),
                    )
                    .first()
                )
                if not opp:
                    opp = MarketOpportunity(
                        card_id=card.id,
                        player_id=player.id,
                        platform=item.platform or "console",
                        data_origin=item.data_origin,
                    )
                    self.db.add(opp)

                opp.observed_price = item.price
                opp.market_price = decision.market_price
                opp.max_buy_price = decision.max_buy_price
                opp.target_sell_price = decision.target_sell_price
                opp.estimated_profit = decision.expected_profit
                opp.roi = decision.expected_roi
                opp.confidence = decision.confidence
                opp.liquidity_score = liquidity.score
                opp.opportunity_score = score_res.score
                opp.detected_at = now
                opp.expires_at = now + timedelta(minutes=30)
                opp.data_origin = item.data_origin

                # Alerta se houver provider configurado
                if self.alert_provider and opp.opportunity_score >= 60.0:
                    self.alert_provider.notify(
                        AlertNotification(
                            type="OPPORTUNITY_DETECTED",
                            title=f"Oportunidade: {player.name} ({card.rating}) - {card.club or ''}",
                            message=f"Margem de lucro estimada em +{decision.expected_profit:,} coins (Score: {opp.opportunity_score:.1f})",
                            data={
                                "card_id": str(card.id),
                                "player": player.name,
                                "rating": card.rating,
                                "version": card.rarity,
                                "club": card.club,
                                "platform": opp.platform,
                                "buy": item.price,
                                "market": decision.market_price,
                                "profit": decision.expected_profit,
                            },
                        )
                    )

            analyses.append(
                OpportunityAnalysis(
                    card_id=card.id,
                    player_id=player.id,
                    player_name=player.name,
                    rating=card.rating,
                    version_name=card.rarity,
                    club=card.club,
                    platform=item.platform or "console",
                    observed_price=item.price,
                    market_price=decision.market_price,
                    max_buy_price=decision.max_buy_price,
                    target_sell_price=decision.target_sell_price,
                    expected_profit=decision.expected_profit,
                    expected_roi=decision.expected_roi,
                    confidence=decision.confidence,
                    liquidity_score=liquidity.score,
                    opportunity_score=score_res.score,
                    recommendation=decision.recommendation,
                    reason=decision.reason,
                )
            )

        self.db.commit()
        return ObservationBatchResponse(processed_count=len(analyses), analyses=analyses)
