"""Regression checks for absolute time, exclusion, folds and reproducibility."""

from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn", reason="Install requirements-pilot.txt for pilot tests")

from src.loader import load_trip
from src.pilot.data import PilotConfig, load_pilot_trip, window_features, read_annotations
from src.pilot.dataset import build_dataset, normal_is_clear
from src.pilot.evaluation import evaluate, nearest_route_distance, training_threshold
from src.pilot.review import review_rows


@pytest.fixture
def pilot_trip(tmp_path):
    origin_ms = 1790372910197
    t = np.arange(0, 40, .02)
    rng = np.random.default_rng(8)
    xyz = rng.normal(0, .1, (len(t), 3))
    xyz[np.abs(t - 10) < .06, 1] += 8
    epoch = origin_ms * 1_000_000 + np.rint(t * 1e9).astype(np.int64)
    acc = pd.DataFrame({"time": epoch, "seconds_elapsed": t, "x": xyz[:, 0], "y": xyz[:, 1], "z": xyz[:, 2]})
    gps = pd.DataFrame({"time": origin_ms * 1_000_000 + np.arange(40, dtype=np.int64) * 1_000_000_000,
                        "seconds_elapsed": np.arange(40), "latitude": -38.7 + np.arange(40)*.00001,
                        "longitude": -72.6, "speed": 5, "horizontalAccuracy": 4})
    archive = tmp_path / "route.zip"
    with ZipFile(archive, "w") as z:
        for name in ("Accelerometer", "TotalAcceleration", "Gyroscope", "Gravity", "Magnetometer", "Compass"):
            z.writestr(f"{name}.csv", acc.to_csv(index=False))
        z.writestr("Location.csv", gps.to_csv(index=False))
        z.writestr("Metadata.csv", pd.DataFrame({"recording epoch time": [origin_ms],
                                                "recording time": ["2026-09-25_21-48-30"],
                                                "recording timezone": ["America/Santiago"]}).to_csv(index=False))
    annotations = tmp_path / "annotations.csv"
    pd.DataFrame({"epoch_ms": origin_ms + np.array([0, 11500, 24000, 39000]),
                  "event_type": ["MONITOREO_INICIO", "BACHE", "GIRO", "MONITOREO_FIN"],
                  "timestamp": ["wrong-formatted-clock"]*4, "elapsed_ms": [999]*4}).to_csv(annotations, index=False)
    return load_pilot_trip(archive, annotations, "synthetic"), archive, annotations


def test_epoch_overrides_formatted_metadata_and_annotation_elapsed(pilot_trip):
    trip, archive, _ = pilot_trip
    assert trip.origin == pd.Timestamp("2026-09-25T21:48:30.197Z")
    assert trip.annotations.iloc[1].seconds_elapsed == pytest.approx(11.5)
    loaded = load_trip(archive)
    assert {"gravity", "magnetometer", "compass"} <= loaded.sensors.keys()
    assert any("disagrees" in w for w in loaded.warnings)


def test_normal_exclusion_uses_full_window_and_all_classes():
    config = PilotConfig()
    assert not normal_is_clear(8.5, np.array([0.]), config)
    assert normal_is_clear(9., np.array([0.]), config)


def test_dataset_reproducible_peaks_provisional_and_no_normal_overlap(pilot_trip):
    trip, _, _ = pilot_trip
    config = PilotConfig(normal_exclusion_seconds=3)
    dataset, marks = build_dataset(trip, config)
    again, _ = build_dataset(trip, config)
    pd.testing.assert_frame_equal(dataset, again)
    assert set(dataset["mode"]) == {"fixed_delay", "peak_assisted"}
    for _, part in dataset.groupby("mode"):
        assert part.label.sum() == 1
        assert (part.label == 0).sum() == 3
        assert part.sort_values("window_start").window_start.to_numpy()[1:].min() >= 0
        bounds = part.sort_values("window_start")
        assert np.all(bounds.window_start.to_numpy()[1:] >= bounds.window_end.to_numpy()[:-1] - 1e-8)
        for row in part[part.label == 0].itertuples():
            assert normal_is_clear(row.seconds_elapsed, np.array([11.5, 24]), config)
    peak = marks.loc[marks.event_type == "BACHE", "candidate_peak_seconds"].iloc[0]
    assert 9.9 < peak < 10.1


def test_window_rejects_sensor_gap(pilot_trip):
    trip, _, _ = pilot_trip
    frame = trip.signals["gyroscope"]
    trip.signals["gyroscope"] = frame[~frame.seconds_elapsed.between(9.9, 10.2)]
    assert window_features(trip, 10, PilotConfig()) is None


def test_fold_purge_skips_shared_sectors_and_predicts_each_heldout_window(pilot_trip):
    trip, _, _ = pilot_trip
    cfg = PilotConfig(normal_exclusion_seconds=3, forest_trees=5)
    data, _ = build_dataset(trip, cfg)
    other = data.assign(route_id="other", sample_id="other_" + data.sample_id)
    both = pd.concat([data, other], ignore_index=True)
    metrics, predictions, _ = evaluate(both, {"synthetic": trip.gps, "other": trip.gps}, cfg)
    purged = metrics[metrics.protocol == "LORO_SPATIAL_PURGE"]
    assert (purged.status == "INSUFFICIENT_CLASSES").all()
    assert (purged.train_n == 0).all()
    assert (predictions.groupby(["mode", "model", "sample_id"]).size() == 1).all()
    assert len(predictions) == len(both)*2


def test_threshold_and_distance_are_deterministic():
    assert training_threshold(np.array([1., 2., 8., 9.]), np.array([0, 0, 1, 1])) == 8
    points = pd.DataFrame({"latitude": [-38.7, np.nan], "longitude": [-72.6, np.nan]})
    distances = nearest_route_distance(points, points.iloc[:1])
    assert distances[0] == pytest.approx(0)
    assert np.isnan(distances[1])


def test_annotation_bad_epoch_rejected(pilot_trip):
    trip, _, path = pilot_trip
    frame = pd.read_csv(path)
    frame.loc[1, "epoch_ms"] = np.nan
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="invalid epoch"):
        read_annotations(path, trip.origin)


def test_corridor_folds_keep_outbound_and_return_together(pilot_trip):
    trip, _, _ = pilot_trip
    cfg = PilotConfig(normal_exclusion_seconds=3, forest_trees=5)
    data, _ = build_dataset(trip, cfg)
    frames = [data.assign(route_id=r, corridor_id=c, sample_id=r + data.sample_id)
              for r, c in (("a", "shared"), ("b", "shared"), ("c", "separate"))]
    metrics, predictions, _ = evaluate(pd.concat(frames, ignore_index=True),
                                      {r: trip.gps for r in ("a", "b", "c")}, cfg,
                                      group_column="corridor_id")
    standard = metrics[metrics.protocol == "LOCO_EXPLORATORY"]
    shared = standard[standard.test_route == "shared"]
    assert (shared.test_routes == "a|b").all()
    assert (shared.train_routes == "c").all()
    assert (shared.train_n == len(data) // 2).all()
    assert (predictions.groupby(["mode", "model", "sample_id"]).size() == 1).all()
    assert (metrics.loc[metrics.protocol == "LOCO_SPATIAL_PURGE", "train_n"] == 0).all()


def test_review_preserves_labels_and_deduplicates_modes(pilot_trip):
    trip, _, _ = pilot_trip
    cfg = PilotConfig(normal_exclusion_seconds=3)
    data, marks = build_dataset(trip, cfg)
    before = data.copy(deep=True)
    review = review_rows(data, marks, cfg)
    assert len(review) == 4
    assert review.original_label.sum() == 1
    assert (review.ground_truth_status == "UNVERIFIED").all()
    pd.testing.assert_frame_equal(data, before)
    assert review.loc[review.original_label == 1, "candidate_delay_seconds"].iloc[0] == pytest.approx(1.5, abs=.1)


def test_retroactive_delay_moves_only_fixed_positive_windows(pilot_trip):
    trip, _, _ = pilot_trip
    old, _ = build_dataset(trip, PilotConfig(normal_exclusion_seconds=3, fixed_delay_seconds=1.5))
    new, _ = build_dataset(trip, PilotConfig(normal_exclusion_seconds=3, fixed_delay_seconds=2.5))
    old_fixed = old[(old['mode'] == 'fixed_delay') & (old.label == 1)]
    new_fixed = new[(new['mode'] == 'fixed_delay') & (new.label == 1)]
    assert np.allclose(new_fixed.seconds_elapsed, old_fixed.seconds_elapsed - 1)
    assert np.allclose(new_fixed.annotation_seconds - new_fixed.seconds_elapsed, 2.5)
    unchanged = (old['mode'] == 'peak_assisted') | (old.label == 0)
    pd.testing.assert_frame_equal(old.loc[unchanged].reset_index(drop=True),
                                  new.loc[unchanged].reset_index(drop=True))
