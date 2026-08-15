"""Safe, tolerant loading of smartphone sensor ZIP archives."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

import pandas as pd

from .utils import elapsed_to_timestamp, normalize_name

LOGGER = logging.getLogger(__name__)

SENSOR_ALIASES: dict[str, tuple[str, ...]] = {
    "accelerometer": ("accelerometer", "acceleration", "linearacceleration"),
    "total_acceleration": ("totalacceleration", "accelerometertotal"),
    "accelerometer_uncalibrated": ("accelerometeruncalibrated", "uncalibratedaccelerometer"),
    "gyroscope": ("gyroscope", "gyro"),
    "gyroscope_uncalibrated": ("gyroscopeuncalibrated", "uncalibratedgyroscope"),
    "gps": ("location", "gps", "geolocation", "position"),
    "orientation": ("orientation", "rotationvector"),
    "compass": ("compass", "magnetometer", "magneticfield"),
    "metadata": ("metadata", "deviceinfo"),
    "annotation": ("annotation", "annotations", "labels"),
}

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "accelerometer": {"seconds_elapsed", "x", "y", "z"},
    "total_acceleration": {"seconds_elapsed", "x", "y", "z"},
    "accelerometer_uncalibrated": {"seconds_elapsed", "x", "y", "z"},
    "gyroscope": {"seconds_elapsed", "x", "y", "z"},
    "gyroscope_uncalibrated": {"seconds_elapsed", "x", "y", "z"},
    "gps": {"seconds_elapsed", "latitude", "longitude"},
}

COLUMN_ALIASES: dict[str, str] = {
    "time": "time",
    "timestamp": "time",
    "epochtime": "time",
    "secondselapsed": "seconds_elapsed",
    "elapsedseconds": "seconds_elapsed",
    "elapsedtime": "seconds_elapsed",
    "latitude": "latitude",
    "lat": "latitude",
    "longitude": "longitude",
    "lon": "longitude",
    "lng": "longitude",
    "horizontalaccuracy": "horizontal_accuracy",
    "accuracy": "horizontal_accuracy",
    "speed": "speed",
    "velocity": "speed",
    "x": "x",
    "y": "y",
    "z": "z",
}


class TripLoadError(RuntimeError):
    """Raised when a trip archive cannot provide the minimum usable data."""


@dataclass(slots=True)
class TripData:
    """In-memory sensor frames from one immutable source archive."""

    trip_id: str
    source_path: Path
    sensors: dict[str, pd.DataFrame]
    source_files: dict[str, str]
    warnings: list[str] = field(default_factory=list)

    @property
    def available_sensors(self) -> tuple[str, ...]:
        return tuple(sorted(self.sensors))

    def require_minimum_sensors(self) -> None:
        missing = {"accelerometer", "gps"} - self.sensors.keys()
        if missing:
            raise TripLoadError(
                "Trip requires accelerometer + GPS; missing: " + ", ".join(sorted(missing))
            )


def _sensor_for_filename(filename: str) -> str | None:
    stem = normalize_name(PurePosixPath(filename).stem)
    # Specific variants must win over their shorter base names.
    for sensor in sorted(SENSOR_ALIASES, key=len, reverse=True):
        if any(stem == alias or stem.startswith(alias) for alias in SENSOR_ALIASES[sensor]):
            return sensor
    return None


def _normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    rename: dict[str, str] = {}
    used: set[str] = set()
    for original in frame.columns:
        normalized = normalize_name(str(original).lstrip("\ufeff"))
        canonical = COLUMN_ALIASES.get(normalized, normalized)
        if canonical in used:
            canonical = f"{canonical}_{len(used)}"
        rename[original] = canonical
        used.add(canonical)
    return frame.rename(columns=rename)


def _prepare_frame(sensor: str, frame: pd.DataFrame) -> pd.DataFrame:
    frame = _normalize_columns(frame)
    if frame.empty:
        return frame
    if "seconds_elapsed" not in frame and "time" in frame:
        epoch = pd.to_numeric(frame["time"], errors="coerce")
        scale = 1e9 if epoch.dropna().median() > 1e15 else 1e3
        frame["seconds_elapsed"] = (epoch - epoch.min()) / scale
    numeric_candidates = REQUIRED_COLUMNS.get(sensor, set()) | {
        "time", "speed", "horizontal_accuracy", "latitude", "longitude"
    }
    for column in numeric_candidates & set(frame.columns):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "seconds_elapsed" in frame:
        frame = frame.dropna(subset=["seconds_elapsed"]).sort_values("seconds_elapsed")
        frame = frame.drop_duplicates(subset=["seconds_elapsed"], keep="first").reset_index(drop=True)
        frame["timestamp"] = elapsed_to_timestamp(frame["seconds_elapsed"], frame.get("time"))
    required = REQUIRED_COLUMNS.get(sensor, set())
    missing = required - set(frame.columns)
    if missing and not frame.empty:
        raise TripLoadError(f"{sensor} is missing columns: {', '.join(sorted(missing))}")
    return frame


def _apply_recording_clock(sensors: dict[str, pd.DataFrame], warnings: list[str]) -> None:
    """Anchor elapsed time to the local recording clock declared by metadata."""

    metadata = sensors.get("metadata")
    if metadata is None or metadata.empty:
        return
    row = metadata.iloc[0]
    recording_time = row.get("recordingtime")
    timezone = row.get("recordingtimezone")
    if pd.isna(recording_time) or pd.isna(timezone):
        return
    try:
        parsed = datetime.strptime(str(recording_time), "%Y-%m-%d_%H-%M-%S")
        local_start = pd.Timestamp(parsed).tz_localize(str(timezone))
    except (TypeError, ValueError, KeyError) as exc:
        warnings.append(f"Could not apply metadata recording clock: {exc}")
        return
    for frame in sensors.values():
        if "seconds_elapsed" in frame:
            frame["timestamp"] = local_start + pd.to_timedelta(frame["seconds_elapsed"], unit="s")


def load_trip(zip_path: str | Path, *, require_minimum: bool = True) -> TripData:
    """Load recognized CSV files directly from a ZIP without altering raw data."""

    path = Path(zip_path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise TripLoadError(f"ZIP archive not found: {path}")

    sensors: dict[str, pd.DataFrame] = {}
    source_files: dict[str, str] = {}
    warnings: list[str] = []
    try:
        with ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir() or PurePosixPath(info.filename).suffix.lower() != ".csv":
                    continue
                sensor = _sensor_for_filename(info.filename)
                if sensor is None:
                    warnings.append(f"Unrecognized CSV ignored: {info.filename}")
                    continue
                if sensor in sensors:
                    warnings.append(f"Duplicate {sensor} ignored: {info.filename}")
                    continue
                if info.file_size == 0:
                    warnings.append(f"Empty {sensor} file: {info.filename}")
                    continue
                try:
                    payload = archive.read(info)
                    frame = pd.read_csv(io.BytesIO(payload), low_memory=False)
                    sensors[sensor] = _prepare_frame(sensor, frame)
                    source_files[sensor] = info.filename
                except (UnicodeDecodeError, pd.errors.ParserError, TripLoadError) as exc:
                    if sensor in {"accelerometer", "gps"}:
                        raise TripLoadError(f"Invalid required sensor {info.filename}: {exc}") from exc
                    warnings.append(f"Could not load optional {info.filename}: {exc}")
    except BadZipFile as exc:
        raise TripLoadError(f"Invalid ZIP archive: {path.name}") from exc

    _apply_recording_clock(sensors, warnings)
    trip = TripData(path.stem, path, sensors, source_files, warnings)
    if require_minimum:
        trip.require_minimum_sensors()
    LOGGER.info("Loaded %s with sensors: %s", trip.trip_id, ", ".join(trip.available_sensors))
    return trip


def discover_trip_archives(*directories: str | Path) -> list[Path]:
    """Return unique trip ZIPs from canonical and optional legacy directories."""

    discovered: dict[Path, Path] = {}
    for directory in directories:
        root = Path(directory)
        if root.is_dir():
            for path in root.glob("*.zip"):
                discovered[path.resolve()] = path.resolve()
    return sorted(discovered.values(), key=lambda item: item.name.lower())
