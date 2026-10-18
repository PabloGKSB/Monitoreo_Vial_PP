"""GPS distance calculations and nearest-time association."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AnalysisConfig

EARTH_RADIUS_M = 6_371_008.8


def haversine_m(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Vectorized great-circle distance in metres."""

    lat1r, lon1r, lat2r, lon2r = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def prepare_gps(frame: pd.DataFrame) -> pd.DataFrame:
    """Remove unusable fixes and add speed and cumulative route distance."""

    gps = frame.copy()
    gps = gps.dropna(subset=["seconds_elapsed", "latitude", "longitude"])
    gps = gps[gps["latitude"].between(-90, 90) & gps["longitude"].between(-180, 180)]
    gps = gps.sort_values("seconds_elapsed").reset_index(drop=True)
    # Rendering and distance use the same conservative continuity boundary.
    gps["route_part"] = (gps["seconds_elapsed"].diff() > 2.0).cumsum()
    gps["speed_kmh"] = pd.to_numeric(gps.get("speed", np.nan), errors="coerce") * 3.6
    if len(gps) < 2:
        gps["step_distance_m"] = 0.0
        gps["route_distance_m"] = 0.0
        return gps
    steps = np.zeros(len(gps))
    steps[1:] = haversine_m(
        gps["latitude"].to_numpy()[:-1], gps["longitude"].to_numpy()[:-1],
        gps["latitude"].to_numpy()[1:], gps["longitude"].to_numpy()[1:],
    )
    # Isolated implausible jumps are excluded from distance, but fixes remain visible.
    elapsed_delta = gps["seconds_elapsed"].diff().to_numpy()
    plausible_limit = np.maximum(100.0, np.nan_to_num(elapsed_delta, nan=0.0) * 70.0)
    steps[steps > plausible_limit] = 0.0
    steps[elapsed_delta > 2.0] = 0.0
    gps["step_distance_m"] = steps
    gps["route_distance_m"] = np.cumsum(steps)
    return gps


def associate_gps(
    records: pd.DataFrame,
    gps_frame: pd.DataFrame,
    config: AnalysisConfig | None = None,
) -> pd.DataFrame:
    """Attach the nearest GPS fix when it falls inside the configured tolerance."""

    config = config or AnalysisConfig()
    result = records.copy()
    output_columns = ["latitude", "longitude", "speed_kmh", "gps_accuracy_m", "gps_status", "route_distance_m", "gps_route_part"]
    if result.empty:
        for column in output_columns:
            result[column] = pd.Series(dtype="object" if column == "gps_status" else "float64")
        return result
    gps = prepare_gps(gps_frame)
    if gps.empty:
        for column in ("latitude", "longitude", "speed_kmh", "gps_accuracy_m", "route_distance_m", "gps_route_part"):
            result[column] = np.nan
        result["gps_status"] = "GPS_NOT_AVAILABLE"
        return result

    gps_times = gps["seconds_elapsed"].to_numpy(float)
    record_times = result["seconds_elapsed"].to_numpy(float)
    right = np.searchsorted(gps_times, record_times)
    left = np.clip(right - 1, 0, len(gps) - 1)
    right = np.clip(right, 0, len(gps) - 1)
    choose_right = np.abs(gps_times[right] - record_times) < np.abs(gps_times[left] - record_times)
    indexes = np.where(choose_right, right, left)
    differences = np.abs(gps_times[indexes] - record_times)
    valid = differences <= config.gps_max_time_difference
    selected = gps.iloc[indexes]
    mappings = {
        "latitude": "latitude",
        "longitude": "longitude",
        "speed_kmh": "speed_kmh",
        "gps_accuracy_m": "horizontal_accuracy",
        "route_distance_m": "route_distance_m",
        "gps_route_part": "route_part",
    }
    for target, source in mappings.items():
        values = selected[source].to_numpy() if source in selected else np.full(len(result), np.nan)
        result[target] = np.where(valid, values, np.nan)
    result["gps_time_difference_s"] = differences
    result["gps_status"] = np.where(valid, "OK", "GPS_NOT_AVAILABLE")
    return result


def route_summary(gps_frame: pd.DataFrame) -> dict[str, float]:
    gps = prepare_gps(gps_frame)
    return {
        "distance_km": float(gps["route_distance_m"].max() / 1000) if not gps.empty else 0.0,
        "mean_speed_kmh": float(gps["speed_kmh"].mean()) if not gps.empty else 0.0,
    }
