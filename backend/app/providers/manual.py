from datetime import datetime, timezone
from typing import Any, Sequence
from app.providers.base import MarketDataProvider, ProviderCardItem, ProviderPricePoint, RawObservation


class ManualMarketDataProvider(MarketDataProvider):
    """Provedor para entrada manual e checagem pontual (USER_MARKET_CHECK)."""

    def get_provider_name(self) -> str:
        return "manual"

    def fetch_card_prices(self, external_id: str, platform: str = "console") -> list[ProviderPricePoint]:
        return []

    def fetch_catalog_cards(self, query: str | None = None) -> list[ProviderCardItem]:
        return []

    def fetch_observations(self, **kwargs) -> Sequence[RawObservation]:
        raw_items: list[dict[str, Any]] = kwargs.get("items", [])
        default_origin: str = kwargs.get("data_origin", "user")
        results: list[RawObservation] = []

        now = datetime.now(timezone.utc)
        for item in raw_items:
            p_name = item.get("player") or item.get("player_name") or item.get("name", "")
            if not p_name:
                continue

            try:
                p_rating = int(item.get("rating") or item.get("player_rating", 0))
                price = int(item.get("price", 0))
            except (ValueError, TypeError):
                continue

            if price <= 0 or p_rating <= 0:
                continue

            obs_type = item.get("type") or item.get("observation_type", "buy_now")
            platform = (item.get("platform") or "console").lower()
            provider = item.get("provider") or item.get("source") or "manual"
            data_origin = item.get("data_origin") or default_origin
            observed_at = item.get("observed_at") or now

            if isinstance(observed_at, str):
                try:
                    observed_at = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
                except ValueError:
                    observed_at = now

            results.append(
                RawObservation(
                    player_name=p_name.strip(),
                    player_rating=p_rating,
                    price=price,
                    observation_type=obs_type,
                    platform=platform,
                    position=item.get("position"),
                    rarity=item.get("rarity") or item.get("card_version") or item.get("version"),
                    league=item.get("league"),
                    club=item.get("club"),
                    nation=item.get("nation"),
                    observed_at=observed_at,
                    provider=provider,
                    external_id=item.get("external_card_id") or item.get("external_id"),
                    card_id=item.get("card_id"),
                    data_origin=data_origin,
                )
            )
        return results
