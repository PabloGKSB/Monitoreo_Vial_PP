import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import analyzer
from src.analyzer import TripAnalyzer
from src.config import AnalysisConfig
from src.detector import detect_events
from src.features import extract_window_features
from src.loader import TripData
from src.preprocessing import preprocess_accelerometer
from src.quality import assess_trip
from src.scoring import add_experimental_road_score


def make_trip(*, invalid_gps=False, invalid_axes=False, gps_gap=False):
    seconds = np.arange(0, 12, .02)
    accel = pd.DataFrame({"seconds_elapsed": seconds, "x": .1, "y": .1,
                          "z": np.sin(seconds), "timestamp": pd.Timestamp("2026-10-10T12:00Z") + pd.to_timedelta(seconds,unit="s")})
    if invalid_axes:
        accel["x"] = np.inf
    gps_seconds = np.r_[np.arange(0,4),np.arange(8,13)] if gps_gap else np.arange(0,13)
    gps = pd.DataFrame({"seconds_elapsed": gps_seconds, "latitude": 100 if invalid_gps else -38.7,
                        "longitude": -72.6, "speed": 2, "horizontal_accuracy": 5})
    return TripData("policy_fixture", Path("fixture.zip"), {"accelerometer":accel,"gps":gps}, {})


@pytest.mark.parametrize("kwargs", [{"invalid_gps":True},{"invalid_axes":True}])
def test_invalid_trip_never_calls_detector_or_preprocessing(tmp_path, monkeypatch, kwargs):
    monkeypatch.setattr(analyzer,"load_trip",lambda _:make_trip(**kwargs))
    def forbidden(*args):
        pytest.fail("Invalid trip must not preprocess or score")
    monkeypatch.setattr(analyzer,"preprocess_accelerometer",forbidden)
    monkeypatch.setattr(analyzer,"score_windows",forbidden)
    result = TripAnalyzer().analyze("unused.zip")
    assert result.summary["detection_status"] == "BLOCKED_INVALID"
    assert result.summary["event_count"] is None
    assert result.events.empty and result.segments.empty
    report = json.loads(TripAnalyzer().export(result,tmp_path)["report"].read_text(encoding="utf-8"))
    assert report["summary"]["event_count"] is None


def test_filters_and_windows_remain_in_separate_signal_blocks():
    first = make_trip().sensors["accelerometer"].iloc[:100].copy()
    second = first.copy()
    second.seconds_elapsed += 10
    second.z += 30
    combined, _ = preprocess_accelerometer(pd.concat([first,second],ignore_index=True))
    isolated, _ = preprocess_accelerometer(first)
    assert combined.signal_block.nunique() == 2
    np.testing.assert_allclose(combined.iloc[:100].smoothed_magnitude,isolated.smoothed_magnitude)
    features = extract_window_features(combined)
    assert not ((features.window_start < 10)&(features.window_end > first.seconds_elapsed.max()+1e-9)).any()
    assert combined.loc[combined.signal_block==1,"jerk"].iloc[0] == 0


def test_nonfinite_row_splits_signal_instead_of_interpolating():
    frame = make_trip().sensors["accelerometer"]
    frame.loc[100,"z"] = np.nan
    processed, _ = preprocess_accelerometer(frame)
    assert processed.signal_block.nunique() == 2
    assert np.isfinite(processed.smoothed_magnitude).all()
    assert assess_trip(make_trip(invalid_axes=True)).overall_status.value == "INVALID"


def test_gps_gap_excludes_windows_and_does_not_color_unknown_road(monkeypatch):
    monkeypatch.setattr(analyzer,"load_trip",lambda _:make_trip(gps_gap=True))
    result = TripAnalyzer().analyze("unused.zip")
    features = result.window_features
    assert not ((features.window_start < 8)&(features.window_end > 3)).any()
    assert result.summary["eligible_window_count"] < result.summary["candidate_window_count"]
    assert result.summary["detection_status"] == "EVALUATED"


def test_anomalies_in_distinct_blocks_do_not_merge():
    rows = pd.DataFrame({"timestamp":[pd.NaT]*12,"seconds_elapsed":np.arange(12)*.1,
        "window_start":np.arange(12)*.1,"window_end":np.arange(12)*.1+.1,
        "magnitude_max":[1]*10+[100,100],"rms":[1]*10+[100,100],
        "std":[1]*10+[100,100],"jerk_max":[1]*10+[100,100],"energy":[1]*10+[100,100],
        "signal_block":[0]*11+[1]})
    assert len(detect_events(rows,AnalysisConfig(detector_threshold=2))) == 2


def test_short_trip_is_not_zero_events(monkeypatch):
    trip = make_trip()
    trip.sensors["accelerometer"] = trip.sensors["accelerometer"].iloc[:20]
    monkeypatch.setattr(analyzer,"load_trip",lambda _:trip)
    result = TripAnalyzer().analyze("unused.zip")
    assert result.summary["event_count"] is None
    assert result.summary["detection_status"] == "NOT_EVALUATED"
    assert result.segments.empty


def test_segment_without_windows_is_not_good_condition():
    frame = pd.DataFrame({"event_count":[0,0],"max_event_score":[np.nan,np.nan],
                          "mean_rms":[np.nan,.1],"observation_count":[0,5]})
    scored = add_experimental_road_score(frame)
    assert scored.iloc[0].condition == "SIN_DATOS"
    assert pd.isna(scored.iloc[0].road_condition_score)
