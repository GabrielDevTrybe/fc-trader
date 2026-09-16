from datetime import datetime, timezone
from typing import Any, Sequence
from app.providers.base import MarketDataProvider, RawObservation


class ManualMarketDataProvider(MarketDataProvider):
    """Provedor para entrada manual rápida de observações de preços (lotes ou individuais)."""

    def fetch_observations(self, **kwargs) -> Sequence[RawObservation]:
        raw_items: list[dict[str, Any]] = kwargs.get("items", [])
        results: list[RawObservation] = []

        now = datetime.now(timezone.utc)
        for item in raw_items:
            # Suporta chaves "player" ou "player_name", "type" ou "observation_type"
            p_name = item.get("player") or item.get("player_name", "")
            p_rating = int(item.get("rating") or item.get("player_rating", 0))
            price = int(item.get("price", 0))
            obs_type = item.get("type") or item.get("observation_type", "buy_now")
            observed_at = item.get("observed_at") or now

            if isinstance(observed_at, str):
                try:
                    observed_at = datetime.fromisoformat(observed_at)
                except ValueError:
                    observed_at = now

            results.append(
                RawObservation(
                    player_name=p_name.strip(),
                    player_rating=p_rating,
                    price=price,
                    observation_type=obs_type,
                    position=item.get("position"),
                    rarity=item.get("rarity"),
                    league=item.get("league"),
                    club=item.get("club"),
                    nation=item.get("nation"),
                    observed_at=observed_at,
                )
            )
        return results
