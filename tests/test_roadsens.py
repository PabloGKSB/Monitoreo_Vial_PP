from dataclasses import replace
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

from src.pilot.data import summarize_signal
from src.pilot.roadsens import (
    CHANNELS, FEATURES, ExternalConfig, evaluate_external, fit_models,
    predict_models, session_folds, session_windows, external_dataset,
)


def series(labels=None, seconds=6):
    t = np.arange(seconds * 100) / 100
    frame = pd.DataFrame({"seconds_elapsed": t})
    for sensor in CHANNELS:
        for axis in "xyz":
            frame[f"{sensor}_{axis}"] = np.sin(t * 4) + (9 if sensor == "totalAcceleration" else 0)
    if labels is not None:
        frame["annotation_text"] = labels
    return frame


def test_labels_are_not_inferred_from_empty_or_bump():
    frame = series(np.repeat(["Pothole", "", "Bump", "Pothole"], 150))
    windows, review, audit = session_windows(frame, "mixed/1", False, ExternalConfig())
    assert windows.label.tolist() == [1, 1]
    assert len(review) == 4
    assert audit["window_status"]["EXCLUDED_UNKNOWN_OR_BUMP"] == 2
    assert len(audit["blocks"]) == 4


def test_normal_source_and_nonfinite_rejection():
    frame = series()
    frame.loc[200, "gyroscope_x"] = np.nan
    windows, review, _ = session_windows(frame, "normal/1", True, ExternalConfig())
    assert windows.label.tolist() == [0, 0, 0]
    assert (review.status == "EXCLUDED_NONFINITE").sum() == 1
    assert set(FEATURES) <= set(windows)
    assert all("mag" in c for c in FEATURES)
    assert not any("speed" in c or "location" in c for c in FEATURES)


def test_mixed_boundaries_and_short_blocks_excluded():
    frame = series(["Pothole"] * 50 + [""] * 550)
    windows, review, audit = session_windows(frame, "mixed/1", False, ExternalConfig())
    assert windows.empty
    assert review.status.iloc[0] == "EXCLUDED_MIXED_LABELS"
    assert audit["blocks"][0]["accepted_windows"] == 0


def test_summary_not_a_series():
    windows, _, audit = session_windows(pd.DataFrame({"Total Rows": [10]}), "99", False, ExternalConfig())
    assert windows.empty and audit["status"] == "EXCLUDED_NOT_A_TIME_SERIES"


def test_clock_and_gap_validation():
    frame = series()
    frame.loc[1, "seconds_elapsed"] = 0
    assert session_windows(frame, "bad", True, ExternalConfig())[2]["status"] == "EXCLUDED_INVALID_CLOCK"
    frame = series().drop(index=range(30, 50))
    windows, review, _ = session_windows(frame, "gap", True, ExternalConfig())
    assert len(windows) == 3
    assert review.status.iloc[0] == "EXCLUDED_GAP"


def test_shared_features_match_local_definition():
    frame = series(seconds=3)
    windows, _, _ = session_windows(frame, "normal", True, ExternalConfig())
    t = frame.seconds_elapsed.to_numpy()[:150]
    mag = np.linalg.norm(frame[["accelerometer_x", "accelerometer_y", "accelerometer_z"]].to_numpy()[:150], axis=1)
    expected = summarize_signal(mag, t)
    for name, value in expected.items():
        assert windows.iloc[0][f"acc_mag_{name}"] == pytest.approx(value)


def synthetic_dataset():
    frames = []
    for label in [0, 1]:
        for index in range(5):
            frame = series(["Pothole"] * 300 if label else None, seconds=3)
            frame["accelerometer_x"] *= 1 + label * 3
            windows, _, _ = session_windows(frame, f"{label}/{index}", not label, ExternalConfig())
            frames.append(windows)
    return pd.concat(frames, ignore_index=True)


def test_group_splits_disjoint_complete_and_repeatable():
    data = synthetic_dataset()
    folds = session_folds(data, ExternalConfig())
    assert folds.equals(session_folds(data, ExternalConfig()))
    for fold in range(5):
        train, test = data[folds != fold], data[folds == fold]
        assert not set(train.session_id) & set(test.session_id)
        assert set(test.label) == {0, 1}
    assert pd.DataFrame({"session": data.session_id, "fold": folds}).groupby("session").fold.nunique().max() == 1


def test_evaluation_predictions_and_target_labels_cannot_affect_inference():
    data = synthetic_dataset()
    config = replace(ExternalConfig(), forest_trees=5)
    windows, metrics, predictions = evaluate_external(data, config)
    assert len(metrics) == 10
    assert len(predictions) == 2 * len(data)
    assert predictions.groupby(["model", "sample_id"]).size().max() == 1
    models = fit_models(data, config)
    before = predict_models(models, data)
    changed = data.copy()
    changed.label = 1 - changed.label
    after = predict_models(models, changed)
    for name in before:
        np.testing.assert_array_equal(before[name], after[name])


def test_too_few_groups_rejected():
    data = synthetic_dataset()
    with pytest.raises(ValueError, match="Too few sessions"):
        session_folds(data[data.session_id != "0/0"], ExternalConfig())


def test_duplicate_archived_csv_excluded_before_split(tmp_path, monkeypatch):
    path = tmp_path / "dataset.zip"
    with ZipFile(path, "w") as archive:
        archive.writestr("Road Anomalies/data.rar", b"placeholder")
    payload = series(["Pothole"] * 300, seconds=3).to_csv(index=False).encode()
    def fake_tar(command):
        return b"1.csv\n2.csv\n" if command[1] == "-tf" else payload
    monkeypatch.setattr("src.pilot.roadsens.subprocess.check_output", fake_tar)
    data, _, audits = external_dataset(path, ExternalConfig())
    assert data.session_id.unique().tolist() == ["mixed/1.csv"]
    assert audits[-1]["status"] == "EXCLUDED_DUPLICATE_CONTENT"
    assert audits[-1]["duplicate_of"] == "mixed/1.csv"
