import csv
from datetime import datetime, timezone
import io
from typing import Sequence
from app.providers.base import MarketDataProvider, RawObservation


class CSVMarketDataProvider(MarketDataProvider):
    """Provedor para importação em lote de observações através de texto/arquivo CSV."""

    def fetch_observations(self, **kwargs) -> Sequence[RawObservation]:
        csv_content: str = kwargs.get("csv_content", "")
        if not csv_content.strip():
            return []

        results: list[RawObservation] = []
        reader = csv.DictReader(io.StringIO(csv_content))
        now = datetime.now(timezone.utc)

        for row in reader:
            p_name = row.get("player") or row.get("player_name", "")
            if not p_name:
                continue

            try:
                rating = int(row.get("rating") or row.get("player_rating", 0))
                price = int(row.get("price", 0))
            except (ValueError, TypeError):
                continue

            obs_type = row.get("type") or row.get("observation_type", "buy_now")
            raw_date = row.get("observed_at")
            observed_at = now
            if raw_date:
                try:
                    observed_at = datetime.fromisoformat(raw_date)
                except ValueError:
                    observed_at = now

            results.append(
                RawObservation(
                    player_name=p_name.strip(),
                    player_rating=rating,
                    price=price,
                    observation_type=obs_type,
                    position=row.get("position"),
                    rarity=row.get("rarity"),
                    league=row.get("league"),
                    club=row.get("club"),
                    nation=row.get("nation"),
                    observed_at=observed_at,
                )
            )
        return results
