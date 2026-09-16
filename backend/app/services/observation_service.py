from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import Player, PriceObservation, MarketOpportunity, BankrollHistory
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

    def get_current_bankroll(self) -> int:
        """Obtém o saldo atual de banca ou inicial padrão."""
        latest = (
            self.db.query(BankrollHistory)
            .filter(BankrollHistory.is_paper.is_(False))
            .order_by(BankrollHistory.recorded_at.desc())
            .first()
        )
        return latest.balance if latest else settings.INITIAL_BANKROLL

    def process_batch(self, items: list[ObservationBatchItem]) -> ObservationBatchResponse:
        now = datetime.now(timezone.utc)
        current_bankroll = self.get_current_bankroll()
        analyses: list[OpportunityAnalysis] = []

        # Cache local de jogadores durante o lote para evitar roundtrips redundantes
        player_cache: dict[tuple[str, int], Player] = {}
        # Histórico recente em memória por jogador
        obs_points_by_player: dict[tuple[str, int], list[PriceDataPoint]] = {}

        for item in items:
            obs_time = item.observed_at or now
            if obs_time.tzinfo is None:
                obs_time = obs_time.replace(tzinfo=timezone.utc)

            clean_name = item.player.strip()
            cache_key = (clean_name.lower(), item.rating)

            if cache_key not in player_cache:
                player = (
                    self.db.query(Player)
                    .filter(
                        Player.name.ilike(clean_name),
                        Player.rating == item.rating,
                    )
                    .first()
                )
                if not player:
                    player = Player(
                        name=clean_name,
                        rating=item.rating,
                        position=item.position,
                        rarity=item.rarity,
                        league=item.league,
                        club=item.club,
                        nation=item.nation,
                    )
                    self.db.add(player)
                    self.db.flush()
                player_cache[cache_key] = player

                # Carrega pontos recentes do banco uma única vez para este jogador
                cutoff = now - timedelta(hours=48)
                existing_obs = (
                    self.db.query(PriceObservation)
                    .filter(
                        PriceObservation.player_id == player.id,
                        PriceObservation.observed_at >= cutoff,
                    )
                    .order_by(PriceObservation.observed_at.desc())
                    .limit(50)
                    .all()
                )
                obs_points_by_player[cache_key] = [
                    PriceDataPoint(
                        price=o.price,
                        observed_at=o.observed_at,
                        observation_type=o.observation_type,
                    )
                    for o in existing_obs
                ]

            player = player_cache[cache_key]

            # Armazena observação no banco
            obs = PriceObservation(
                player_id=player.id,
                price=item.price,
                observation_type=item.type,
                source="manual",
                observed_at=obs_time,
            )
            self.db.add(obs)

            # Adiciona ao histórico em memória para recálculo imediato
            point = PriceDataPoint(
                price=item.price,
                observed_at=obs_time,
                observation_type=item.type,
            )
            obs_points_by_player[cache_key].insert(0, point)

            points = obs_points_by_player[cache_key]

            # Executa Engines
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

            # Se houver preço justo, agenda atualização da oportunidade
            if decision.market_price:
                self.db.query(MarketOpportunity).filter(
                    MarketOpportunity.player_id == player.id
                ).delete()

                opp_record = MarketOpportunity(
                    player_id=player.id,
                    observed_price=item.price,
                    market_price=decision.market_price,
                    max_buy_price=decision.max_buy_price,
                    target_sell_price=decision.target_sell_price,
                    estimated_profit=decision.expected_profit,
                    roi=decision.expected_roi,
                    confidence=decision.confidence,
                    liquidity_score=liquidity.score,
                    opportunity_score=score_res.score,
                    detected_at=now,
                    expires_at=now + timedelta(minutes=45),
                )
                self.db.add(opp_record)

                if decision.is_opportunity and self.alert_provider:
                    self.alert_provider.send_alert(
                        AlertNotification(
                            player_name=player.name,
                            rating=player.rating,
                            observed_price=item.price,
                            market_price=decision.market_price,
                            expected_profit=decision.expected_profit,
                            expected_roi=decision.expected_roi,
                            confidence=decision.confidence,
                            opportunity_score=score_res.score,
                            created_at=now,
                        )
                    )

            analyses.append(
                OpportunityAnalysis(
                    player_id=player.id,
                    player_name=player.name,
                    rating=player.rating,
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
        return ObservationBatchResponse(
            processed_count=len(analyses),
            analyses=analyses,
        )
