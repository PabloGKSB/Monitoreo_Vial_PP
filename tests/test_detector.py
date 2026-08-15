import numpy as np
import pandas as pd

from src.config import AnalysisConfig
from src.detector import detect_events
from src.features import extract_window_features
from src.preprocessing import preprocess_accelerometer


def _synthetic_acceleration(with_impact: bool) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    elapsed = np.arange(0, 20, 0.01)
    x = rng.normal(0, 0.08, len(elapsed))
    y = rng.normal(0, 0.08, len(elapsed))
    z = 9.81 + rng.normal(0, 0.08, len(elapsed))
    if with_impact:
        impact = np.abs(elapsed - 10.0) < 0.04
        z[impact] += 8.0 * np.hanning(impact.sum())
    return pd.DataFrame({
        "seconds_elapsed": elapsed,
        "timestamp": pd.Timestamp("2026-01-01", tz="UTC") + pd.to_timedelta(elapsed, unit="s"),
        "x": x, "y": y, "z": z,
    })


def test_gravity_is_compensated_when_present():
    processed, info = preprocess_accelerometer(_synthetic_acceleration(False))
    assert info.gravity_compensation == "low-pass vector subtraction"
    assert processed["dynamic_magnitude"].median() < 0.5
    assert processed["jerk"].notna().all()


def test_detector_finds_and_merges_artificial_impact():
    config = AnalysisConfig(detector_threshold=3.0)
    processed, _ = preprocess_accelerometer(_synthetic_acceleration(True), config)
    features = extract_window_features(processed, config)
    events = detect_events(features, config)
    assert len(events) == 1
    assert abs(events.iloc[0]["seconds_elapsed"] - 10.0) < 1.0
    assert events.iloc[0]["event_score"] >= config.detector_threshold


def test_normal_signal_does_not_produce_strong_event_burst():
    config = AnalysisConfig(detector_threshold=5.0)
    processed, _ = preprocess_accelerometer(_synthetic_acceleration(False), config)
    features = extract_window_features(processed, config)
    events = detect_events(features, config)
    assert len(events) <= 1
