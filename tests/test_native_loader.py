import json
from zipfile import ZipFile

import pandas as pd
import pytest

from src.analyzer import TripAnalyzer
from src.gps import prepare_gps
from src.loader import TripLoadError, load_trip
from src.maps import build_trip_map


def native_archive(tmp_path, version="capture-preview-2", bad_clock=False, duplicate=False):
    path = tmp_path / "native.zip"
    epoch, origin = 1790614908223, 242845907135600
    metadata = {"schema_version": version, "origin_monotonic_ns": str(origin),
                "origin_epoch_ms": epoch, "annotation_origin_monotonic_ms": 242845754,
                "annotations_file": "test_anotaciones.csv", "state": "COMPLETED",
                "queue_dropped": 2}
    elapsed = [0, 1, 75, 76]
    clock = {"sensor_timestamp_ns": [origin + t * 10**9 for t in elapsed],
             "epoch_ms_derived": [epoch + t * 1000 for t in elapsed],
             "seconds_elapsed": elapsed}
    if bad_clock:
        clock["epoch_ms_derived"][0] += 1
    if duplicate:
        for values in clock.values():
            values[1] = values[0]
    with ZipFile(path, "w") as archive:
        archive.writestr("session/metadata.json", json.dumps(metadata))
        for filename, values in {
            "accelerometer.csv": {"x": [0]*4, "y": [0]*4, "z": [9.8]*4},
            "linear_acceleration.csv": {"x": [0]*4, "y": [0]*4, "z": [0.1]*4},
            "gps.csv": {"latitude": [-38.7, -38.7001, -38.71, -38.7101],
                        "longitude": [-72.6]*4, "speed_mps": [1, None, 2, 3],
                        "horizontal_accuracy_m": [4]*4, "location_epoch_ms": [epoch]*4},
        }.items():
            archive.writestr("session/" + filename, pd.DataFrame({**clock, **values}).to_csv(index=False))
        annotations = pd.DataFrame({"trip_id": ["test"], "timestamp": ["local text"],
                                    "epoch_ms": [epoch + 1000], "elapsed_ms": [1000],
                                    "event_type": ["OTRO"]})
        archive.writestr("session/test_anotaciones.csv", annotations.to_csv(index=False))
    return path


def test_native_streams_clocks_and_optional_gps(tmp_path):
    trip = load_trip(native_archive(tmp_path))
    assert trip.trip_id == "test"
    assert trip.sensors["accelerometer"].z.iloc[0] == 0.1
    assert trip.sensors["total_acceleration"].z.iloc[0] == 9.8
    assert trip.sensors["gps"].timestamp.iloc[0] == pd.Timestamp("2026-09-28T17:01:48.223Z")
    assert trip.sensors["gps"].sensor_timestamp_ns.dtype == "int64"
    assert trip.sensors["gps"].speed.isna().sum() == 1
    assert trip.sensors["gps"].horizontal_accuracy.iloc[0] == 4
    assert "location_epoch_ms" in trip.sensors["gps"]
    assert trip.sensors["annotation"].seconds_elapsed.iloc[0] == pytest.approx(0.8468644)
    assert trip.sensors["annotation"].event_type.iloc[0] == "OTRO"
    assert any("cola llena" in w for w in trip.warnings)


@pytest.mark.parametrize("kwargs,match", [
    ({"version": "future-3"}, "Unsupported"),
    ({"bad_clock": True}, "Epoch clock mismatch"),
    ({"duplicate": True}, "Non-increasing"),
])
def test_native_rejects_invalid_profiles(tmp_path, kwargs, match):
    with pytest.raises(TripLoadError, match=match):
        load_trip(native_archive(tmp_path, **kwargs))


def test_native_inspection_and_map_do_not_bridge_gap(tmp_path):
    result = TripAnalyzer().analyze(native_archive(tmp_path))
    gps = prepare_gps(result.trip.sensors["gps"])
    assert gps.route_part.tolist() == [0, 0, 1, 1]
    assert gps.step_distance_m.iloc[2] == 0
    assert 20 < gps.route_distance_m.iloc[-1] < 25
    assert result.summary["analysis_mode"] == "native_inspection"
    assert result.events.empty and result.segments.empty
    html = build_trip_map(result).get_root().render()
    assert html.count("L.polyline(") == 2
    assert "Inicio GPS" in html and "Fin GPS" in html
    assert result.summary["quality_status"] == "WARNING"


def test_native_without_manifest_rejected(tmp_path):
    path = tmp_path / "missing.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("linear_acceleration.csv", "seconds_elapsed,x,y,z\n0,0,0,0\n")
    with pytest.raises(TripLoadError, match="requires metadata.json"):
        load_trip(path)
