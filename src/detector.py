"""Adaptive, robust anomaly detector for possible road irregularities."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AnalysisConfig

SCORE_FEATURES = ("magnitude_max", "rms", "std", "jerk_max", "energy")


def _robust_positive_z(values: pd.Series) -> np.ndarray:
    data = values.to_numpy(float)
    median = float(np.nanmedian(data))
    mad = float(np.nanmedian(np.abs(data - median)))
    scale = 1.4826 * mad
    if scale <= np.finfo(float).eps:
        q25, q75 = np.nanpercentile(data, [25, 75])
        scale = float((q75 - q25) / 1.349)
    if scale <= np.finfo(float).eps:
        scale = max(abs(median) * 0.05, np.finfo(float).eps)
    return np.clip((data - median) / scale, 0.0, 20.0)


def score_windows(features: pd.DataFrame, config: AnalysisConfig | None = None) -> pd.DataFrame:
    """Add per-feature robust z-scores and their weighted anomaly score."""

    config = config or AnalysisConfig()
    missing = set(SCORE_FEATURES) - set(features.columns)
    if missing:
        raise ValueError("Feature table missing: " + ", ".join(sorted(missing)))
    result = features.copy()
    weights = np.asarray(config.detector_weights, dtype=float)
    weights /= weights.sum()
    score_parts: list[np.ndarray] = []
    for name in SCORE_FEATURES:
        part = _robust_positive_z(np.log1p(result[name].clip(lower=0)))
        result[f"robust_z_{name}"] = part
        score_parts.append(part)
    result["event_score"] = np.average(np.vstack(score_parts), axis=0, weights=weights)
    result["is_anomaly"] = result["event_score"] >= config.detector_threshold
    return result


def _severity(score: float, threshold: float) -> str:
    if score < threshold * 1.5:
        return "LEVE"
    if score < threshold * 2.5:
        return "MEDIA"
    return "ALTA"


def detect_events(features: pd.DataFrame, config: AnalysisConfig | None = None) -> pd.DataFrame:
    """Score windows and merge temporally adjacent detections into physical events."""

    config = config or AnalysisConfig()
    columns = [
        "event_id", "timestamp", "seconds_elapsed", "event_score", "severity",
        "event_start", "event_end", "peak_acceleration", "rms", "std", "jerk_max", "energy",
    ]
    if len(features) < config.detector_min_baseline_windows:
        return pd.DataFrame(columns=columns)
    scored = score_windows(features, config)
    anomalies = scored[scored["is_anomaly"]].sort_values("seconds_elapsed")
    if anomalies.empty:
        return pd.DataFrame(columns=columns)

    boundaries = anomalies["window_start"].diff().fillna(0) > config.event_merge_seconds
    for column in ("signal_block", "gps_route_part"):
        if column in anomalies:
            boundaries |= anomalies[column].ne(anomalies[column].shift())
    groups = boundaries.cumsum()
    events: list[dict[str, object]] = []
    for event_number, (_, group) in enumerate(anomalies.groupby(groups), start=1):
        peak_row = group.loc[group["event_score"].idxmax()]
        events.append(
            {
                "event_id": f"EVT-{event_number:04d}",
                "timestamp": peak_row["timestamp"],
                "seconds_elapsed": float(peak_row["seconds_elapsed"]),
                "event_score": float(peak_row["event_score"]),
                "severity": _severity(float(peak_row["event_score"]), config.detector_threshold),
                "event_start": float(group["window_start"].min()),
                "event_end": float(group["window_end"].max()),
                "peak_acceleration": float(group["magnitude_max"].max()),
                "rms": float(group["rms"].max()),
                "std": float(group["std"].max()),
                "jerk_max": float(group["jerk_max"].max()),
                "energy": float(group["energy"].max()),
            }
        )
    return pd.DataFrame(events, columns=columns)

