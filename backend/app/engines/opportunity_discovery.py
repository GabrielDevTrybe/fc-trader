from datetime import datetime, timedelta, timezone
from typing import Sequence
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import PlayerCard, PriceObservation, MarketOpportunity
from app.engines.market_price import MarketPriceEngine, PriceDataPoint
from app.engines.liquidity import LiquidityAnalyzer
from app.engines.trading import TradingEngine
from app.engines.opportunity_score import OpportunityScoreEngine


class OpportunityDiscoveryEngine:
    """Motor de Descoberta de Oportunidades (Discovery Engine).

    Preparado para a Fase 3:
    Analisa universos dinâmicos de CardVersions no catálogo, sem acoplamento a jogadores fixos,
    executando a cadeia determinística:
      Price Observations
            ↓
      MarketPriceEngine
            ↓
      LiquidityAnalyzer
            ↓
      TradingEngine
            ↓
      OpportunityScoreEngine
            ↓
      MarketOpportunity (Persistida e ranqueada)
    """

    def __init__(self, db: Session) -> None:
        self.db = db
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

    def discover_opportunities_for_universe(
        self,
        cards: Sequence[PlayerCard],
        platform: str = "console",
        current_bankroll: int = 5000,
        data_origin: str = "user",
    ) -> list[MarketOpportunity]:
        """Varre um universo arbitrário de CardVersions e retorna oportunidades viáveis detectadas."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=48)
        discovered: list[MarketOpportunity] = []

        for card in cards:
            if not card.is_active:
                continue

            observations = (
                self.db.query(PriceObservation)
                .filter(
                    PriceObservation.card_id == card.id,
                    PriceObservation.platform == platform,
                    PriceObservation.data_origin == data_origin,
                    PriceObservation.observed_at >= cutoff,
                )
                .order_by(PriceObservation.observed_at.desc())
                .limit(50)
                .all()
            )

            if len(observations) < self.price_engine.min_samples:
                continue

            points = [
                PriceDataPoint(
                    price=o.price,
                    observed_at=o.observed_at,
                    observation_type=o.observation_type,
                )
                for o in observations
            ]

            market_stats = self.price_engine.calculate_fair_price(points, reference_time=now)
            liquidity = self.liquidity_analyzer.analyze(points, reference_time=now)

            # Usa o preço mais recente de compra imediata ou lance como observed_price
            latest_obs = observations[0]
            decision = self.trading_engine.evaluate(
                observed_price=latest_obs.price,
                market_stats=market_stats,
                liquidity=liquidity,
                bankroll=current_bankroll,
            )

            if decision.is_opportunity and decision.market_price is not None:
                score_res = self.score_engine.calculate(
                    expected_roi=decision.expected_roi,
                    expected_profit=decision.expected_profit,
                    buy_price=latest_obs.price,
                    liquidity_score=liquidity.score,
                    confidence=decision.confidence,
                    bankroll=current_bankroll,
                    age_minutes=0.0,
                )

                opp = (
                    self.db.query(MarketOpportunity)
                    .filter(
                        MarketOpportunity.card_id == card.id,
                        MarketOpportunity.platform == platform,
                        MarketOpportunity.data_origin == data_origin,
                    )
                    .first()
                )
                if not opp:
                    opp = MarketOpportunity(
                        card_id=card.id,
                        player_id=card.player_id,
                        platform=platform,
                        data_origin=data_origin,
                    )
                    self.db.add(opp)

                opp.observed_price = latest_obs.price
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

                discovered.append(opp)

        if discovered:
            self.db.commit()
            discovered.sort(key=lambda o: o.opportunity_score, reverse=True)

        return discovered
