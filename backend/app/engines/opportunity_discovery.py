from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Sequence
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import PlayerCard, PriceObservation, MarketOpportunity, MarketSnapshot
from app.engines.market_intelligence import MarketIntelligenceEngine, MarketPriceDataPoint, MarketSnapshotResult
from app.engines.liquidity import LiquidityAnalyzer
from app.engines.tax import calculate_tax, calculate_profit, calculate_roi, calculate_max_buy_price


@dataclass(frozen=True)
class DiscoveredOpportunity:
    card_id: UUID
    player_id: UUID | None
    platform: str
    strategy_type: str  # QUICK_FLIP, SWING, INVESTMENT
    estimated_market_price: int
    max_buy_price: int
    target_sell_price: int
    observed_price: int
    gross_profit: int
    ea_tax: int
    net_profit: int
    roi: float
    confidence_score: float
    confidence_level: str
    liquidity_score: int
    capital_efficiency: float
    expected_holding_time_minutes: int | None
    capital_required: int
    recommended_quantity: int
    estimated_total_profit: int
    ranking_score: float
    snapshot_id: UUID | None = None


@dataclass(frozen=True)
class OpportunityDiagnosis:
    card_id: UUID
    player_id: UUID | None
    player_name: str | None
    rating: int | None
    version_name: str | None
    club: str | None
    platform: str
    reason_code: str  # INSUFFICIENT_MARGIN, INSUFFICIENT_OBSERVATIONS, INSUFFICIENT_CONFIDENCE, STALE_DATA, etc.
    sample_count: int
    valid_sample_count: int
    estimated_market_price: int | None
    observed_min_price: int | None
    observed_recent_price: int | None
    max_buy_price: int | None
    conservative_buy_price: int | None
    conservative_sell_price: int | None
    estimated_tax: int | None
    estimated_profit: int | None
    estimated_roi: float | None
    confidence_score: float
    confidence_level: str
    freshness_status: str
    data_quality: str
    liquidity_score: int | None = None
    evaluated_at: datetime | None = None


class OpportunityDiscoveryEngine:
    """Motor determinístico de Descoberta Automática de Oportunidades no Catálogo.

    Varre um universo dinâmico de CardVersions ativas:
    1. Computa inteligência estatística de mercado via MarketIntelligenceEngine.
    2. Rejeita dados insuficientes, expirados ou com confiança inferior ao mínimo.
    3. Aplica critérios por tipo de estratégia (QUICK_FLIP, SWING, INVESTMENT).
    4. Executa cálculo reverso estrito de max_buy via autoridade do TaxEngine:
       max_buy = min(statistical_buy_ceiling, max_buy_by_profit, max_buy_by_roi)
    5. Avalia eficiência de capital (lucro / capital alocado) e holding time (nullable).
    6. Aplica ranking multicritério equilibrado (lucro, ROI, confiança, liquidez e giro).
    7. Registra diagnóstico matemático auditável (OpportunityDiagnosis) de cada análise.
    """

    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        self.market_intel = MarketIntelligenceEngine()
        self.liquidity_analyzer = LiquidityAnalyzer()
        self.latest_diagnoses: list[OpportunityDiagnosis] = []

    def get_latest_diagnoses(self) -> list[OpportunityDiagnosis]:
        return list(self.latest_diagnoses)

    def discover_opportunities_for_universe(
        self,
        cards: Sequence[PlayerCard],
        platform: str = "console",
        available_cash: int = 25000,
        total_equity: int = 25000,
        inventory_cost: int = 0,
        open_positions_by_player: dict[UUID, int] | None = None,
        open_positions_by_card: dict[UUID, int] | None = None,
        data_origin: str = "user",
        reference_time: datetime | None = None,
    ) -> list[MarketOpportunity]:
        """Varre o catálogo de cartas e persiste/atualiza as oportunidades ranqueadas no banco."""
        now = reference_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        self.latest_diagnoses = []
        cutoff = now - timedelta(hours=settings.OBSERVATION_HISTORICAL_HOURS)
        positions_by_player = open_positions_by_player or {}
        positions_by_card = open_positions_by_card or {}

        # Teto de estoque global do portfólio (máx 70% de total_equity)
        max_portfolio_inventory = math.floor(total_equity * settings.PORTFOLIO_MAX_INVENTORY_PERCENTAGE)
        remaining_inventory_capacity = max(0, max_portfolio_inventory - inventory_cost)
        if remaining_inventory_capacity <= 0:
            for card in cards:
                p_name = card.player.name if card.player else None
                self.latest_diagnoses.append(
                    OpportunityDiagnosis(
                        card_id=card.id,
                        player_id=card.player_id,
                        player_name=p_name,
                        rating=card.rating,
                        version_name=card.rarity,
                        club=card.club,
                        platform=platform,
                        reason_code="INVENTORY_LIMIT_REACHED",
                        sample_count=0,
                        valid_sample_count=0,
                        estimated_market_price=None,
                        observed_min_price=None,
                        observed_recent_price=None,
                        max_buy_price=None,
                        conservative_buy_price=None,
                        conservative_sell_price=None,
                        estimated_tax=None,
                        estimated_profit=None,
                        estimated_roi=None,
                        confidence_score=0.0,
                        confidence_level="LOW",
                        freshness_status="HISTORICAL",
                        data_quality="LIMIT_REACHED",
                        liquidity_score=None,
                        evaluated_at=now,
                    )
                )
            return []

        # Teto por jogador/carta (máx 25% de total_equity)
        max_player_cap = math.floor(total_equity * settings.PLAYER_MAX_CONCENTRATION_PERCENTAGE)

        discovered_list: list[DiscoveredOpportunity] = []
        persisted_opps: list[MarketOpportunity] = []

        for card in cards:
            if not card.is_active:
                continue

            p_name = card.player.name if card.player else None

            # Checagem prévia de limites de posições abertas
            if positions_by_card.get(card.id, 0) >= settings.MAX_OPEN_POSITIONS_PER_PLAYER:
                self.latest_diagnoses.append(
                    OpportunityDiagnosis(
                        card_id=card.id,
                        player_id=card.player_id,
                        player_name=p_name,
                        rating=card.rating,
                        version_name=card.rarity,
                        club=card.club,
                        platform=platform,
                        reason_code="CONCENTRATION_LIMIT_REACHED",
                        sample_count=0,
                        valid_sample_count=0,
                        estimated_market_price=None,
                        observed_min_price=None,
                        observed_recent_price=None,
                        max_buy_price=None,
                        conservative_buy_price=None,
                        conservative_sell_price=None,
                        estimated_tax=None,
                        estimated_profit=None,
                        estimated_roi=None,
                        confidence_score=0.0,
                        confidence_level="LOW",
                        freshness_status="HISTORICAL",
                        data_quality="LIMIT_REACHED",
                        liquidity_score=None,
                        evaluated_at=now,
                    )
                )
                continue
            if card.player_id and positions_by_player.get(card.player_id, 0) >= (settings.MAX_OPEN_POSITIONS_PER_PLAYER * 2):
                self.latest_diagnoses.append(
                    OpportunityDiagnosis(
                        card_id=card.id,
                        player_id=card.player_id,
                        player_name=p_name,
                        rating=card.rating,
                        version_name=card.rarity,
                        club=card.club,
                        platform=platform,
                        reason_code="CONCENTRATION_LIMIT_REACHED",
                        sample_count=0,
                        valid_sample_count=0,
                        estimated_market_price=None,
                        observed_min_price=None,
                        observed_recent_price=None,
                        max_buy_price=None,
                        conservative_buy_price=None,
                        conservative_sell_price=None,
                        estimated_tax=None,
                        estimated_profit=None,
                        estimated_roi=None,
                        confidence_score=0.0,
                        confidence_level="LOW",
                        freshness_status="HISTORICAL",
                        data_quality="LIMIT_REACHED",
                        liquidity_score=None,
                        evaluated_at=now,
                    )
                )
                continue

            # 1. Carrega observações recentes para esta CardVersion e plataforma
            if not self.db:
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

            obs_prices = [o.price for o in observations if o.price > 0]
            obs_min = min(obs_prices) if obs_prices else None
            obs_recent = observations[0].price if observations else None

            if len(observations) < self.market_intel.min_samples:
                self.latest_diagnoses.append(
                    OpportunityDiagnosis(
                        card_id=card.id,
                        player_id=card.player_id,
                        player_name=p_name,
                        rating=card.rating,
                        version_name=card.rarity,
                        club=card.club,
                        platform=platform,
                        reason_code="INSUFFICIENT_OBSERVATIONS",
                        sample_count=len(observations),
                        valid_sample_count=len(obs_prices),
                        estimated_market_price=None,
                        observed_min_price=obs_min,
                        observed_recent_price=obs_recent,
                        max_buy_price=None,
                        conservative_buy_price=None,
                        conservative_sell_price=None,
                        estimated_tax=None,
                        estimated_profit=None,
                        estimated_roi=None,
                        confidence_score=0.0,
                        confidence_level="LOW",
                        freshness_status="HISTORICAL" if not observations else "FRESH",
                        data_quality="INSUFFICIENT_DATA",
                        liquidity_score=None,
                        evaluated_at=now,
                    )
                )
                continue

            data_points = [
                MarketPriceDataPoint(
                    price=o.price,
                    observed_at=o.observed_at,
                    observation_type=o.observation_type,
                    source=o.source,
                    platform=o.platform,
                )
                for o in observations
            ]

            # 2. Computa Snapshot de Inteligência de Mercado
            snapshot_res = self.market_intel.compute_snapshot(
                observations=data_points,
                card_id=str(card.id),
                platform=platform,
                reference_time=now,
            )

            # Filtros de descarte: dados insuficientes, confiança insuficiente ou cotações estritamente expiradas
            if not snapshot_res.has_sufficient_data:
                self.latest_diagnoses.append(
                    OpportunityDiagnosis(
                        card_id=card.id,
                        player_id=card.player_id,
                        player_name=p_name,
                        rating=card.rating,
                        version_name=card.rarity,
                        club=card.club,
                        platform=platform,
                        reason_code="INSUFFICIENT_DATA",
                        sample_count=snapshot_res.sample_count,
                        valid_sample_count=snapshot_res.valid_sample_count,
                        estimated_market_price=snapshot_res.estimated_market_price,
                        observed_min_price=obs_min,
                        observed_recent_price=obs_recent,
                        max_buy_price=None,
                        conservative_buy_price=snapshot_res.conservative_buy_price,
                        conservative_sell_price=snapshot_res.conservative_sell_price,
                        estimated_tax=None,
                        estimated_profit=None,
                        estimated_roi=None,
                        confidence_score=snapshot_res.confidence_score,
                        confidence_level=snapshot_res.confidence_level,
                        freshness_status=snapshot_res.freshness_status,
                        data_quality=snapshot_res.data_quality,
                        liquidity_score=None,
                        evaluated_at=now,
                    )
                )
                continue

            if snapshot_res.confidence_score < settings.MINIMUM_CONFIDENCE_FOR_ACTION:
                self.latest_diagnoses.append(
                    OpportunityDiagnosis(
                        card_id=card.id,
                        player_id=card.player_id,
                        player_name=p_name,
                        rating=card.rating,
                        version_name=card.rarity,
                        club=card.club,
                        platform=platform,
                        reason_code="INSUFFICIENT_CONFIDENCE",
                        sample_count=snapshot_res.sample_count,
                        valid_sample_count=snapshot_res.valid_sample_count,
                        estimated_market_price=snapshot_res.estimated_market_price,
                        observed_min_price=obs_min,
                        observed_recent_price=obs_recent,
                        max_buy_price=None,
                        conservative_buy_price=snapshot_res.conservative_buy_price,
                        conservative_sell_price=snapshot_res.conservative_sell_price,
                        estimated_tax=None,
                        estimated_profit=None,
                        estimated_roi=None,
                        confidence_score=snapshot_res.confidence_score,
                        confidence_level=snapshot_res.confidence_level,
                        freshness_status=snapshot_res.freshness_status,
                        data_quality=snapshot_res.data_quality,
                        liquidity_score=None,
                        evaluated_at=now,
                    )
                )
                continue

            if snapshot_res.freshness_status == "HISTORICAL":
                self.latest_diagnoses.append(
                    OpportunityDiagnosis(
                        card_id=card.id,
                        player_id=card.player_id,
                        player_name=p_name,
                        rating=card.rating,
                        version_name=card.rarity,
                        club=card.club,
                        platform=platform,
                        reason_code="STALE_DATA",
                        sample_count=snapshot_res.sample_count,
                        valid_sample_count=snapshot_res.valid_sample_count,
                        estimated_market_price=snapshot_res.estimated_market_price,
                        observed_min_price=obs_min,
                        observed_recent_price=obs_recent,
                        max_buy_price=None,
                        conservative_buy_price=snapshot_res.conservative_buy_price,
                        conservative_sell_price=snapshot_res.conservative_sell_price,
                        estimated_tax=None,
                        estimated_profit=None,
                        estimated_roi=None,
                        confidence_score=snapshot_res.confidence_score,
                        confidence_level=snapshot_res.confidence_level,
                        freshness_status=snapshot_res.freshness_status,
                        data_quality=snapshot_res.data_quality,
                        liquidity_score=None,
                        evaluated_at=now,
                    )
                )
                continue

            if snapshot_res.estimated_market_price is None:
                self.latest_diagnoses.append(
                    OpportunityDiagnosis(
                        card_id=card.id,
                        player_id=card.player_id,
                        player_name=p_name,
                        rating=card.rating,
                        version_name=card.rarity,
                        club=card.club,
                        platform=platform,
                        reason_code="NO_VALID_MARKET_PRICE",
                        sample_count=snapshot_res.sample_count,
                        valid_sample_count=snapshot_res.valid_sample_count,
                        estimated_market_price=None,
                        observed_min_price=obs_min,
                        observed_recent_price=obs_recent,
                        max_buy_price=None,
                        conservative_buy_price=snapshot_res.conservative_buy_price,
                        conservative_sell_price=snapshot_res.conservative_sell_price,
                        estimated_tax=None,
                        estimated_profit=None,
                        estimated_roi=None,
                        confidence_score=snapshot_res.confidence_score,
                        confidence_level=snapshot_res.confidence_level,
                        freshness_status=snapshot_res.freshness_status,
                        data_quality=snapshot_res.data_quality,
                        liquidity_score=None,
                        evaluated_at=now,
                    )
                )
                continue

            # Persiste snapshot auditável no banco
            snapshot_entity = MarketSnapshot(
                card_id=card.id,
                platform=platform,
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
                data_origin=data_origin,
            )
            self.db.add(snapshot_entity)
            self.db.flush()

            # 3. Liquidez
            liquidity = self.liquidity_analyzer.analyze(
                [PriceObservation(price=p.price, observed_at=p.observed_at) for p in data_points],
                reference_time=now,
            )

            # 4. Avaliação de Oportunidade e Estratégia
            opp_eval, diag = self.evaluate_opportunity_with_diagnosis(
                card=card,
                snapshot=snapshot_res,
                liquidity_score=liquidity.score,
                latest_observation_price=observations[0].price,
                available_cash=available_cash,
                max_allocation_cap=min(remaining_inventory_capacity, max_player_cap, available_cash),
                snapshot_id=snapshot_entity.id,
                observations=observations,
            )

            self.latest_diagnoses.append(diag)

            if opp_eval:
                discovered_list.append(opp_eval)

        # 5. Persiste as oportunidades filtradas e ranqueadas
        if discovered_list and self.db:
            discovered_list.sort(key=lambda o: o.ranking_score, reverse=True)

            for opp_data in discovered_list:
                opp = (
                    self.db.query(MarketOpportunity)
                    .filter(
                        MarketOpportunity.card_id == opp_data.card_id,
                        MarketOpportunity.platform == platform,
                        MarketOpportunity.data_origin == data_origin,
                    )
                    .first()
                )
                if not opp:
                    opp = MarketOpportunity(
                        card_id=opp_data.card_id,
                        player_id=opp_data.player_id,
                        platform=platform,
                        data_origin=data_origin,
                    )
                    self.db.add(opp)

                opp.observed_price = opp_data.observed_price
                opp.market_price = opp_data.estimated_market_price
                opp.max_buy_price = opp_data.max_buy_price
                opp.target_sell_price = opp_data.target_sell_price
                opp.estimated_profit = opp_data.net_profit
                opp.roi = opp_data.roi
                opp.confidence = opp_data.confidence_level
                opp.liquidity_score = opp_data.liquidity_score
                opp.opportunity_score = opp_data.ranking_score
                opp.strategy_type = opp_data.strategy_type
                opp.capital_efficiency = opp_data.capital_efficiency
                opp.expected_holding_time_minutes = opp_data.expected_holding_time_minutes
                opp.detected_at = now
                opp.expires_at = now + timedelta(minutes=settings.ACTION_RECOMMENDATION_TTL_MINUTES)

                persisted_opps.append(opp)

            self.db.commit()

        return persisted_opps

    def evaluate_opportunity(
        self,
        card: PlayerCard,
        snapshot: MarketSnapshotResult,
        liquidity_score: int,
        latest_observation_price: int,
        available_cash: int,
        max_allocation_cap: int,
        snapshot_id: UUID | None = None,
    ) -> DiscoveredOpportunity | None:
        """Avalia oportunidade preservando retrocompatibilidade com chamadores existentes."""
        opp, _ = self.evaluate_opportunity_with_diagnosis(
            card=card,
            snapshot=snapshot,
            liquidity_score=liquidity_score,
            latest_observation_price=latest_observation_price,
            available_cash=available_cash,
            max_allocation_cap=max_allocation_cap,
            snapshot_id=snapshot_id,
        )
        return opp

    def evaluate_opportunity_with_diagnosis(
        self,
        card: PlayerCard,
        snapshot: MarketSnapshotResult,
        liquidity_score: int,
        latest_observation_price: int,
        available_cash: int,
        max_allocation_cap: int,
        snapshot_id: UUID | None = None,
        observations: list[PriceObservation] | None = None,
    ) -> tuple[DiscoveredOpportunity | None, OpportunityDiagnosis]:
        """Avalia oportunidade e extrai diagnóstico matemático estritamente estruturado e auditável."""
        now = snapshot.calculated_at or datetime.now(timezone.utc)
        p_name = card.player.name if card.player else None

        obs_prices = [o.price for o in observations if o.price > 0] if observations else (
            [latest_observation_price] if latest_observation_price > 0 else []
        )
        obs_min = min(obs_prices) if obs_prices else (latest_observation_price if latest_observation_price > 0 else None)
        obs_recent = latest_observation_price if latest_observation_price > 0 else (observations[0].price if observations else None)

        if not snapshot.estimated_market_price or snapshot.estimated_market_price <= 0:
            diag = OpportunityDiagnosis(
                card_id=card.id,
                player_id=card.player_id,
                player_name=p_name,
                rating=card.rating,
                version_name=card.rarity,
                club=card.club,
                platform=snapshot.platform,
                reason_code="NO_VALID_MARKET_PRICE",
                sample_count=snapshot.sample_count,
                valid_sample_count=snapshot.valid_sample_count,
                estimated_market_price=None,
                observed_min_price=obs_min,
                observed_recent_price=obs_recent,
                max_buy_price=None,
                conservative_buy_price=snapshot.conservative_buy_price,
                conservative_sell_price=snapshot.conservative_sell_price,
                estimated_tax=None,
                estimated_profit=None,
                estimated_roi=None,
                confidence_score=snapshot.confidence_score,
                confidence_level=snapshot.confidence_level,
                freshness_status=snapshot.freshness_status,
                data_quality=snapshot.data_quality,
                liquidity_score=liquidity_score,
                evaluated_at=now,
            )
            return None, diag

        # 1. Definição da Estratégia Baseada em Liquidez e Confiança
        if liquidity_score >= 70 and snapshot.confidence_score >= 0.70:
            strategy_type = "QUICK_FLIP"
            min_roi = settings.MINIMUM_ROI_QUICK_FLIP
            min_profit = settings.MINIMUM_PROFIT_QUICK_FLIP
        elif liquidity_score >= 45:
            strategy_type = "SWING"
            min_roi = settings.MINIMUM_ROI_SWING
            min_profit = settings.MINIMUM_PROFIT_SWING
        else:
            strategy_type = "INVESTMENT"
            min_roi = settings.MINIMUM_ROI_INVESTMENT
            min_profit = settings.MINIMUM_PROFIT_INVESTMENT

        target_sell = snapshot.conservative_sell_price or snapshot.estimated_market_price

        # 2. Cálculo Reverso Estrito de max_buy via TaxEngine
        stat_ceiling = snapshot.conservative_buy_price or int(math.floor(snapshot.estimated_market_price * 0.90))

        buy_by_profit = calculate_max_buy_price(
            target_sell_price=target_sell,
            min_profit=min_profit,
            min_roi=0.0,
            bankroll=available_cash,
            max_bankroll_percentage=1.0,
            tax_rate=settings.TRADING_TAX_RATE,
        )

        buy_by_roi = calculate_max_buy_price(
            target_sell_price=target_sell,
            min_profit=0,
            min_roi=min_roi,
            bankroll=available_cash,
            max_bankroll_percentage=1.0,
            tax_rate=settings.TRADING_TAX_RATE,
        )

        max_buy = min(stat_ceiling, buy_by_profit, buy_by_roi)
        ea_tax = calculate_tax(target_sell)

        if max_buy <= 0:
            diag = OpportunityDiagnosis(
                card_id=card.id,
                player_id=card.player_id,
                player_name=p_name,
                rating=card.rating,
                version_name=card.rarity,
                club=card.club,
                platform=snapshot.platform,
                reason_code="NO_VALID_BUY_PRICE",
                sample_count=snapshot.sample_count,
                valid_sample_count=snapshot.valid_sample_count,
                estimated_market_price=snapshot.estimated_market_price,
                observed_min_price=obs_min,
                observed_recent_price=obs_recent,
                max_buy_price=max_buy,
                conservative_buy_price=stat_ceiling,
                conservative_sell_price=target_sell,
                estimated_tax=ea_tax,
                estimated_profit=None,
                estimated_roi=None,
                confidence_score=snapshot.confidence_score,
                confidence_level=snapshot.confidence_level,
                freshness_status=snapshot.freshness_status,
                data_quality=snapshot.data_quality,
                liquidity_score=liquidity_score,
                evaluated_at=now,
            )
            return None, diag

        if max_buy > available_cash:
            diag = OpportunityDiagnosis(
                card_id=card.id,
                player_id=card.player_id,
                player_name=p_name,
                rating=card.rating,
                version_name=card.rarity,
                club=card.club,
                platform=snapshot.platform,
                reason_code="CAPITAL_INSUFFICIENT",
                sample_count=snapshot.sample_count,
                valid_sample_count=snapshot.valid_sample_count,
                estimated_market_price=snapshot.estimated_market_price,
                observed_min_price=obs_min,
                observed_recent_price=obs_recent,
                max_buy_price=max_buy,
                conservative_buy_price=stat_ceiling,
                conservative_sell_price=target_sell,
                estimated_tax=ea_tax,
                estimated_profit=None,
                estimated_roi=None,
                confidence_score=snapshot.confidence_score,
                confidence_level=snapshot.confidence_level,
                freshness_status=snapshot.freshness_status,
                data_quality=snapshot.data_quality,
                liquidity_score=liquidity_score,
                evaluated_at=now,
            )
            return None, diag

        # 3. Preço Efetivo de Entrada: cotação mais recente do mercado
        entry_price = latest_observation_price
        net_profit = calculate_profit(entry_price, target_sell, settings.TRADING_TAX_RATE)
        roi = calculate_roi(entry_price, target_sell, settings.TRADING_TAX_RATE)
        gross_profit = target_sell - entry_price

        if entry_price > max_buy or entry_price <= 0:
            diag = OpportunityDiagnosis(
                card_id=card.id,
                player_id=card.player_id,
                player_name=p_name,
                rating=card.rating,
                version_name=card.rarity,
                club=card.club,
                platform=snapshot.platform,
                reason_code="INSUFFICIENT_MARGIN",
                sample_count=snapshot.sample_count,
                valid_sample_count=snapshot.valid_sample_count,
                estimated_market_price=snapshot.estimated_market_price,
                observed_min_price=obs_min,
                observed_recent_price=obs_recent,
                max_buy_price=max_buy,
                conservative_buy_price=stat_ceiling,
                conservative_sell_price=target_sell,
                estimated_tax=ea_tax,
                estimated_profit=net_profit,
                estimated_roi=round(roi, 4),
                confidence_score=snapshot.confidence_score,
                confidence_level=snapshot.confidence_level,
                freshness_status=snapshot.freshness_status,
                data_quality=snapshot.data_quality,
                liquidity_score=liquidity_score,
                evaluated_at=now,
            )
            return None, diag

        if net_profit < min_profit:
            diag = OpportunityDiagnosis(
                card_id=card.id,
                player_id=card.player_id,
                player_name=p_name,
                rating=card.rating,
                version_name=card.rarity,
                club=card.club,
                platform=snapshot.platform,
                reason_code="PROFIT_BELOW_THRESHOLD",
                sample_count=snapshot.sample_count,
                valid_sample_count=snapshot.valid_sample_count,
                estimated_market_price=snapshot.estimated_market_price,
                observed_min_price=obs_min,
                observed_recent_price=obs_recent,
                max_buy_price=max_buy,
                conservative_buy_price=stat_ceiling,
                conservative_sell_price=target_sell,
                estimated_tax=ea_tax,
                estimated_profit=net_profit,
                estimated_roi=round(roi, 4),
                confidence_score=snapshot.confidence_score,
                confidence_level=snapshot.confidence_level,
                freshness_status=snapshot.freshness_status,
                data_quality=snapshot.data_quality,
                liquidity_score=liquidity_score,
                evaluated_at=now,
            )
            return None, diag

        if roi < min_roi:
            diag = OpportunityDiagnosis(
                card_id=card.id,
                player_id=card.player_id,
                player_name=p_name,
                rating=card.rating,
                version_name=card.rarity,
                club=card.club,
                platform=snapshot.platform,
                reason_code="ROI_BELOW_THRESHOLD",
                sample_count=snapshot.sample_count,
                valid_sample_count=snapshot.valid_sample_count,
                estimated_market_price=snapshot.estimated_market_price,
                observed_min_price=obs_min,
                observed_recent_price=obs_recent,
                max_buy_price=max_buy,
                conservative_buy_price=stat_ceiling,
                conservative_sell_price=target_sell,
                estimated_tax=ea_tax,
                estimated_profit=net_profit,
                estimated_roi=round(roi, 4),
                confidence_score=snapshot.confidence_score,
                confidence_level=snapshot.confidence_level,
                freshness_status=snapshot.freshness_status,
                data_quality=snapshot.data_quality,
                liquidity_score=liquidity_score,
                evaluated_at=now,
            )
            return None, diag

        # 5. Eficiência de Capital e Holding Time
        capital_efficiency = round(net_profit / float(entry_price), 4) if entry_price > 0 else 0.0
        expected_holding_time: int | None = None

        # 6. Quantidade Recomendada e Alocação de Capital
        qty = max(1, max_allocation_cap // max_buy)
        if strategy_type == "QUICK_FLIP":
            qty = min(qty, settings.MASS_BIDDING_MAX_QUANTITY)
        elif strategy_type == "SWING":
            qty = min(qty, 2)
        else:
            qty = 1

        capital_required = qty * max_buy
        if capital_required > available_cash:
            qty = max(1, available_cash // max_buy)
            capital_required = qty * max_buy

        total_profit = qty * net_profit

        # 7. Ranking Multicritério Determinístico
        ranking_score = self.calculate_ranking_score(
            net_profit=net_profit,
            roi=roi,
            confidence_score=snapshot.confidence_score,
            liquidity_score=liquidity_score,
            capital_efficiency=capital_efficiency,
            strategy_type=strategy_type,
        )

        opp = DiscoveredOpportunity(
            card_id=card.id,
            player_id=card.player_id,
            platform=snapshot.platform,
            strategy_type=strategy_type,
            estimated_market_price=snapshot.estimated_market_price,
            max_buy_price=max_buy,
            target_sell_price=target_sell,
            observed_price=entry_price,
            gross_profit=gross_profit,
            ea_tax=ea_tax,
            net_profit=net_profit,
            roi=round(roi, 4),
            confidence_score=snapshot.confidence_score,
            confidence_level=snapshot.confidence_level,
            liquidity_score=liquidity_score,
            capital_efficiency=capital_efficiency,
            expected_holding_time_minutes=expected_holding_time,
            capital_required=capital_required,
            recommended_quantity=qty,
            estimated_total_profit=total_profit,
            ranking_score=round(ranking_score, 2),
            snapshot_id=snapshot_id,
        )

        diag = OpportunityDiagnosis(
            card_id=card.id,
            player_id=card.player_id,
            player_name=p_name,
            rating=card.rating,
            version_name=card.rarity,
            club=card.club,
            platform=snapshot.platform,
            reason_code="OPPORTUNITY_QUALIFIED",
            sample_count=snapshot.sample_count,
            valid_sample_count=snapshot.valid_sample_count,
            estimated_market_price=snapshot.estimated_market_price,
            observed_min_price=obs_min,
            observed_recent_price=obs_recent,
            max_buy_price=max_buy,
            conservative_buy_price=stat_ceiling,
            conservative_sell_price=target_sell,
            estimated_tax=ea_tax,
            estimated_profit=net_profit,
            estimated_roi=round(roi, 4),
            confidence_score=snapshot.confidence_score,
            confidence_level=snapshot.confidence_level,
            freshness_status=snapshot.freshness_status,
            data_quality=snapshot.data_quality,
            liquidity_score=liquidity_score,
            evaluated_at=now,
        )

        return opp, diag

    @staticmethod
    def calculate_ranking_score(
        net_profit: int,
        roi: float,
        confidence_score: float,
        liquidity_score: int,
        capital_efficiency: float,
        strategy_type: str = "QUICK_FLIP",
    ) -> float:
        """Calcula o score composto de ranqueamento determinístico.

        Garante que cartas com alta confiança e liquidez superem oportunidades
        com alto lucro nominal incerto e dispersão elevada.
        """
        # Normalizações determinísticas em escala de 0 a 100
        roi_norm = min(100.0, max(0.0, roi * 200.0))                      # 50% ROI -> 100 pts
        profit_norm = min(100.0, max(0.0, (net_profit / 2000.0) * 100.0)) # 2000 coins lucro -> 100 pts
        conf_norm = max(0.0, min(100.0, confidence_score * 100.0))        # Confiança 1.0 -> 100 pts
        liq_norm = max(0.0, min(100.0, float(liquidity_score)))           # Liquidez 100 -> 100 pts
        eff_norm = min(100.0, max(0.0, capital_efficiency * 200.0))       # Eficiência 0.50 -> 100 pts

        # Ponderação Multicritério:
        # 25% Confiança + 25% ROI + 20% Lucro Líquido + 15% Liquidez + 15% Eficiência
        composite = (
            0.25 * conf_norm
            + 0.25 * roi_norm
            + 0.20 * profit_norm
            + 0.15 * liq_norm
            + 0.15 * eff_norm
        )
        return composite
