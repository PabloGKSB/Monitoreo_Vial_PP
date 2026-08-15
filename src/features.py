"""Windowed time-domain vibration features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AnalysisConfig


FEATURE_DESCRIPTIONS: dict[str, str] = {
    "mean": "Mean smoothed dynamic acceleration in the window.",
    "std": "Standard deviation of smoothed dynamic acceleration.",
    "variance": "Variance of smoothed dynamic acceleration.",
    "min": "Minimum smoothed dynamic acceleration.",
    "max": "Maximum smoothed dynamic acceleration.",
    "peak_to_peak": "Window maximum minus minimum.",
    "rms": "Root mean square vibration amplitude.",
    "magnitude_max": "Maximum un-smoothed dynamic magnitude.",
    "magnitude_mean": "Mean un-smoothed dynamic magnitude.",
    "magnitude_std": "Standard deviation of un-smoothed dynamic magnitude.",
    "jerk_max": "Maximum absolute rate of acceleration change.",
    "jerk_rms": "Root mean square jerk.",
    "energy": "Mean squared smoothed dynamic acceleration.",
    "p90": "90th percentile of smoothed dynamic acceleration.",
    "p95": "95th percentile of smoothed dynamic acceleration.",
    "crest_factor": "Peak-to-RMS ratio, a measure of impulsiveness.",
}


def _window_features(window: pd.DataFrame, start: float, end: float) -> dict[str, object]:
    signal = window["smoothed_magnitude"].to_numpy(float)
    magnitude = window["dynamic_magnitude"].to_numpy(float)
    jerk = window["jerk"].to_numpy(float)
    rms = float(np.sqrt(np.mean(np.square(signal))))
    peak = float(np.max(np.abs(signal)))
    center_index = len(window) // 2
    result: dict[str, object] = {
        "window_start": start,
        "window_end": end,
        "seconds_elapsed": float(window["seconds_elapsed"].iloc[center_index]),
        "timestamp": window["timestamp"].iloc[center_index] if "timestamp" in window else pd.NaT,
        "sample_count": len(window),
        "mean": float(np.mean(signal)),
        "std": float(np.std(signal)),
        "variance": float(np.var(signal)),
        "min": float(np.min(signal)),
        "max": float(np.max(signal)),
        "peak_to_peak": float(np.ptp(signal)),
        "rms": rms,
        "magnitude_max": float(np.max(magnitude)),
        "magnitude_mean": float(np.mean(magnitude)),
        "magnitude_std": float(np.std(magnitude)),
        "jerk_max": float(np.max(np.abs(jerk))),
        "jerk_rms": float(np.sqrt(np.mean(np.square(jerk)))),
        "energy": float(np.mean(np.square(signal))),
        "p75": float(np.percentile(signal, 75)),
        "p90": float(np.percentile(signal, 90)),
        "p95": float(np.percentile(signal, 95)),
        "crest_factor": peak / rms if rms > np.finfo(float).eps else 0.0,
    }
    return result


def extract_window_features(
    processed: pd.DataFrame, config: AnalysisConfig | None = None
) -> pd.DataFrame:
    """Extract configurable overlapping windows using elapsed time boundaries."""

    config = config or AnalysisConfig()
    if processed.empty:
        return pd.DataFrame()
    step = config.window_seconds * (1.0 - config.window_overlap)
    first = float(processed["seconds_elapsed"].min())
    last = float(processed["seconds_elapsed"].max())
    starts = np.arange(first, max(first, last - config.window_seconds) + step * 0.5, step)
    rows: list[dict[str, object]] = []
    elapsed = processed["seconds_elapsed"]
    for start in starts:
        end = start + config.window_seconds
        window = processed[(elapsed >= start) & (elapsed < end)]
        if len(window) >= config.minimum_samples_per_window:
            rows.append(_window_features(window, float(start), float(end)))
    return pd.DataFrame(rows)

