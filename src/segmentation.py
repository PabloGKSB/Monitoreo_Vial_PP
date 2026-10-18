"""Spatial aggregation of experimental road-condition indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AnalysisConfig
from .gps import associate_gps, prepare_gps
from .scoring import add_experimental_road_score


def segment_trip(
    gps_frame: pd.DataFrame,
    window_features: pd.DataFrame,
    events: pd.DataFrame,
    config: AnalysisConfig | None = None,
) -> pd.DataFrame:
    """Aggregate GPS geometry, vibration windows and events into fixed-distance bins."""

    config = config or AnalysisConfig()
    gps = prepare_gps(gps_frame)
    columns = [
        "segment_id", "start_distance_m", "end_distance_m", "start_latitude", "start_longitude",
        "end_latitude", "end_longitude", "event_count", "mean_event_score", "max_event_score",
        "mean_rms", "vibration_intensity", "mean_speed_kmh", "observation_count",
        "road_condition_score", "condition",
    ]
    if gps.empty:
        return pd.DataFrame(columns=columns)
    windows_geo = associate_gps(window_features, gps, config)
    events_geo = events if {"route_distance_m", "gps_route_part"} <= set(events) else associate_gps(events, gps, config)
    max_distance = float(gps["route_distance_m"].max())
    segment_count = max(1, int(np.floor(max_distance / config.road_segment_meters)) + 1)
    rows: list[dict[str, object]] = []
    groups = [(index, part) for index in range(segment_count) for part in gps.route_part.unique()]
    for index, part in groups:
        start = index * config.road_segment_meters
        end = start + config.road_segment_meters
        gps_part = gps[(gps["route_distance_m"] >= start) & (gps["route_distance_m"] < end) & (gps.route_part == part)]
        window_part = windows_geo[(windows_geo["route_distance_m"] >= start) & (windows_geo["route_distance_m"] < end) & (windows_geo.gps_route_part == part)]
        event_part = events_geo[(events_geo["route_distance_m"] >= start) & (events_geo["route_distance_m"] < end) & (events_geo.gps_route_part == part)]
        if gps_part.empty:
            continue
        rows.append({
            "segment_id": f"SEG-{index + 1:04d}-P{int(part)}",
            "start_distance_m": start,
            "end_distance_m": min(end, max_distance),
            "start_latitude": float(gps_part.iloc[0]["latitude"]),
            "start_longitude": float(gps_part.iloc[0]["longitude"]),
            "end_latitude": float(gps_part.iloc[-1]["latitude"]),
            "end_longitude": float(gps_part.iloc[-1]["longitude"]),
            "event_count": len(event_part),
            "mean_event_score": float(event_part["event_score"].mean()) if len(event_part) else np.nan,
            "max_event_score": float(event_part["event_score"].max()) if len(event_part) else np.nan,
            "mean_rms": float(window_part["rms"].mean()) if len(window_part) else np.nan,
            "vibration_intensity": float(window_part["energy"].mean()) if len(window_part) else np.nan,
            "mean_speed_kmh": float(gps_part["speed_kmh"].mean()),
            "observation_count": len(window_part),
        })
    return add_experimental_road_score(pd.DataFrame(rows)).reindex(columns=columns)

