import csv
from datetime import datetime, timezone
import io
from typing import Sequence
from app.providers.base import MarketDataProvider, ProviderCardItem, ProviderPricePoint, RawObservation


class CSVMarketDataProvider(MarketDataProvider):
    """Provedor para importação e parsing em lote de observações através de texto/arquivo CSV."""

    def get_provider_name(self) -> str:
        return "csv"

    def fetch_card_prices(self, external_id: str, platform: str = "console") -> list[ProviderPricePoint]:
        return []

    def fetch_catalog_cards(self, query: str | None = None) -> list[ProviderCardItem]:
        return []

    def parse_csv(self, csv_content: str, default_data_origin: str = "user") -> list[RawObservation]:
        """Faz o parsing estruturado de conteúdo CSV para lista canônica de RawObservation."""
        if not csv_content or not csv_content.strip():
            return []

        results: list[RawObservation] = []
        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        now = datetime.now(timezone.utc)

        for raw_row in reader:
            # Normaliza chaves em minúsculas e sem espaços
            row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items() if k}

            p_name = row.get("player_name") or row.get("player") or row.get("name", "")
            if not p_name:
                continue

            try:
                rating = int(row.get("rating") or row.get("player_rating", 0))
                price = int(row.get("observed_price") or row.get("observed_price_coins") or row.get("price", 0))
            except (ValueError, TypeError):
                continue

            if price <= 0 or rating <= 0:
                continue

            obs_type = row.get("observation_type") or row.get("type") or "buy_now"
            platform = (row.get("platform") or "console").lower()
            provider = row.get("provider") or row.get("source") or "csv"
            ext_id = row.get("external_id") or row.get("external_card_id") or None
            card_id = row.get("card_id") or None
            data_origin = row.get("data_origin") or default_data_origin

            raw_date = row.get("observed_at")
            observed_at = now
            if raw_date:
                try:
                    observed_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                except ValueError:
                    observed_at = now

            results.append(
                RawObservation(
                    player_name=p_name,
                    player_rating=rating,
                    price=price,
                    observation_type=obs_type,
                    platform=platform,
                    position=row.get("position") or None,
                    rarity=row.get("rarity") or row.get("card_version") or row.get("version") or None,
                    league=row.get("league") or None,
                    club=row.get("club") or None,
                    nation=row.get("nation") or None,
                    observed_at=observed_at,
                    provider=provider,
                    external_id=ext_id,
                    card_id=card_id,
                    data_origin=data_origin,
                )
            )

        return results

    def fetch_observations(self, **kwargs) -> Sequence[RawObservation]:
        csv_content: str = kwargs.get("csv_content", "")
        origin: str = kwargs.get("data_origin", "user")
        return self.parse_csv(csv_content, default_data_origin=origin)
