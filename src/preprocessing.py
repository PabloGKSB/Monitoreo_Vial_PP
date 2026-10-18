"""Orientation-independent accelerometer preprocessing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt

from .config import AnalysisConfig


@dataclass(frozen=True, slots=True)
class PreprocessingInfo:
    sampling_hz: float
    gravity_compensation: str
    median_raw_magnitude: float


def _sampling_frequency(elapsed: np.ndarray) -> float:
    deltas = np.diff(elapsed)
    positive = deltas[deltas > 0]
    if positive.size == 0:
        raise ValueError("Accelerometer timestamps do not advance")
    return float(1.0 / np.median(positive))


def _filter(values: np.ndarray, cutoff_hz: float, sampling_hz: float, kind: str) -> np.ndarray:
    nyquist = sampling_hz / 2.0
    normalized = min(cutoff_hz / nyquist, 0.99)
    if normalized <= 0 or len(values) < 16:
        return values.copy()
    sos = butter(2, normalized, btype=kind, output="sos")
    try:
        return sosfiltfilt(sos, values, axis=0)
    except ValueError:
        return values.copy()


def _preprocess_block(
    frame: pd.DataFrame, config: AnalysisConfig | None = None
) -> tuple[pd.DataFrame, PreprocessingInfo]:
    """Compute raw magnitude, dynamic magnitude, smoothing and jerk.

    A median magnitude between 6 and 13 m/s2 indicates that gravity is likely
    included. In that case a low-pass vector estimate is subtracted. Otherwise
    the input is treated as a phone-provided linear acceleration signal.
    """

    config = config or AnalysisConfig()
    required = {"seconds_elapsed", "x", "y", "z"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("Accelerometer missing columns: " + ", ".join(sorted(missing)))
    result = frame.copy()
    result = result.dropna(subset=list(required)).sort_values("seconds_elapsed").reset_index(drop=True)
    elapsed = result["seconds_elapsed"].to_numpy(float)
    axes = result[["x", "y", "z"]].to_numpy(float)
    sampling_hz = _sampling_frequency(elapsed)
    raw_magnitude = np.linalg.norm(axes, axis=1)
    median_magnitude = float(np.median(raw_magnitude))

    if 6.0 <= median_magnitude <= 13.0:
        gravity = _filter(axes, config.gravity_cutoff_hz, sampling_hz, "lowpass")
        dynamic_axes = axes - gravity
        gravity_method = "low-pass vector subtraction"
    else:
        dynamic_axes = axes.copy()
        gravity_method = "input treated as linear acceleration"

    dynamic_magnitude = np.linalg.norm(dynamic_axes, axis=1)
    smoothed = _filter(dynamic_magnitude, config.smoothing_cutoff_hz, sampling_hz, "lowpass")
    jerk = np.zeros_like(smoothed)
    valid_delta = np.diff(elapsed) > 0
    jerk[1:][valid_delta] = np.diff(smoothed)[valid_delta] / np.diff(elapsed)[valid_delta]

    result["magnitude"] = raw_magnitude
    result[["dynamic_x", "dynamic_y", "dynamic_z"]] = dynamic_axes
    result["dynamic_magnitude"] = dynamic_magnitude
    result["smoothed_magnitude"] = smoothed
    result["jerk"] = jerk
    return result, PreprocessingInfo(sampling_hz, gravity_method, median_magnitude)


def preprocess_accelerometer(
    frame: pd.DataFrame, config: AnalysisConfig | None = None
) -> tuple[pd.DataFrame, PreprocessingInfo]:
    """Filter independent continuous blocks; never fill missing samples."""
    config = config or AnalysisConfig()
    required = ["seconds_elapsed", "x", "y", "z"]
    missing = set(required) - set(frame)
    if missing:
        raise ValueError("Accelerometer missing columns: " + ", ".join(sorted(missing)))
    values = frame[required].apply(pd.to_numeric, errors="coerce")
    usable = np.isfinite(values.to_numpy(float)).all(axis=1)
    valid = frame.loc[usable].copy()
    valid[required] = values.loc[usable]
    if len(valid) < 2:
        return pd.DataFrame(), PreprocessingInfo(0.0, "no usable blocks", 0.0)
    times = valid.seconds_elapsed.to_numpy(float)
    delta = np.diff(times)
    if np.any(delta <= 0):
        raise ValueError("Accelerometer timestamps must be strictly increasing")
    limit = max(config.minimum_gap_seconds, config.gap_factor * float(np.median(delta)))
    positions = np.flatnonzero(usable)
    breaks = (delta > limit) | (np.diff(positions) > 1)
    valid["signal_block"] = np.r_[0, breaks.cumsum()]
    pieces, infos = [], []
    for block, rows in valid.groupby("signal_block", sort=True):
        if len(rows) < config.minimum_samples_per_window:
            continue
        processed, info = _preprocess_block(rows, config)
        processed["signal_block"] = int(block)
        pieces.append(processed)
        infos.append(info)
    if not pieces:
        return pd.DataFrame(), PreprocessingInfo(0.0, "no usable blocks", 0.0)
    methods = sorted({info.gravity_compensation for info in infos})
    return pd.concat(pieces, ignore_index=True), PreprocessingInfo(
        float(np.median([info.sampling_hz for info in infos])), "; ".join(methods),
        float(np.median([info.median_raw_magnitude for info in infos])))

