from __future__ import annotations

from zipfile import ZipFile

import pandas as pd
import pytest

from src.loader import TripLoadError, load_trip


def _write_csv(archive: ZipFile, name: str, frame: pd.DataFrame) -> None:
    archive.writestr(name, frame.to_csv(index=False))


def test_loader_detects_nested_and_optional_sensors(tmp_path):
    path = tmp_path / "trip.zip"
    accel = pd.DataFrame({"time": [1_700_000_000_000_000_000] * 2, "seconds_elapsed": [0, 0.01], "X": [0, 1], "Y": [0, 0], "Z": [9.8, 10]})
    gps = pd.DataFrame({"seconds_elapsed": [0, 1], "Latitude": [-38.7, -38.7001], "Longitude": [-72.6, -72.6001]})
    with ZipFile(path, "w") as archive:
        _write_csv(archive, "sensors/Accelerometer.csv", accel)
        _write_csv(archive, "sensors/Location.csv", gps)
        _write_csv(archive, "sensors/Gyro.csv", accel)
        _write_csv(archive, "Metadata.csv", pd.DataFrame({
            "recording time": ["2026-08-14_13-10-19"],
            "recording timezone": ["America/Santiago"],
        }))
        archive.writestr("Annotation.csv", "")
    trip = load_trip(path)
    assert {"accelerometer", "gps", "gyroscope"} <= set(trip.available_sensors)
    assert "timestamp" in trip.sensors["accelerometer"]
    assert str(trip.sensors["accelerometer"].iloc[0]["timestamp"]) == "2023-11-14 22:13:20+00:00"
    assert trip.sensors["gps"].iloc[0]["timestamp"] == pd.Timestamp("2026-08-14 17:10:19Z")
    assert any("Empty annotation" in warning for warning in trip.warnings)


def test_loader_requires_accelerometer_and_gps(tmp_path):
    path = tmp_path / "trip.zip"
    with ZipFile(path, "w") as archive:
        _write_csv(archive, "Accelerometer.csv", pd.DataFrame({"seconds_elapsed": [0, 1], "x": [0, 0], "y": [0, 0], "z": [0, 0]}))
    with pytest.raises(TripLoadError, match="missing: gps"):
        load_trip(path)
