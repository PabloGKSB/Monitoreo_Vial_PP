"""Held-out-route window classification, with optional spatial training purge."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, f1_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.neighbors import BallTree
from sklearn.pipeline import make_pipeline

from src.gps import EARTH_RADIUS_M
from .data import PilotConfig


def training_threshold(x: np.ndarray, y: np.ndarray) -> float:
    """Fit a scalar threshold using training labels only; deterministic conservative ties."""
    values = np.unique(x)
    candidates = np.r_[values, np.nextafter(values[-1], np.inf)]
    scores = [f1_score(y, x >= threshold, zero_division=0) for threshold in candidates]
    return float(candidates[np.flatnonzero(np.isclose(scores, max(scores)))[-1]])


def nearest_route_distance(points: pd.DataFrame, gps: pd.DataFrame) -> np.ndarray:
    """Distance to nearest recorded fix, not a road or physical-event identity."""
    coords = points[["latitude", "longitude"]].to_numpy(float)
    track = gps[["latitude", "longitude"]].dropna().to_numpy(float)
    output = np.full(len(points), np.nan)
    valid = np.isfinite(coords).all(axis=1)
    if len(track) and valid.any():
        tree = BallTree(np.radians(track), metric="haversine")
        output[valid] = tree.query(np.radians(coords[valid]), k=1)[0][:, 0] * EARTH_RADIUS_M
    return output


def evaluate(dataset: pd.DataFrame, tracks: dict[str, pd.DataFrame], config: PilotConfig,
             *, group_column: str = "route_id"
             ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Do not mix modes; all imputation and parameter fitting stay in training folds."""
    features = [c for c in dataset if c.startswith(("acc_", "total_", "gyro_"))] + ["speed_kmh"]
    metrics, predictions, importances = [], [], []
    for mode, frame in dataset.groupby("mode", sort=True):
        frame = frame.reset_index(drop=True)
        if frame[group_column].isna().any() or frame[group_column].nunique() < 2:
            raise ValueError("At least two complete evaluation groups required")
        for train_idx, test_idx in LeaveOneGroupOut().split(frame, frame.label, frame[group_column]):
            base_train, test = frame.iloc[train_idx], frame.iloc[test_idx]
            route = str(test[group_column].iloc[0])
            test_tracks = pd.concat([tracks[r] for r in test.route_id.unique()], ignore_index=True)
            distances = nearest_route_distance(base_train, test_tracks)
            prefix = "LORO" if group_column == "route_id" else "LOCO"
            for protocol in (f"{prefix}_EXPLORATORY", f"{prefix}_SPATIAL_PURGE"):
                keep = (np.isfinite(distances) & (distances > config.spatial_purge_meters)
                        if protocol.endswith("SPATIAL_PURGE") else np.ones(len(base_train), dtype=bool))
                train = base_train.iloc[np.flatnonzero(keep)]
                common = {"mode": mode, "protocol": protocol, "test_route": route,
                          "group_column": group_column,
                          "train_routes": "|".join(sorted(train.route_id.unique())),
                          "test_routes": "|".join(sorted(test.route_id.unique())),
                          "train_n": len(train), "test_n": len(test),
                          "train_positive": int(train.label.sum()), "test_positive": int(test.label.sum()),
                          "purged_n": int((~keep).sum()),
                          "train_near_test_route_n": int((distances <= config.spatial_purge_meters).sum()),
                          "train_unknown_location_n": int(np.isnan(distances).sum())}
                if train.label.nunique() < 2 or test.label.nunique() < 2:
                    metrics.extend([{**common, "model": model, "status": "INSUFFICIENT_CLASSES"}
                                    for model in ("threshold", "random_forest")])
                    continue
                xtrain, ytrain = train[features], train.label.to_numpy(int)
                xtest, ytest = test[features], test.label.to_numpy(int)
                threshold = training_threshold(train.acc_mag_absmax.to_numpy(), ytrain)
                forest = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                                       RandomForestClassifier(n_estimators=config.forest_trees,
                                                              min_samples_leaf=config.forest_min_leaf,
                                                              class_weight="balanced", random_state=config.seed,
                                                              n_jobs=1))
                forest.fit(xtrain, ytrain)
                outputs = {"threshold": (test.acc_mag_absmax.to_numpy() >= threshold).astype(int),
                           "random_forest": forest.predict(xtest)}
                for feature, importance in zip(features, forest[-1].feature_importances_):
                    importances.append({"mode": mode, "protocol": protocol, "test_route": route,
                                        "feature": feature, "impurity_importance": float(importance)})
                for model, predicted in outputs.items():
                    precision, recall, f1, _ = precision_recall_fscore_support(ytest, predicted, average="binary", zero_division=0)
                    tn, fp, fn, tp = confusion_matrix(ytest, predicted, labels=[0, 1]).ravel()
                    metrics.append({**common, "model": model, "status": "OK_EXPLORATORY_WINDOWS",
                                    "precision": float(precision), "recall": float(recall), "f1": float(f1),
                                    "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
                                    "threshold": threshold if model == "threshold" else .5})
                    for row, truth, pred in zip(test.itertuples(), ytest, predicted):
                        predictions.append({"sample_id": row.sample_id, "mode": mode, "protocol": protocol,
                                            "test_route": route, "model": model, "label": int(truth),
                                            "prediction": int(pred), "seconds_elapsed": row.seconds_elapsed,
                                            "latitude": row.latitude, "longitude": row.longitude,
                                            "outcome": "TP" if truth and pred else "FN" if truth else "FP" if pred else "TN"})
    prediction_columns = ["sample_id", "mode", "protocol", "test_route", "model", "label",
                          "prediction", "seconds_elapsed", "latitude", "longitude", "outcome"]
    return pd.DataFrame(metrics), pd.DataFrame(predictions, columns=prediction_columns), pd.DataFrame(importances)
