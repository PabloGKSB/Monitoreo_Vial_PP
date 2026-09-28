"""Annotation-assisted datasets with audited exclusions and deterministic sampling."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import AnalysisConfig
from src.gps import associate_gps
from .data import MARKERS, PilotConfig, PilotTrip, window_features


def normal_is_clear(center: float, event_times: np.ndarray, config: PilotConfig) -> bool:
    """The entire NORMAL window must lie outside every event's exclusion interval."""
    margin = config.normal_exclusion_seconds + config.window_seconds / 2
    return bool(np.all(np.abs(event_times - center) > margin))


def candidate_peak(trip: PilotTrip, timestamp: float, config: PilotConfig) -> float:
    frame = trip.signals["accelerometer"]
    part = frame[frame["seconds_elapsed"].between(timestamp - config.search_before_seconds,
                                                timestamp + config.search_after_seconds)]
    if part.empty:
        return float("nan")
    magnitude = np.linalg.norm(part[["x", "y", "z"]].to_numpy(float), axis=1)
    if not np.isfinite(magnitude).all():
        return float("nan")
    return float(part.iloc[int(np.argmax(magnitude))]["seconds_elapsed"])


def build_dataset(trip: PilotTrip, config: PilotConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Produce fixed-delay and peak-assisted datasets, both explicitly exploratory."""
    events = trip.annotations[~trip.annotations["event_type"].isin(MARKERS)].copy()
    events["candidate_peak_seconds"] = [candidate_peak(trip, t, config) for t in events.seconds_elapsed]
    events["candidate_delay_seconds"] = events.seconds_elapsed - events.candidate_peak_seconds
    events["route_id"] = trip.route_id
    events["candidate_status"] = "UNREVIEWED_PEAK_NOT_GROUND_TRUTH"
    interval_start = max(float(trip.annotations.seconds_elapsed.min()),
                         max(float(trip.signals[s].seconds_elapsed.min()) for s in ("accelerometer", "total_acceleration", "gyroscope")))
    interval_end = min(float(trip.annotations.seconds_elapsed.max()),
                       min(float(trip.signals[s].seconds_elapsed.max()) for s in ("accelerometer", "total_acceleration", "gyroscope")))
    half = config.window_seconds / 2
    all_rows = []
    for mode in ("fixed_delay", "peak_assisted"):
        rows, accepted_centers = [], []
        statuses = {}
        for event in events[events.event_type == "BACHE"].itertuples():
            center = (event.seconds_elapsed - config.fixed_delay_seconds
                      if mode == "fixed_delay" else event.candidate_peak_seconds)
            reason = "ACCEPTED_UNREVIEWED"
            features = None
            if not np.isfinite(center) or center - half < interval_start or center + half > interval_end:
                reason = "OUTSIDE_COMMON_CAPTURE"
            elif any(abs(center - previous) < config.window_seconds for previous in accepted_centers):
                reason = "OVERLAPPING_POSITIVE"
            else:
                features = window_features(trip, center, config)
                if features is None:
                    reason = "INCOMPLETE_OR_GAPPY_WINDOW"
            statuses[event.annotation_id] = reason
            if features is None:
                continue
            accepted_centers.append(center)
            rows.append({"sample_id": f"{trip.route_id}_{mode}_{event.annotation_id}",
                         "annotation_id": event.annotation_id, "label": 1,
                         "label_source": "BACHE_MANUAL_UNREVIEWED", "seconds_elapsed": center,
                         "annotation_seconds": event.seconds_elapsed, **features})
        events[f"{mode}_status"] = events.annotation_id.map(statuses).fillna("EXCLUSION_ONLY")

        # Same grid and seed across modes; never use amplitude to choose negatives.
        grid = np.arange(interval_start + half, interval_end - half, config.window_seconds)
        grid = grid[[normal_is_clear(t, events.seconds_elapsed.to_numpy(), config) for t in grid]]
        rng = np.random.default_rng(config.seed)
        selected_normals = 0
        target = config.normal_ratio * len(accepted_centers)
        for center in rng.permutation(grid):
            if selected_normals >= target:
                break
            if any(abs(center - previous) < config.window_seconds for previous in accepted_centers):
                continue
            features = window_features(trip, float(center), config)
            if features is None:
                continue
            selected_normals += 1
            rows.append({"sample_id": f"{trip.route_id}_{mode}_N{selected_normals:03d}",
                         "annotation_id": "", "label": 0, "label_source": "NORMAL_CANDIDATE_UNREVIEWED",
                         "seconds_elapsed": float(center), "annotation_seconds": np.nan, **features})
        if not rows:
            continue
        frame = pd.DataFrame(rows)
        frame["route_id"], frame["mode"] = trip.route_id, mode
        frame["window_start"] = frame.seconds_elapsed - half
        frame["window_end"] = frame.seconds_elapsed + half
        frame["timestamp_utc"] = trip.origin + pd.to_timedelta(frame.seconds_elapsed, unit="s")
        frame = associate_gps(frame, trip.gps, AnalysisConfig(gps_max_time_difference=config.gps_tolerance_seconds))
        all_rows.append(frame)
    events = associate_gps(events, trip.gps, AnalysisConfig(gps_max_time_difference=config.gps_tolerance_seconds))
    return pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame(), events
