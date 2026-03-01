"""Data models for dishes and nutrition."""

from dataclasses import dataclass


@dataclass
class Dish:
    id: str
    station_id: str | None
    name: str
    calories: float
    protein_g: float
    station_name: str | None = None
    image_url: str | None = None

    @property
    def stationId(self) -> str | None:
        return self.station_id


def parse_dish(raw: dict) -> "Dish":
    """Build Dish from API raw dict. Treats null calories/protein as 0."""
    n = raw.get("nutritionInfo") or {}
    calories = float(n.get("calories") or 0)
    protein = float(n.get("proteinG") or 0)
    url = raw.get("imageUrl")
    return Dish(
        id=str(raw.get("id", "")),
        station_id=raw.get("stationId"),
        name=str(raw.get("name", "")).strip() or "Unknown",
        calories=calories,
        protein_g=protein,
        station_name=raw.get("stationName"),
        image_url=str(url).strip() if url else None,
    )
