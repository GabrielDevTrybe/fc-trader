from datetime import datetime, timedelta, timezone
import math
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import (
    Player,
    PlayerCard,
    CardExternalId,
    PriceObservation,
    MarketOpportunity,
    MarketSnapshot,
    BankrollHistory,
)
from app.schemas.schemas import (
    ObservationBatchItem,
    ObservationBatchResponse,
    OpportunityAnalysis,
)
from app.engines.market_intelligence import MarketIntelligenceEngine, MarketPriceDataPoint
from app.engines.opportunity_discovery import OpportunityDiscoveryEngine
from app.engines.liquidity import LiquidityAnalyzer
from app.providers.csv_provider import CSVMarketDataProvider
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
        self.market_intel = MarketIntelligenceEngine()
        self.discovery_engine = OpportunityDiscoveryEngine(db=db)
        self.liquidity_analyzer = LiquidityAnalyzer()

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

    def process_csv_batch(self, csv_content: str, data_origin: str = "user") -> ObservationBatchResponse:
        """Processa texto CSV em lote convertendo para ObservationBatchItems canônicos."""
        csv_provider = CSVMarketDataProvider()
        raw_items = csv_provider.parse_csv(csv_content, default_data_origin=data_origin)
        batch_items: list[ObservationBatchItem] = []

        for r in raw_items:
            c_uuid = None
            if r.card_id:
                try:
                    c_uuid = UUID(r.card_id)
                except ValueError:
                    c_uuid = None

            batch_items.append(
                ObservationBatchItem(
                    player=r.player_name,
                    rating=r.player_rating,
                    price=r.price,
                    type=r.observation_type,
                    platform=r.platform,
                    position=r.position,
                    rarity=r.rarity,
                    league=r.league,
                    club=r.club,
                    nation=r.nation,
                    card_id=c_uuid,
                    external_card_id=r.external_id,
                    provider=r.provider,
                    data_origin=r.data_origin,
                    observed_at=r.observed_at,
                )
            )

        return self.process_batch(batch_items)

    def process_batch(self, items: list[ObservationBatchItem]) -> ObservationBatchResponse:
        now = datetime.now(timezone.utc)
        analyses: list[OpportunityAnalysis] = []

        for item in items:
            obs_time = item.observed_at or now
            if obs_time.tzinfo is None:
                obs_time = obs_time.replace(tzinfo=timezone.utc)

            clean_name = item.player.strip()
            current_bankroll = self.get_current_bankroll(data_origin=item.data_origin)

            # 1. Localiza ou cadastra o Atleta (Player)
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

                if item.external_card_id:
                    self.db.add(
                        CardExternalId(
                            card_id=card.id,
                            provider=item.provider,
                            external_id=item.external_card_id,
                        )
                    )
                    self.db.flush()

            # 3. Registra a observação preservando a proveniência semântica
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

            # 4. Carrega histórico de preços para computar inteligência estatística
            cutoff = now - timedelta(hours=settings.OBSERVATION_HISTORICAL_HOURS)
            existing_obs = (
                self.db.query(PriceObservation)
                .filter(
                    PriceObservation.card_id == card.id,
                    PriceObservation.platform == (item.platform or "console"),
                    PriceObservation.data_origin == item.data_origin,
                    PriceObservation.observed_at >= cutoff,
                )
                .order_by(PriceObservation.observed_at.desc())
                .limit(50)
                .all()
            )

            data_points = [
                MarketPriceDataPoint(
                    price=o.price,
                    observed_at=o.observed_at,
                    observation_type=o.observation_type,
                    source=o.source,
                    platform=o.platform,
                )
                for o in existing_obs
            ]

            # 5. Executa MarketIntelligenceEngine (com expurgo de outliers IQR e pesos temporais)
            snapshot_res = self.market_intel.compute_snapshot(
                observations=data_points,
                card_id=str(card.id),
                platform=item.platform or "console",
                reference_time=now,
            )

            # Persiste/Atualiza Snapshot Auditável no Banco
            snapshot_entity = MarketSnapshot(
                card_id=card.id,
                platform=item.platform or "console",
                sample_count=snapshot_res.sample_count,
                valid_sample_count=snapshot_res.valid_sample_count,
                min_price=snapshot_res.min_price,
                max_price=snapshot_res.max_price,
                median_price=snapshot_res.median_price,
                p20_price=snapshot_res.p20_price,
                p80_price=snapshot_res.p80_price,
                robust_mean=snapshot_res.robust_mean,
                std_dev=snapshot_res.std_dev,
                dispersion_ratio=snapshot_res.dispersion_ratio,
                estimated_market_price=snapshot_res.estimated_market_price,
                conservative_buy_price=snapshot_res.conservative_buy_price,
                conservative_sell_price=snapshot_res.conservative_sell_price,
                confidence_score=snapshot_res.confidence_score,
                confidence_level=snapshot_res.confidence_level,
                freshness_status=snapshot_res.freshness_status,
                newest_observation_age_seconds=snapshot_res.newest_observation_age_seconds,
                trend=snapshot_res.trend,
                data_quality=snapshot_res.data_quality,
                calculated_at=now,
                expires_at=now + timedelta(minutes=settings.SNAPSHOT_VALIDITY_MINUTES),
                data_origin=item.data_origin,
            )
            self.db.add(snapshot_entity)
            self.db.flush()

            # 6. Avaliação de Oportunidade
            liquidity = self.liquidity_analyzer.analyze(
                [PriceObservation(price=p.price, observed_at=p.observed_at) for p in data_points],
                reference_time=now,
            )

            opp_eval = None
            if snapshot_res.has_sufficient_data and snapshot_res.confidence_score >= settings.MINIMUM_CONFIDENCE_FOR_ACTION:
                opp_eval = self.discovery_engine.evaluate_opportunity(
                    card=card,
                    snapshot=snapshot_res,
                    liquidity_score=liquidity.score,
                    latest_observation_price=item.price,
                    available_cash=current_bankroll,
                    max_allocation_cap=math.floor(current_bankroll * 0.25),
                    snapshot_id=snapshot_entity.id,
                )

            # Atualiza ou cria MarketOpportunity
            if opp_eval:
                opp = (
                    self.db.query(MarketOpportunity)
                    .filter(
                        MarketOpportunity.card_id == card.id,
                        MarketOpportunity.platform == (item.platform or "console"),
                        MarketOpportunity.data_origin == item.data_origin,
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

                opp.observed_price = opp_eval.observed_price
                opp.market_price = opp_eval.estimated_market_price
                opp.max_buy_price = opp_eval.max_buy_price
                opp.target_sell_price = opp_eval.target_sell_price
                opp.estimated_profit = opp_eval.net_profit
                opp.roi = opp_eval.roi
                opp.confidence = opp_eval.confidence_level
                opp.liquidity_score = opp_eval.liquidity_score
                opp.opportunity_score = opp_eval.ranking_score
                opp.strategy_type = opp_eval.strategy_type
                opp.capital_efficiency = opp_eval.capital_efficiency
                opp.expected_holding_time_minutes = opp_eval.expected_holding_time_minutes
                opp.detected_at = now
                opp.expires_at = now + timedelta(minutes=settings.ACTION_RECOMMENDATION_TTL_MINUTES)
                self.db.flush()

                # Notificação se oportunidade de alto impacto
                if self.alert_provider and opp.opportunity_score >= 60.0:
                    self.alert_provider.notify(
                        AlertNotification(
                            type="OPPORTUNITY_DETECTED",
                            title=f"Oportunidade: {player.name} ({card.rating}) - {opp.strategy_type}",
                            message=f"Lucro líquido: +{opp_eval.net_profit:,} coins (Score: {opp.opportunity_score:.1f})",
                            data={
                                "card_id": str(card.id),
                                "player": player.name,
                                "rating": card.rating,
                                "version": card.rarity,
                                "platform": opp.platform,
                                "buy": item.price,
                                "max_buy": opp.max_buy_price,
                                "profit": opp_eval.net_profit,
                            },
                        )
                    )

            # Análise para resposta do batch
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
                    market_price=snapshot_res.estimated_market_price,
                    max_buy_price=opp_eval.max_buy_price if opp_eval else 0,
                    target_sell_price=opp_eval.target_sell_price if opp_eval else 0,
                    expected_profit=opp_eval.net_profit if opp_eval else 0,
                    expected_roi=opp_eval.roi if opp_eval else 0.0,
                    confidence=snapshot_res.confidence_level,
                    liquidity_score=liquidity.score,
                    opportunity_score=opp_eval.ranking_score if opp_eval else 0.0,
                    recommendation="BUY" if opp_eval else "PASS",
                    reason=snapshot_res.reason if not opp_eval else f"Estratégia {opp_eval.strategy_type} viável",
                )
            )

        self.db.commit()
        return ObservationBatchResponse(processed_count=len(analyses), analyses=analyses)
