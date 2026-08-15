from zipfile import ZipFile

import numpy as np
import pandas as pd

from src.analyzer import TripAnalyzer
from src.annotations import compare_annotations
from src.config import AnalysisConfig


def _trip_zip(path):
    rng = np.random.default_rng(7)
    elapsed = np.arange(0, 12, 0.02)
    z = rng.normal(0, 0.05, len(elapsed))
    z[np.abs(elapsed - 6) < 0.06] += 6
    accel = pd.DataFrame({
        "time": 1_767_225_600_000_000_000 + (elapsed * 1e9).astype(int),
        "seconds_elapsed": elapsed, "x": rng.normal(0, .05, len(elapsed)),
        "y": rng.normal(0, .05, len(elapsed)), "z": z,
    })
    gps_elapsed = np.arange(0, 13, 1.0)
    gps = pd.DataFrame({
        "seconds_elapsed": gps_elapsed, "latitude": -38.7 + gps_elapsed * 0.00005,
        "longitude": -72.6, "speed": 5.0, "horizontalAccuracy": 6.0,
    })
    with ZipFile(path, "w") as archive:
        archive.writestr("Accelerometer.csv", accel.to_csv(index=False))
        archive.writestr("Location.csv", gps.to_csv(index=False))


def test_analyzer_end_to_end_and_export(tmp_path):
    path = tmp_path / "synthetic_trip.zip"
    _trip_zip(path)
    analyzer = TripAnalyzer(AnalysisConfig(detector_threshold=2.5))
    result = analyzer.analyze(path)
    outputs = analyzer.export(result, tmp_path / "outputs")
    assert result.summary["distance_km"] > 0
    assert len(result.segments) > 0
    assert result.events.iloc[0]["gps_status"] == "OK"
    assert all(output.exists() for output in outputs.values())


def test_manual_annotation_matches_nearby_event():
    annotations = pd.DataFrame({"seconds_elapsed": [10.0], "label": ["BACHE"]})
    events = pd.DataFrame({"seconds_elapsed": [12.0], "event_id": ["EVT-0001"]})
    compared = compare_annotations(annotations, events, AnalysisConfig(annotation_tolerance_seconds=5))
    assert compared.iloc[0]["match_status"] == "MATCHED"
    assert compared.iloc[0]["event_id"] == "EVT-0001"
