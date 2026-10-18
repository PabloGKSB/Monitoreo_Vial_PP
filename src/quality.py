"""Sensor timing, continuity and GPS quality assessment."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum

import numpy as np
import pandas as pd

from .config import AnalysisConfig
from .loader import TripData


class QualityStatus(StrEnum):
    OK = "OK"
    WARNING = "WARNING"
    INVALID = "INVALID"


@dataclass(slots=True)
class DataGap:
    start_seconds: float
    end_seconds: float
    duration_seconds: float


@dataclass(slots=True)
class SensorQuality:
    sensor: str
    status: QualityStatus
    record_count: int
    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float | None = None
    sampling_hz: float | None = None
    gaps: list[DataGap] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    metrics: dict[str, float | int | None] = field(default_factory=dict)


@dataclass(slots=True)
class QualityReport:
    overall_status: QualityStatus
    sensors: dict[str, SensorQuality]
    start_timestamp: pd.Timestamp | None
    end_timestamp: pd.Timestamp | None
    duration_seconds: float
    summary: str

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["overall_status"] = self.overall_status.value
        result["start_timestamp"] = self.start_timestamp.isoformat() if self.start_timestamp else None
        result["end_timestamp"] = self.end_timestamp.isoformat() if self.end_timestamp else None
        for sensor in result["sensors"].values():
            sensor["status"] = sensor["status"].value
        return result


def _finite_float(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def assess_sensor(sensor: str, frame: pd.DataFrame, config: AnalysisConfig) -> SensorQuality:
    """Measure actual sampling and gaps without assuming a nominal frequency."""

    count = len(frame)
    if count == 0 or "seconds_elapsed" not in frame:
        return SensorQuality(sensor, QualityStatus.INVALID, count, issues=["No timed records"])

    times = pd.to_numeric(frame["seconds_elapsed"], errors="coerce")
    elapsed = times[np.isfinite(times)].to_numpy(float)
    if elapsed.size < 2:
        return SensorQuality(sensor, QualityStatus.INVALID, count, issues=["Fewer than two timed records"])
    deltas = np.diff(elapsed)
    if np.any(deltas <= 0):
        return SensorQuality(sensor, QualityStatus.INVALID, count, issues=["Non-increasing timestamps"])
    positive = deltas[deltas > 0]
    if positive.size == 0:
        return SensorQuality(sensor, QualityStatus.INVALID, count, issues=["Timestamps do not advance"])

    median_delta = float(np.median(positive))
    sampling_hz = 1.0 / median_delta
    gap_threshold = max(config.minimum_gap_seconds, config.gap_factor * median_delta)
    gap_indexes = np.flatnonzero(deltas > gap_threshold)
    gaps = [
        DataGap(float(elapsed[i]), float(elapsed[i + 1]), float(deltas[i])) for i in gap_indexes
    ]
    issues: list[str] = []
    status = QualityStatus.OK
    if gaps:
        status = QualityStatus.WARNING
        issues.append(f"{len(gaps)} data gap(s) detected")
    irregular_ratio = float(np.mean(np.abs(positive - median_delta) > median_delta * 0.5))
    if irregular_ratio > 0.1:
        status = QualityStatus.WARNING
        issues.append("Irregular sampling intervals")
    if len(elapsed) != count:
        status = QualityStatus.WARNING
        issues.append("Non-finite timestamps excluded")

    result = SensorQuality(
        sensor=sensor,
        status=status,
        record_count=count,
        start_seconds=float(elapsed[0]),
        end_seconds=float(elapsed[-1]),
        duration_seconds=float(elapsed[-1] - elapsed[0]),
        sampling_hz=sampling_hz,
        gaps=gaps,
        issues=issues,
        metrics={"median_interval_seconds": median_delta, "irregular_interval_ratio": irregular_ratio},
    )
    if sensor == "gps":
        _assess_gps(frame, result)
    if sensor == "accelerometer" and {"x", "y", "z"} <= set(frame):
        axes = frame[["x", "y", "z"]].apply(pd.to_numeric, errors="coerce")
        usable = np.isfinite(axes.to_numpy(float)).all(axis=1) & np.isfinite(times)
        result.metrics["unusable_signal_records"] = int((~usable).sum())
        if not usable.all():
            result.status = QualityStatus.WARNING
            result.issues.append("Non-finite acceleration records excluded")
        if usable.sum() < 2 or (~usable).sum() * 2 >= count:
            result.status = QualityStatus.INVALID
            result.issues.append("Insufficient usable acceleration records")
    return result


def _assess_gps(frame: pd.DataFrame, result: SensorQuality) -> None:
    lat = pd.to_numeric(frame.get("latitude"), errors="coerce")
    lon = pd.to_numeric(frame.get("longitude"), errors="coerce")
    missing = int((lat.isna() | lon.isna()).sum())
    present = lat.notna() & lon.notna()
    invalid = int((present & (~lat.between(-90, 90) | ~lon.between(-180, 180))).sum())
    accuracy = pd.to_numeric(
        frame.get("horizontal_accuracy", pd.Series(np.nan, index=frame.index)), errors="coerce"
    )
    speed = pd.to_numeric(frame.get("speed", pd.Series(np.nan, index=frame.index)), errors="coerce")
    result.metrics.update(
        {
            "missing_coordinates": missing,
            "invalid_coordinates": invalid,
            "median_horizontal_accuracy_m": _finite_float(float(accuracy.median())),
            "p95_horizontal_accuracy_m": _finite_float(float(accuracy.quantile(0.95))),
            "mean_speed_mps": _finite_float(float(speed.mean())),
            "negative_speed_records": int((speed < 0).fillna(False).sum()),
        }
    )
    if missing or invalid:
        result.status = QualityStatus.WARNING
        result.issues.append(f"{missing + invalid} missing or invalid coordinate record(s)")
    if (missing + invalid) * 2 >= len(frame):
        result.status = QualityStatus.INVALID
        result.issues.append("At least half of GPS coordinates are unusable")


def assess_trip(trip: TripData, config: AnalysisConfig | None = None) -> QualityReport:
    """Assess every available sensor and determine minimum trip usability."""

    config = config or AnalysisConfig()
    sensors = {
        name: assess_sensor(name, frame, config)
        for name, frame in trip.sensors.items()
        if name not in {"metadata", "annotation"}
    }
    required = [sensors.get("accelerometer"), sensors.get("gps")]
    if any(item is None or item.status == QualityStatus.INVALID for item in required):
        overall = QualityStatus.INVALID
        summary = "TRIP INVALID: accelerometer and GPS are required"
    elif any(item.status != QualityStatus.OK for item in sensors.values()):
        overall = QualityStatus.WARNING
        summary = "TRIP USABLE WITH WARNINGS"
    else:
        overall = QualityStatus.OK
        summary = "TRIP USABLE"

    if trip.metadata and (trip.metadata.get("queue_dropped", 0)
                          or trip.metadata.get("quality_warnings")
                          or trip.metadata.get("state") != "COMPLETED"
                          or trip.metadata.get("error")
                          or trip.metadata.get("pending_unwritten", 0)):
        if overall == QualityStatus.OK:
            overall = QualityStatus.WARNING
            summary = "TRIP USABLE WITH CAPTURE WARNINGS"

    timestamps = [
        value
        for frame in trip.sensors.values()
        if "timestamp" in frame
        for value in (frame["timestamp"].min(), frame["timestamp"].max())
        if pd.notna(value)
    ]
    elapsed_ends = [
        float(frame["seconds_elapsed"].max())
        for frame in trip.sensors.values()
        if "seconds_elapsed" in frame and not frame.empty
    ]
    elapsed_starts = [
        float(frame["seconds_elapsed"].min())
        for frame in trip.sensors.values()
        if "seconds_elapsed" in frame and not frame.empty
    ]
    return QualityReport(
        overall_status=overall,
        sensors=sensors,
        start_timestamp=min(timestamps) if timestamps else None,
        end_timestamp=max(timestamps) if timestamps else None,
        duration_seconds=max(elapsed_ends) - min(elapsed_starts) if elapsed_ends else 0.0,
        summary=summary,
    )
