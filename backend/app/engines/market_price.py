from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Sequence


@dataclass(frozen=True)
class PriceDataPoint:
    price: int
    observed_at: datetime | None = None
    observation_type: str = "buy_now"  # "buy_now", "bid", "sale_estimate"


@dataclass(frozen=True)
class MarketPriceResult:
    market_price: int | None
    sample_count: int
    valid_sample_count: int
    outliers: list[int]
    clean_prices: list[int]
    median_price: int | None
    trimmed_mean: float | None
    std_dev: float
    confidence: str  # "LOW", "MEDIUM", "HIGH"
    has_sufficient_data: bool
    reason: str


class MarketPriceEngine:
    """Motor determinístico para estimação do preço justo de mercado (Fair Market Price).

    Aplica:
    1. Rejeição de dados insuficientes (< 3 observações).
    2. Detecção e remoção determinística de outliers via Intervalo Interquartil (IQR).
    3. Ponderação por decaimento temporal para priorizar observações recentes.
    """

    def __init__(
        self,
        min_samples: int = 3,
        min_samples_for_outliers: int = 5,
        iqr_multiplier: float = 2.0,
        decay_half_life_hours: float = 12.0,
    ) -> None:
        self.min_samples = min_samples
        self.min_samples_for_outliers = min_samples_for_outliers
        self.iqr_multiplier = iqr_multiplier
        self.decay_half_life_hours = decay_half_life_hours

    def calculate_fair_price(
        self,
        observations: Sequence[PriceDataPoint],
        reference_time: datetime | None = None,
    ) -> MarketPriceResult:
        if not observations or len(observations) < self.min_samples:
            prices = [obs.price for obs in observations] if observations else []
            return MarketPriceResult(
                market_price=None,
                sample_count=len(prices),
                valid_sample_count=len(prices),
                outliers=[],
                clean_prices=prices,
                median_price=int(sorted(prices)[len(prices) // 2]) if prices else None,
                trimmed_mean=None,
                std_dev=0.0,
                confidence="LOW",
                has_sufficient_data=False,
                reason="Dados insuficientes (mínimo de 3 observações requeridas)",
            )

        # 1. Extração e ordenação dos preços
        raw_prices = [obs.price for obs in observations if obs.price > 0]
        if len(raw_prices) < self.min_samples:
            return MarketPriceResult(
                market_price=None,
                sample_count=len(raw_prices),
                valid_sample_count=len(raw_prices),
                outliers=[],
                clean_prices=raw_prices,
                median_price=None,
                trimmed_mean=None,
                std_dev=0.0,
                confidence="LOW",
                has_sufficient_data=False,
                reason="Observações com preços válidos insuficientes",
            )

        sorted_prices = sorted(raw_prices)
        n = len(sorted_prices)

        # 2. Detecção de Outliers via IQR (quando N >= min_samples_for_outliers)
        clean_obs: list[PriceDataPoint] = []
        outliers: list[int] = []

        if n >= self.min_samples_for_outliers:
            q1 = self._percentile(sorted_prices, 25)
            q3 = self._percentile(sorted_prices, 75)
            iqr = q3 - q1

            if iqr == 0:
                med = self._percentile(sorted_prices, 50)
                lower_bound = max(100, int(med * 0.50))
                upper_bound = int(med * 2.0)
            else:
                lower_bound = max(100, int(q1 - self.iqr_multiplier * iqr))
                upper_bound = int(q3 + self.iqr_multiplier * iqr)

            for obs in observations:
                if lower_bound <= obs.price <= upper_bound:
                    clean_obs.append(obs)
                else:
                    outliers.append(obs.price)

            # Se todos ou quase todos fossem descartados, mantém os dados originais
            if len(clean_obs) < 2:
                clean_obs = list(observations)
                outliers = []
        else:
            clean_obs = list(observations)

        clean_prices = [obs.price for obs in clean_obs]
        sorted_clean = sorted(clean_prices)
        median_price = int(self._percentile(sorted_clean, 50))

        # 3. Ponderação Temporal com Decaimento Exponencial
        now = reference_time or datetime.now(timezone.utc)
        weighted_sum = 0.0
        total_weight = 0.0

        for obs in clean_obs:
            weight = 1.0
            if obs.observed_at:
                obs_time = obs.observed_at
                if obs_time.tzinfo is None:
                    obs_time = obs_time.replace(tzinfo=timezone.utc)
                delta_hours = max(0.0, (now - obs_time).total_seconds() / 3600.0)
                # decaimento: 2^(-delta / half_life)
                weight = math.pow(2.0, -delta_hours / self.decay_half_life_hours)

            weighted_sum += obs.price * weight
            total_weight += weight

        fair_price = int(round(weighted_sum / total_weight)) if total_weight > 0 else median_price

        # 4. Cálculo de Desvio Padrão
        mean = sum(clean_prices) / len(clean_prices)
        variance = sum((p - mean) ** 2 for p in clean_prices) / len(clean_prices)
        std_dev = math.sqrt(variance)

        # 5. Avaliação de Confiança
        confidence = self._assess_confidence(len(clean_prices), std_dev, mean)

        return MarketPriceResult(
            market_price=fair_price,
            sample_count=len(observations),
            valid_sample_count=len(clean_prices),
            outliers=outliers,
            clean_prices=clean_prices,
            median_price=median_price,
            trimmed_mean=round(mean, 2),
            std_dev=round(std_dev, 2),
            confidence=confidence,
            has_sufficient_data=True,
            reason="Preço justo calculado com sucesso",
        )

    @staticmethod
    def _percentile(sorted_data: list[int], percentile: float) -> float:
        """Calcula percentil linear determinístico em lista ordenada."""
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
    def _assess_confidence(sample_size: int, std_dev: float, mean: float) -> str:
        cv = (std_dev / mean) if mean > 0 else 1.0
        if sample_size >= 7 and cv <= 0.10:
            return "HIGH"
        elif sample_size >= 4 and cv <= 0.20:
            return "MEDIUM"
        return "LOW"
