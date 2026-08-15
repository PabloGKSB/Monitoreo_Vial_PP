import pandas as pd

from src.config import AnalysisConfig
from src.quality import QualityStatus, assess_sensor


def test_sampling_frequency_uses_real_timestamps():
    frame = pd.DataFrame({"seconds_elapsed": [0.0, 0.02, 0.04, 0.06]})
    result = assess_sensor("accelerometer", frame, AnalysisConfig())
    assert result.sampling_hz == 50.0
    assert result.status == QualityStatus.OK


def test_detects_large_sensor_gap():
    frame = pd.DataFrame({"seconds_elapsed": [0.0, 0.01, 0.02, 3.0, 3.01]})
    result = assess_sensor("gyroscope", frame, AnalysisConfig())
    assert result.status == QualityStatus.WARNING
    assert len(result.gaps) == 1
    assert result.gaps[0].duration_seconds == 2.98


def test_gps_invalid_coordinates_are_reported():
    frame = pd.DataFrame({
        "seconds_elapsed": [0.0, 1.0, 2.0],
        "latitude": [-38.7, 100.0, None],
        "longitude": [-72.6, -72.6, -72.6],
        "horizontal_accuracy": [5.0, 8.0, 10.0],
        "speed": [2.0, -1.0, 3.0],
    })
    result = assess_sensor("gps", frame, AnalysisConfig())
    assert result.status == QualityStatus.INVALID
    assert result.metrics["missing_coordinates"] == 1
    assert result.metrics["invalid_coordinates"] == 1

