"""Absolute-clock ingestion and window features for paired pilot recordings."""

from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

from src.gps import prepare_gps
from src.loader import load_trip

SIGNALS = {"accelerometer": "acc", "total_acceleration": "total", "gyroscope": "gyro"}
MARKERS = {"MONITOREO_INICIO", "MONITOREO_FIN"}


@dataclass(frozen=True)
class PilotConfig:
    window_seconds: float = 1.5
    fixed_delay_seconds: float = 1.5
    search_before_seconds: float = 3.0
    search_after_seconds: float = 1.0
    normal_exclusion_seconds: float = 8.0
    normal_ratio: int = 3
    max_gap_seconds: float = 0.1
    minimum_coverage: float = 0.8
    gps_tolerance_seconds: float = 2.0
    spatial_purge_meters: float = 50.0
    seed: int = 42
    forest_trees: int = 200
    forest_min_leaf: int = 2

    def __post_init__(self):
        numeric = [self.window_seconds, self.max_gap_seconds, self.gps_tolerance_seconds,
                   self.normal_exclusion_seconds, self.spatial_purge_meters]
        if not all(np.isfinite(x) and x > 0 for x in numeric):
            raise ValueError("Durations and spatial radius must be finite and positive")
        if not 0 < self.minimum_coverage <= 1 or self.normal_ratio < 1:
            raise ValueError("Invalid coverage or normal ratio")
        if self.fixed_delay_seconds < 0 or min(self.search_before_seconds, self.search_after_seconds) < 0:
            raise ValueError("Delays must be nonnegative")


@dataclass
class PilotTrip:
    route_id: str
    origin: pd.Timestamp
    signals: dict[str, pd.DataFrame]
    gps: pd.DataFrame
    annotations: pd.DataFrame
    audit: dict


def read_annotations(path: Path, origin: pd.Timestamp) -> pd.DataFrame:
    """Use Anotador epoch_ms, never its naive text or session-relative elapsed_ms."""
    frame = pd.read_csv(path)
    if not {"epoch_ms", "event_type"}.issubset(frame):
        raise ValueError(f"{path.name}: epoch_ms and event_type required")
    epoch = pd.to_numeric(frame["epoch_ms"], errors="coerce")
    if epoch.isna().any() or not np.isfinite(epoch).all() or (epoch % 1 != 0).any():
        raise ValueError(f"{path.name}: invalid epoch_ms")
    if frame["event_type"].isna().any():
        raise ValueError(f"{path.name}: missing event_type")
    frame["annotation_id"] = [f"A{i + 1:03d}" for i in range(len(frame))]
    frame["event_type"] = frame["event_type"].str.strip().str.upper()
    frame["timestamp_utc"] = pd.to_datetime(epoch.astype("int64"), unit="ms", utc=True)
    frame["seconds_elapsed"] = (frame["timestamp_utc"] - origin).dt.total_seconds()
    starts = frame.loc[frame.event_type == "MONITOREO_INICIO", "seconds_elapsed"]
    ends = frame.loc[frame.event_type == "MONITOREO_FIN", "seconds_elapsed"]
    if len(starts) != 1 or len(ends) != 1 or starts.iloc[0] >= ends.iloc[0]:
        raise ValueError("Annotations require one ordered monitoring start/end pair")
    if not frame.seconds_elapsed.between(starts.iloc[0], ends.iloc[0]).all():
        raise ValueError("Annotation outside monitoring session")
    return frame.sort_values("seconds_elapsed").reset_index(drop=True)


def load_pilot_trip(zip_path: Path, annotation_path: Path, route_id: str) -> PilotTrip:
    trip = load_trip(zip_path)
    acc = trip.sensors["accelerometer"]
    if "time" not in acc or acc["time"].isna().any():
        raise ValueError("Pilot requires an absolute accelerometer clock")
    metadata = trip.sensors.get("metadata", pd.DataFrame())
    metadata_epoch = (pd.to_numeric(metadata.iloc[0].get("recordingepochtime"), errors="coerce")
                      if not metadata.empty else np.nan)
    origin = (pd.to_datetime(metadata_epoch, unit="ms", utc=True) if pd.notna(metadata_epoch)
              else acc["timestamp"].iloc[0] - pd.to_timedelta(acc["seconds_elapsed"].iloc[0], unit="s"))
    sensors, timing = {}, {}
    for name, frame in trip.sensors.items():
        if "time" not in frame or len(frame) < 2:
            continue
        frame = frame.copy()
        frame["seconds_elapsed"] = (frame["timestamp"] - origin).dt.total_seconds()
        t = frame["seconds_elapsed"].to_numpy(float)
        dt = np.diff(t)
        if not np.isfinite(t).all() or (dt <= 0).any():
            raise ValueError(f"{route_id}/{name}: nonmonotonic absolute clock")
        sensors[name] = frame
        timing[name] = {
            "records": len(frame), "median_hz": float(1 / np.median(dt)),
            "effective_hz": float((len(frame) - 1) / (t[-1] - t[0])),
            "max_interval_seconds": float(dt.max()), "intervals_over_100ms": int((dt > .1).sum()),
            "start_seconds": float(t[0]), "end_seconds": float(t[-1]),
        }
    if not set(SIGNALS).issubset(sensors) or "gps" not in sensors:
        raise ValueError("Pilot feature schema requires accelerometer, total acceleration, gyro and GPS")
    annotations = read_annotations(annotation_path, origin)
    gps = prepare_gps(sensors["gps"])
    if gps.empty:
        raise ValueError(f"{route_id}: no valid GPS coordinates")
    raw_checks = {}
    with ZipFile(zip_path) as archive:
        for name in (*SIGNALS, "gps"):
            raw = pd.read_csv(io.BytesIO(archive.read(trip.source_files[name])))
            clock = pd.to_numeric(raw["time"], errors="coerce")
            raw_checks[name] = {"records": len(raw), "missing_epoch": int(clock.isna().sum()),
                                "duplicate_epoch": int(clock.duplicated().sum()),
                                "backward_epoch": int((clock.diff() < 0).sum())}
    audit = {
        "route_id": route_id, "origin_utc": origin.isoformat(),
        "origin_santiago": origin.tz_convert("America/Santiago").isoformat(),
        "duration_seconds": timing["accelerometer"]["end_seconds"] - timing["accelerometer"]["start_seconds"],
        "distance_km": float(gps["route_distance_m"].max() / 1000),
        "gps_accuracy_median": (float(gps["horizontal_accuracy"].median())
                                if "horizontal_accuracy" in gps and gps.horizontal_accuracy.notna().any() else None),
        "sensors": timing, "warnings": trip.warnings,
        "annotation_counts": {str(k): int(v) for k, v in annotations["event_type"].value_counts().items()},
        "annotation_start_offset_seconds": float(annotations["seconds_elapsed"].min()),
        "annotation_end_offset_seconds": float(annotations["seconds_elapsed"].max()),
        "clock_policy": "absolute epoch; metadata text never overrides epoch",
        "timing_audit_stage": "intervals after loader normalization; raw counts in raw_checks",
        "raw_checks": raw_checks,
    }
    return PilotTrip(route_id, origin, sensors, gps, annotations, audit)


def summarize_signal(values: np.ndarray, times: np.ndarray) -> dict[str, float]:
    """Population statistics and finite-difference jerk on native samples."""
    jerk = np.diff(values) / np.diff(times)
    return {
        "mean": float(values.mean()), "min": float(values.min()), "max": float(values.max()),
        "absmax": float(np.abs(values).max()), "range": float(np.ptp(values)),
        "std": float(values.std()), "rms": float(np.sqrt(np.mean(values ** 2))),
        "p95": float(np.percentile(values, 95)), "energy": float(np.mean(values ** 2)),
        "jerk_absmax": float(np.abs(jerk).max()),
        "jerk_rms": float(np.sqrt(np.mean(jerk ** 2))),
        "jerk_abs_p95": float(np.percentile(np.abs(jerk), 95)),
    }


def window_features(trip: PilotTrip, center: float, config: PilotConfig) -> dict[str, float] | None:
    """Reject incomplete/gappy windows; use a shared absolute-clock interval."""
    start, end = center - config.window_seconds / 2, center + config.window_seconds / 2
    features = {}
    for sensor, prefix in SIGNALS.items():
        frame = trip.signals[sensor]
        t = frame["seconds_elapsed"].to_numpy(float)
        lo, hi = np.searchsorted(t, [start, end])
        if start < t[0] or end > t[-1] or hi - lo < 5:
            return None
        times = t[lo:hi]
        median_dt = float(np.median(np.diff(t)))
        dt = np.diff(np.r_[start, times, end])
        if dt.max() > config.max_gap_seconds or len(times) < config.minimum_coverage * config.window_seconds / median_dt:
            return None
        xyz = frame.iloc[lo:hi][["x", "y", "z"]].to_numpy(float)
        if not np.isfinite(xyz).all():
            return None
        channels = {axis: xyz[:, i] for i, axis in enumerate("xyz")}
        channels["mag"] = np.linalg.norm(xyz, axis=1)
        for channel, values in channels.items():
            features.update({f"{prefix}_{channel}_{key}": value
                             for key, value in summarize_signal(values, times).items()})
    return features
