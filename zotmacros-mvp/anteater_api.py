"""AnteaterAPI dining client. All responses are wrapped as { "ok": true, "data": ... }."""

import requests

BASE = "https://anteaterapi.com/v2/rest/dining"
TIMEOUT = 15


def _get(path: str, params: dict | None = None) -> any:
    url = f"{BASE}{path}"
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"AnteaterAPI request failed: {e}") from e

    data = r.json()
    if not isinstance(data, dict):
        raise RuntimeError("AnteaterAPI returned invalid JSON")
    if not data.get("ok"):
        raise RuntimeError("API returned ok=false")
    return data.get("data")


def get_restaurants(id: str | None = None) -> list[dict]:
    """Fetch restaurants list. If id is passed, filter by id (e.g. anteatery, brandywine)."""
    params = {"id": id} if id else None
    return _get("/restaurants", params) or []


def get_restaurant_today(restaurant_id: str, day_iso: str) -> dict:
    """Fetch restaurant menu for a given day: periods + stationToDishes."""
    return _get("/restaurantToday", {"id": restaurant_id, "date": day_iso}) or {}


def get_dishes_batch(ids: list[str]) -> list[dict]:
    """Fetch dish details (including nutritionInfo) for given IDs."""
    if not ids:
        return []
    ids_param = ",".join(ids)
    return _get("/dishes/batch", {"ids": ids_param}) or []
