"""Recommend meal combos that fit remaining calories and maximize protein."""

import itertools
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import Dish


def recommend(
    dishes: list["Dish"],
    cal_left: float,
    protein_left: float,
    max_items: int = 3,
    top_k: int = 5,
    cal_wiggle: float = 50,
) -> list[tuple[list["Dish"], float, float]]:
    """
    Return top_k combos of 1..max_items dishes that fit within cal_left + cal_wiggle,
    scored by: minimize protein shortfall (heavily), avoid huge protein overshoot (lightly),
    then minimize leftover calories.
    """
    if not dishes or cal_left <= 0:
        return []

    # Limit to ~80 highest-protein dishes for speed
    sorted_by_protein = sorted(dishes, key=lambda d: d.protein_g, reverse=True)
    pool = sorted_by_protein[:80]

    cal_max = cal_left + cal_wiggle
    combos: list[tuple[list["Dish"], float, float]] = []

    for n in range(1, max_items + 1):
        for combo in itertools.combinations(pool, n):
            total_cal = sum(d.calories for d in combo)
            total_protein = sum(d.protein_g for d in combo)
            if total_cal > cal_max:
                continue
            combos.append((list(combo), total_cal, total_protein))

    def score(item: tuple[list["Dish"], float, float]) -> tuple[float, float, float]:
        _, total_cal, total_protein = item
        shortfall = max(0.0, protein_left - total_protein)
        overshoot = max(0.0, total_protein - protein_left)
        leftover_cal = max(0.0, cal_left - total_cal)
        # Minimize shortfall (heavy), then lightly penalize overshoot, then minimize leftover cal
        return (shortfall, overshoot * 0.1, leftover_cal)

    combos.sort(key=score)
    return combos[:top_k]
