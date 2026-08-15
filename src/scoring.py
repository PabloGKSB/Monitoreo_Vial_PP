"""Experimental road-condition scoring helpers."""

from __future__ import annotations

import pandas as pd


def add_experimental_road_score(segments: pd.DataFrame) -> pd.DataFrame:
    """Rank relative event burden and vibration within one trip on a 0-100 scale.

    This is deliberately a pattern-visualization index, not a validated pavement
    condition metric. A score cannot be compared scientifically across vehicles.
    """

    result = segments.copy()
    if result.empty:
        result["road_condition_score"] = pd.Series(dtype=float)
        result["condition"] = pd.Series(dtype=str)
        return result
    event_burden = result["event_count"] * result["max_event_score"].fillna(0)
    event_rank = event_burden.rank(pct=True, method="average")
    vibration_rank = result["mean_rms"].fillna(0).rank(pct=True, method="average")
    score = (0.7 * event_rank + 0.3 * vibration_rank) * 100
    score = score.where(event_burden > 0, vibration_rank * 30)
    result["road_condition_score"] = score.round(2)
    result["condition"] = pd.cut(
        result["road_condition_score"], bins=[-float("inf"), 40, 70, float("inf")],
        labels=["BUENO", "REGULAR", "MALO"], right=False,
    ).astype(str)
    return result

