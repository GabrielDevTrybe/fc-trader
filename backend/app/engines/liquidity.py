from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Sequence

from app.engines.market_price import PriceDataPoint


@dataclass(frozen=True)
class LiquidityResult:
    score: int  # 0 to 100
    observation_count: int
    newest_observation_age_minutes: float | None
    price_spread_percentage: float
    confidence: str  # "LOW", "MEDIUM", "HIGH"
    reason: str


class LiquidityAnalyzer:
    """Analisador determinístico de liquidez de mercado (Score de 0 a 100).

    Baseia-se estritamente em dados observados reais:
    - Quantidade e frequência de observações registradas.
    - Idade da observação mais recente.
    - Dispersão e estabilidade de preço (spread e coeficiente de variação).
    """

    def analyze(
        self,
        observations: Sequence[PriceDataPoint],
        reference_time: datetime | None = None,
    ) -> LiquidityResult:
        if not observations:
            return LiquidityResult(
                score=0,
                observation_count=0,
                newest_observation_age_minutes=None,
                price_spread_percentage=0.0,
                confidence="LOW",
                reason="Sem observações registradas para análise de liquidez",
            )

        now = reference_time or datetime.now(timezone.utc)
        count = len(observations)
        prices = [obs.price for obs in observations if obs.price > 0]

        if not prices:
            return LiquidityResult(
                score=0,
                observation_count=count,
                newest_observation_age_minutes=None,
                price_spread_percentage=0.0,
                confidence="LOW",
                reason="Sem preços válidos registrados",
            )

        # 1. Fator Volume de Amostras (0 a 35 pontos)
        if count >= 10:
            volume_pts = 35
        elif count >= 6:
            volume_pts = 28
        elif count >= 3:
            volume_pts = 18
        else:
            volume_pts = 6

        # 2. Fator Recência da Observação mais nova (0 a 35 pontos)
        newest_age_minutes: float | None = None
        valid_dates = [obs.observed_at for obs in observations if obs.observed_at]

        if valid_dates:
            normalized_dates = [
                d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
                for d in valid_dates
            ]
            most_recent = max(normalized_dates)
            delta_seconds = max(0.0, (now - most_recent).total_seconds())
            newest_age_minutes = round(delta_seconds / 60.0, 1)

            if newest_age_minutes <= 15:
                recency_pts = 35
            elif newest_age_minutes <= 60:
                recency_pts = 28
            elif newest_age_minutes <= 180:
                recency_pts = 18
            elif newest_age_minutes <= 360:
                recency_pts = 10
            else:
                recency_pts = 4
        else:
            recency_pts = 12  # Padrão neutro quando data exata não informada

        # 3. Fator Estabilidade de Preço / Spread (0 a 30 pontos)
        min_p, max_p = min(prices), max(prices)
        mean_p = sum(prices) / len(prices)
        spread_pct = ((max_p - min_p) / mean_p) if mean_p > 0 else 0.0

        variance = sum((p - mean_p) ** 2 for p in prices) / len(prices)
        cv = (math.sqrt(variance) / mean_p) if mean_p > 0 else 1.0

        if cv <= 0.06:
            stability_pts = 30
        elif cv <= 0.12:
            stability_pts = 22
        elif cv <= 0.22:
            stability_pts = 14
        else:
            stability_pts = 5

        total_score = min(100, max(0, volume_pts + recency_pts + stability_pts))

        if count >= 6 and total_score >= 65:
            confidence = "HIGH"
        elif count >= 3 and total_score >= 40:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        return LiquidityResult(
            score=total_score,
            observation_count=count,
            newest_observation_age_minutes=newest_age_minutes,
            price_spread_percentage=round(spread_pct * 100, 1),
            confidence=confidence,
            reason=f"Liquidez avaliada com {count} amostras (Score: {total_score}/100)",
        )
