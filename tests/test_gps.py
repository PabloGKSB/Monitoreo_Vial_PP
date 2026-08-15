import pandas as pd

from src.config import AnalysisConfig
from src.gps import associate_gps, prepare_gps


def test_nearest_gps_is_associated_with_tolerance():
    gps = pd.DataFrame({
        "seconds_elapsed": [0.0, 1.0, 2.0], "latitude": [-38.7, -38.7001, -38.7002],
        "longitude": [-72.6, -72.6001, -72.6002], "speed": [1.0, 2.0, 3.0],
        "horizontal_accuracy": [5.0, 6.0, 7.0],
    })
    records = pd.DataFrame({"seconds_elapsed": [1.2, 10.0]})
    result = associate_gps(records, gps, AnalysisConfig(gps_max_time_difference=0.5))
    assert result.iloc[0]["gps_status"] == "OK"
    assert result.iloc[0]["speed_kmh"] == 7.2
    assert result.iloc[1]["gps_status"] == "GPS_NOT_AVAILABLE"


def test_route_distance_increases():
    gps = pd.DataFrame({
        "seconds_elapsed": [0.0, 1.0], "latitude": [-38.7, -38.7001],
        "longitude": [-72.6, -72.6001], "speed": [1.0, 1.0],
    })
    result = prepare_gps(gps)
    assert 10 < result.iloc[-1]["route_distance_m"] < 20
