"""Manual annotation loading and nearest-event comparison."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import AnalysisConfig
from .utils import normalize_name


def load_annotations(path: str | Path, trip_start: pd.Timestamp | None = None) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame = frame.rename(columns={column: normalize_name(column) for column in frame.columns})
    if "secondselapsed" in frame:
        frame["seconds_elapsed"] = pd.to_numeric(frame["secondselapsed"], errors="coerce")
    elif "timestamp" in frame and trip_start is not None:
        timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        frame["seconds_elapsed"] = (timestamps - trip_start).dt.total_seconds()
    else:
        raise ValueError("Annotations require seconds_elapsed or timestamp with a trip start")
    if "label" not in frame:
        raise ValueError("Annotations require a label column")
    return frame.dropna(subset=["seconds_elapsed", "label"]).reset_index(drop=True)


def compare_annotations(
    annotations: pd.DataFrame, events: pd.DataFrame, config: AnalysisConfig | None = None
) -> pd.DataFrame:
    config = config or AnalysisConfig()
    result = annotations.copy()
    if events.empty:
        result["event_id"] = None
        result["time_difference_s"] = np.nan
        result["match_status"] = "NO_DETECTION"
        return result
    event_times = events["seconds_elapsed"].to_numpy(float)
    indexes = [int(np.argmin(np.abs(event_times - value))) for value in result["seconds_elapsed"]]
    differences = np.array([abs(event_times[i] - value) for i, value in zip(indexes, result["seconds_elapsed"])])
    matched = differences <= config.annotation_tolerance_seconds
    result["event_id"] = [events.iloc[i]["event_id"] if ok else None for i, ok in zip(indexes, matched)]
    result["time_difference_s"] = differences
    result["match_status"] = np.where(matched, "MATCHED", "NO_DETECTION")
    return result

