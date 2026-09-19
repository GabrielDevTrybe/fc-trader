from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Sequence
from app.core.config import settings


@dataclass(frozen=True)
class MarketPriceDataPoint:
    price: int
    observed_at: datetime
    observation_type: str = "buy_now"  # buy_now, bid, sale_estimate
    source: str = "manual"             # manual, csv, USER_MARKET_CHECK, test
    platform: str = "console"          # console, pc


@dataclass(frozen=True)
class MarketSnapshotResult:
    card_id: str | None
    platform: str
    sample_count: int
    valid_sample_count: int
    clean_sample_count: int
    outliers: list[int]
    clean_prices: list[int]
    min_price: int | None
    max_price: int | None
    median_price: int | None
    p20_price: int | None
    p80_price: int | None
    robust_mean: float | None
    std_dev: float
    dispersion_ratio: float  # Coefficient of Variation (std_dev / mean)
    estimated_market_price: int | None
    conservative_buy_price: int | None
    conservative_sell_price: int | None
    confidence_score: float  # 0.0 to 1.0
    confidence_level: str    # HIGH, MEDIUM, LOW
    freshness_status: str    # FRESH, STALE, HISTORICAL
    newest_observation_age_seconds: int | None
    trend: str               # RISING, FALLING, STABLE, NEUTRAL
    stability_score: float   # 0.0 to 1.0
    data_quality: str        # OK, INSUFFICIENT_DATA, HIGH_DISPERSION, STALE_MARKET_DATA
    has_sufficient_data: bool
    reason: str
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MarketIntelligenceEngine:
    """Motor determinístico de inteligência e análise estatística de mercado.

    Recebe observações de preço para uma CardVersion e plataforma específicas,
    aplicando:
    1. Rejeição de amostras insuficientes (< 3 observações válidas).
    2. Detecção e remoção determinística de outliers via Intervalo Interquartil (IQR).
    3. Cálculo de percentis (Mín, P20, Mediana, P80, Máx).
    4. Média robusta com ponderação temporal por decaimento exponencial.
    5. Métricas de dispersão (Desvio Padrão e Coeficiente de Variação).
    6. Avaliação rigorosa de Freshness (FRESH, STALE, HISTORICAL).
    7. Pontuação de Confiança determinística multidimensional (0.0 a 1.0).
    8. Preservação semântica das fontes (ex: USER_MARKET_CHECK).
    """

    def __init__(
        self,
        min_samples: int | None = None,
        min_samples_for_outliers: int | None = None,
        iqr_multiplier: float | None = None,
        decay_half_life_hours: float = 6.0,
    ) -> None:
        self.min_samples = min_samples if min_samples is not None else settings.MARKET_PRICE_MIN_SAMPLES
        self.min_samples_for_outliers = (
            min_samples_for_outliers if min_samples_for_outliers is not None else settings.MARKET_PRICE_MIN_SAMPLES_FOR_OUTLIERS
        )
        self.iqr_multiplier = iqr_multiplier if iqr_multiplier is not None else settings.MARKET_PRICE_IQR_MULTIPLIER
        self.decay_half_life_hours = decay_half_life_hours

    def compute_snapshot(
        self,
        observations: Sequence[MarketPriceDataPoint],
        card_id: str | None = None,
        platform: str = "console",
        reference_time: datetime | None = None,
    ) -> MarketSnapshotResult:
        now = reference_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        raw_count = len(observations) if observations else 0

        # 1. Filtro básico de cotações válidas (> 0 coins)
        valid_points = [o for o in observations if o.price > 0] if observations else []
        valid_count = len(valid_points)

        if valid_count < self.min_samples:
            return MarketSnapshotResult(
                card_id=card_id,
                platform=platform,
                sample_count=raw_count,
                valid_sample_count=valid_count,
                clean_sample_count=valid_count,
                outliers=[],
                clean_prices=[p.price for p in valid_points],
                min_price=min([p.price for p in valid_points]) if valid_points else None,
                max_price=max([p.price for p in valid_points]) if valid_points else None,
                median_price=None,
                p20_price=None,
                p80_price=None,
                robust_mean=None,
                std_dev=0.0,
                dispersion_ratio=0.0,
                estimated_market_price=None,
                conservative_buy_price=None,
                conservative_sell_price=None,
                confidence_score=0.0,
                confidence_level="LOW",
                freshness_status="HISTORICAL" if not valid_points else self._evaluate_freshness(valid_points, now)[0],
                newest_observation_age_seconds=self._evaluate_freshness(valid_points, now)[1] if valid_points else None,
                trend="NEUTRAL",
                stability_score=0.0,
                data_quality="INSUFFICIENT_DATA",
                has_sufficient_data=False,
                reason=f"Dados insuficientes ({valid_count}/{self.min_samples} observações mínimas requeridas)",
                calculated_at=now,
            )

        # 2. Ordenação e Detecção de Outliers via IQR
        sorted_points = sorted(valid_points, key=lambda x: x.price)
        sorted_prices = [p.price for p in sorted_points]

        clean_points: list[MarketPriceDataPoint] = []
        outliers: list[int] = []

        if valid_count >= self.min_samples_for_outliers:
            q1 = self._percentile(sorted_prices, 25)
            q3 = self._percentile(sorted_prices, 75)
            iqr = q3 - q1

            if iqr == 0:
                med = self._percentile(sorted_prices, 50)
                lower_bound = max(100, int(med * 0.70))
                upper_bound = int(med * 1.30)
            else:
                lower_bound = max(100, int(q1 - self.iqr_multiplier * iqr))
                upper_bound = int(q3 + self.iqr_multiplier * iqr)

            for pt in sorted_points:
                if lower_bound <= pt.price <= upper_bound:
                    clean_points.append(pt)
                else:
                    outliers.append(pt.price)

            # Se todos ou quase todos fossem expurgados por distorção, preserva originais
            if len(clean_points) < self.min_samples:
                clean_points = list(sorted_points)
                outliers = []
        else:
            clean_points = list(sorted_points)

        clean_prices = sorted([pt.price for pt in clean_points])
        clean_count = len(clean_prices)

        # 3. Percentis Estatísticos
        min_p = clean_prices[0]
        max_p = clean_prices[-1]
        p20_p = int(self._percentile(clean_prices, 20))
        median_p = int(self._percentile(clean_prices, 50))
        p80_p = int(self._percentile(clean_prices, 80))

        # 4. Média Robusta com Ponderação Temporal Exponencial
        weighted_sum = 0.0
        total_weight = 0.0

        for pt in clean_points:
            pt_time = pt.observed_at
            if pt_time.tzinfo is None:
                pt_time = pt_time.replace(tzinfo=timezone.utc)
            delta_hours = max(0.0, (now - pt_time).total_seconds() / 3600.0)
            weight = math.pow(2.0, -delta_hours / self.decay_half_life_hours)

            weighted_sum += pt.price * weight
            total_weight += weight

        robust_mean = (weighted_sum / total_weight) if total_weight > 0 else float(median_p)

        # 5. Métricas de Dispersão
        arithmetic_mean = sum(clean_prices) / clean_count
        variance = sum((p - arithmetic_mean) ** 2 for p in clean_prices) / clean_count
        std_dev = math.sqrt(variance)
        dispersion_ratio = (std_dev / arithmetic_mean) if arithmetic_mean > 0 else 0.0

        # 6. Freshness da Amostragem
        freshness_status, newest_age_sec = self._evaluate_freshness(clean_points, now)

        # 7. Tendência Temporal (Trend)
        trend = self._calculate_trend(clean_points)

        # 8. Preço Justo Estimado e Preços Conservadores
        estimated_market_price = self._round_to_fut_increment(int(round(robust_mean)))
        conservative_sell_price = min(median_p, int(round(robust_mean)))
        conservative_buy_price = min(p20_p, int(math.floor(estimated_market_price * 0.90)))

        # 9. Estabilidade e Confiança Determinística
        diff_med_mean = abs(median_p - robust_mean) / robust_mean if robust_mean > 0 else 1.0
        stability_score = max(0.0, 1.0 - diff_med_mean - (dispersion_ratio * 0.5))

        conf_score, conf_level = self._calculate_confidence(
            sample_count=clean_count,
            newest_age_sec=newest_age_sec,
            dispersion_ratio=dispersion_ratio,
            stability_score=stability_score,
        )

        # 10. Classificação de Qualidade dos Dados
        data_quality = "OK"
        if freshness_status == "HISTORICAL":
            data_quality = "STALE_MARKET_DATA"
        elif dispersion_ratio > 0.25:
            data_quality = "HIGH_DISPERSION"

        return MarketSnapshotResult(
            card_id=card_id,
            platform=platform,
            sample_count=raw_count,
            valid_sample_count=valid_count,
            clean_sample_count=clean_count,
            outliers=outliers,
            clean_prices=clean_prices,
            min_price=min_p,
            max_price=max_p,
            median_price=median_p,
            p20_price=p20_p,
            p80_price=p80_p,
            robust_mean=round(robust_mean, 2),
            std_dev=round(std_dev, 2),
            dispersion_ratio=round(dispersion_ratio, 4),
            estimated_market_price=estimated_market_price,
            conservative_buy_price=conservative_buy_price,
            conservative_sell_price=conservative_sell_price,
            confidence_score=round(conf_score, 2),
            confidence_level=conf_level,
            freshness_status=freshness_status,
            newest_observation_age_seconds=newest_age_sec,
            trend=trend,
            stability_score=round(stability_score, 2),
            data_quality=data_quality,
            has_sufficient_data=True,
            reason="Snapshot de mercado computado com sucesso",
            calculated_at=now,
        )

    @staticmethod
    def _percentile(sorted_data: list[int], percentile: float) -> float:
        if not sorted_data:
            return 0.0
        k = (len(sorted_data) - 1) * (percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return float(sorted_data[int(k)])
        d0 = sorted_data[int(f)] * (c - k)
        d1 = sorted_data[int(c)] * (k - f)
        return float(d0 + d1)

    @staticmethod
    def _evaluate_freshness(points: Sequence[MarketPriceDataPoint], now: datetime) -> tuple[str, int]:
        if not points:
            return "HISTORICAL", 999999

        newest_sec = min(
            max(0, int((now - (pt.observed_at.replace(tzinfo=timezone.utc) if pt.observed_at.tzinfo is None else pt.observed_at)).total_seconds()))
            for pt in points
        )

        fresh_limit = settings.OBSERVATION_FRESH_MINUTES * 60
        stale_limit = settings.OBSERVATION_STALE_MINUTES * 60

        if newest_sec <= fresh_limit:
            return "FRESH", newest_sec
        elif newest_sec <= stale_limit:
            return "STALE", newest_sec
        return "HISTORICAL", newest_sec

    @staticmethod
    def _calculate_trend(points: Sequence[MarketPriceDataPoint]) -> str:
        if len(points) < 4:
            return "NEUTRAL"

        # Ordena cronologicamente para avaliar declive temporal
        chrono = sorted(
            points,
            key=lambda p: p.observed_at.replace(tzinfo=timezone.utc) if p.observed_at.tzinfo is None else p.observed_at,
        )
        mid = len(chrono) // 2
        older_half = chrono[:mid]
        newer_half = chrono[mid:]

        avg_older = sum(p.price for p in older_half) / len(older_half)
        avg_newer = sum(p.price for p in newer_half) / len(newer_half)

        if avg_older <= 0:
            return "NEUTRAL"

        pct_change = (avg_newer - avg_older) / avg_older
        if pct_change >= 0.04:
            return "RISING"
        elif pct_change <= -0.04:
            return "FALLING"
        return "STABLE"

    @staticmethod
    def _calculate_confidence(
        sample_count: int,
        newest_age_sec: int,
        dispersion_ratio: float,
        stability_score: float,
    ) -> tuple[float, str]:
        # 1. Componente Amostral (30%)
        if sample_count >= 8:
            s_samples = 1.0
        elif sample_count >= 5:
            s_samples = 0.75
        elif sample_count >= 3:
            s_samples = 0.40
        else:
            s_samples = 0.0

        # 2. Componente de Freshness (30%)
        if newest_age_sec <= 300:      # <= 5 min
            s_fresh = 1.0
        elif newest_age_sec <= 900:    # <= 15 min
            s_fresh = 0.85
        elif newest_age_sec <= 1800:   # <= 30 min
            s_fresh = 0.50
        elif newest_age_sec <= 3600:   # <= 60 min
            s_fresh = 0.25
        else:
            s_fresh = 0.0

        # 3. Componente de Dispersão (25%)
        if dispersion_ratio <= 0.05:
            s_disp = 1.0
        elif dispersion_ratio <= 0.10:
            s_disp = 0.80
        elif dispersion_ratio <= 0.15:
            s_disp = 0.60
        elif dispersion_ratio <= 0.25:
            s_disp = 0.30
        else:
            s_disp = 0.05

        # 4. Componente de Estabilidade (15%)
        s_stab = max(0.0, min(1.0, stability_score))

        score = (
            settings.CONFIDENCE_WEIGHT_SAMPLES * s_samples
            + settings.CONFIDENCE_WEIGHT_FRESHNESS * s_fresh
            + settings.CONFIDENCE_WEIGHT_DISPERSION * s_disp
            + settings.CONFIDENCE_WEIGHT_STABILITY * s_stab
        )
        score = max(0.0, min(1.0, score))

        if score >= 0.75:
            level = "HIGH"
        elif score >= settings.MINIMUM_CONFIDENCE_FOR_ACTION:
            level = "MEDIUM"
        else:
            level = "LOW"

        return score, level

    @staticmethod
    def _round_to_fut_increment(price: int) -> int:
        """Arredonda para incremento canônico do mercado Ultimate Team."""
        if price <= 1000:
            step = 50
        elif price <= 10000:
            step = 100
        elif price <= 50000:
            step = 250
        elif price <= 100000:
            step = 500
        else:
            step = 1000
        return int(round(price / step) * step)
