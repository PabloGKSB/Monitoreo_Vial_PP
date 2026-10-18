"""Audited external window benchmark; never replaces the deployed V0 detector."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess
import tempfile
from zipfile import ZipFile

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from .data import PilotConfig, load_pilot_trip, summarize_signal
from .dataset import build_dataset
from .evaluation import training_threshold

CHANNELS = {"accelerometer": "acc", "totalAcceleration": "total", "gyroscope": "gyro"}
FEATURES = tuple(f"{prefix}_mag_{stat}" for prefix in CHANNELS.values()
                 for stat in summarize_signal(np.array([0., 1.]), np.array([0., 1.])))


@dataclass(frozen=True)
class ExternalConfig:
    window_seconds: float = 1.5
    max_gap_seconds: float = 0.1
    minimum_coverage: float = 0.8
    folds: int = 5
    seed: int = 42
    forest_trees: int = 200
    forest_min_leaf: int = 2


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare_local_transfer(input_dir: Path, manifest_path: Path):
    """Rebuild the existing fixed-delay pilot; it is evaluation-only here."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = PilotConfig(**manifest["parameters"])
    if config.window_seconds != 1.5 or config.fixed_delay_seconds != 2.5:
        raise ValueError("Transfer requires the documented 1.5 s window / 2.5 s delay")
    frames, sources, candidates = [], [], []
    for route in manifest["routes"]:
        archive, annotations = input_dir / route["zip"], input_dir / route["annotations"]
        trip = load_pilot_trip(archive, annotations, route["route_id"])
        dataset, review = build_dataset(trip, config)
        frame = dataset[dataset["mode"] == "fixed_delay"].copy()
        frame["session_id"] = route["route_id"]
        frame["corridor_id"] = manifest["corridors"][route["route_id"]]
        frames.append(frame)
        candidates.append(review)
        sources.extend({"name": p.name, "sha256": sha256(p)} for p in (archive, annotations))
    return pd.concat(frames, ignore_index=True), sources, pd.concat(candidates, ignore_index=True)


def session_windows(frame: pd.DataFrame, session_id: str, source_normal: bool,
                    config: ExternalConfig):
    """Fixed non-overlapping grid; unknown/mixed labels never become negatives."""
    audit = {"session_id": session_id, "rows": len(frame), "source_normal": source_normal}
    if "seconds_elapsed" not in frame:
        return pd.DataFrame(), pd.DataFrame(), {**audit, "status": "EXCLUDED_NOT_A_TIME_SERIES"}
    columns = [f"{sensor}_{axis}" for sensor in CHANNELS for axis in "xyz"]
    if not set(columns) <= set(frame):
        return pd.DataFrame(), pd.DataFrame(), {**audit, "status": "EXCLUDED_MISSING_CHANNELS"}
    t = pd.to_numeric(frame.seconds_elapsed, errors="coerce").to_numpy(float)
    if len(t) < 2 or not np.isfinite(t).all() or (np.diff(t) <= 0).any():
        return pd.DataFrame(), pd.DataFrame(), {**audit, "status": "EXCLUDED_INVALID_CLOCK"}
    median_dt = float(np.median(np.diff(t)))
    values = frame[columns].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if source_normal:
        labels = np.full(len(t), "NORMAL_SOURCE", dtype=object)
    else:
        labels = frame.get("annotation_text", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip().to_numpy()
    starts = np.r_[0, np.flatnonzero(labels[1:] != labels[:-1]) + 1]
    stops = np.r_[starts[1:], len(t)]
    blocks = [{"session_id": session_id, "block_id": int(i), "source_label": str(labels[lo]),
               "start_seconds": float(t[lo]), "last_sample_seconds": float(t[hi - 1]),
               "row_count": int(hi - lo), "accepted_windows": 0}
              for i, (lo, hi) in enumerate(zip(starts, stops))]
    block_ids = np.repeat(np.arange(len(starts)), stops - starts)
    rows, window_audit = [], []
    # A final sample covers one nominal sample period, not an invented extra window.
    n_windows = int(np.floor((t[-1] + median_dt - t[0] + 1e-8) / config.window_seconds))
    for index in range(n_windows):
        start = t[0] + index * config.window_seconds
        end = start + config.window_seconds
        lo, hi = np.searchsorted(t, [start - 1e-9, end - 1e-9])
        sample_id = f"{session_id}:W{index:05d}"
        item = {"sample_id": sample_id, "session_id": session_id,
                "window_start": float(start), "window_end": float(end), "sample_count": int(hi - lo)}
        observed = set(labels[lo:hi])
        label = 1 if observed == {"Pothole"} else 0 if observed == {"NORMAL_SOURCE"} else None
        reason = "ACCEPTED"
        if label is None:
            reason = "EXCLUDED_MIXED_LABELS" if len(observed) > 1 else "EXCLUDED_UNKNOWN_OR_BUMP"
        elif hi - lo < max(5, config.minimum_coverage * config.window_seconds / median_dt):
            reason = "EXCLUDED_COVERAGE"
        elif np.diff(np.r_[start, t[lo:hi], end]).max() > config.max_gap_seconds + 1e-9:
            reason = "EXCLUDED_GAP"
        elif not np.isfinite(values[lo:hi]).all():
            reason = "EXCLUDED_NONFINITE"
        window_audit.append({**item, "status": reason, "observed_labels": "|".join(sorted(observed))})
        if reason != "ACCEPTED":
            continue
        features = {}
        for offset, prefix in enumerate(CHANNELS.values()):
            magnitude = np.linalg.norm(values[lo:hi, offset * 3:offset * 3 + 3], axis=1)
            features.update({f"{prefix}_mag_{name}": value
                             for name, value in summarize_signal(magnitude, t[lo:hi]).items()})
        block_id = int(block_ids[lo])
        blocks[block_id]["accepted_windows"] += 1
        rows.append({**item, "label": label, "block_id": block_id,
                     "label_source": "POTHOLE_AUTHOR" if label else "NORMAL_FOLDER_AUTHOR", **features})
    audit.update(status="AUDITED", median_dt=median_dt, max_dt=float(np.diff(t).max()),
                 label_rows=dict(Counter(labels)), blocks=blocks,
                 window_status=dict(Counter(i["status"] for i in window_audit)),
                 trailing_seconds=float(max(0, t[-1] + median_dt - (t[0] + n_windows * config.window_seconds))))
    return pd.DataFrame(rows), pd.DataFrame(window_audit), audit


def external_dataset(zip_path: Path, config: ExternalConfig):
    frames, reviews, audits = [], [], []
    hashes = {}
    with tempfile.TemporaryDirectory(prefix="roadsens-audit-") as temporary, ZipFile(zip_path) as archive:
        for index, info in enumerate(archive.infolist()):
            if not info.filename.lower().endswith(".rar"):
                continue
            source_normal = "Normal Road (No Annotation)" in info.filename
            if not source_normal and "Road Anomalies" not in info.filename:
                raise ValueError(f"Unrecognized RAR group: {info.filename}")
            # Only controlled local paths are written; CSV members are streamed by tar.
            rar = Path(temporary) / f"group_{index}.rar"
            rar.write_bytes(archive.read(info))
            names = subprocess.check_output(["tar", "-tf", str(rar)]).decode("utf-8").splitlines()
            for name in names:
                if PurePosixPath(name).name != name or not name.lower().endswith(".csv") or name.startswith("-"):
                    raise ValueError(f"Unexpected RAR member: {name}")
                payload = subprocess.check_output(["tar", "-xOf", str(rar), name])
                session_id = ("normal/" if source_normal else "mixed/") + name
                digest = hashlib.sha256(payload).hexdigest()
                if digest in hashes:
                    audits.append({"session_id": session_id, "status": "EXCLUDED_DUPLICATE_CONTENT",
                                   "duplicate_of": hashes[digest], "sha256": digest,
                                   "rar_member": info.filename, "csv_member": name})
                    print(f"Excluded duplicate {session_id}: {hashes[digest]}", flush=True)
                    continue
                hashes[digest] = session_id
                frame = pd.read_csv(io.BytesIO(payload), low_memory=False)
                windows, review, audit = session_windows(frame, session_id, source_normal, config)
                audit.update(sha256=digest, rar_member=info.filename, csv_member=name)
                frames.append(windows)
                reviews.append(review)
                audits.append(audit)
                print(f"Audited {session_id}: {len(windows)} accepted windows", flush=True)
    return pd.concat(frames, ignore_index=True), pd.concat(reviews, ignore_index=True), audits


def session_folds(dataset: pd.DataFrame, config: ExternalConfig):
    """Stratify groups by class presence, keeping every session in one test fold."""
    signatures = dataset.groupby("session_id").label.apply(lambda s: tuple(sorted(s.unique())))
    rng = np.random.default_rng(config.seed)
    assignment = {}
    for signature in sorted(set(signatures)):
        groups = sorted(signatures[signatures == signature].index)
        if len(groups) < config.folds:
            raise ValueError(f"Too few sessions for {config.folds} folds: {signature}")
        for index, group in enumerate(rng.permutation(groups)):
            assignment[str(group)] = index % config.folds
    return dataset.session_id.map(assignment).astype(int)


def fit_models(train: pd.DataFrame, config: ExternalConfig):
    if set(train.label.unique()) != {0, 1}:
        raise ValueError("Training requires both classes")
    threshold = training_threshold(train.acc_mag_absmax.to_numpy(), train.label.to_numpy())
    forest = RandomForestClassifier(n_estimators=config.forest_trees,
                                    min_samples_leaf=config.forest_min_leaf,
                                    class_weight="balanced", random_state=config.seed, n_jobs=1)
    forest.fit(train[list(FEATURES)], train.label)
    return threshold, forest


def predict_models(models, frame: pd.DataFrame):
    threshold, forest = models
    return {"threshold": (frame.acc_mag_absmax.to_numpy() >= threshold).astype(int),
            "random_forest": forest.predict(frame[list(FEATURES)])}


def metrics_for(truth, predicted):
    tn, fp, fn, tp = confusion_matrix(truth, predicted, labels=[0, 1]).ravel()
    p, r, f, support = precision_recall_fscore_support(truth, predicted, labels=[0, 1], zero_division=0)
    return {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
            "precision_normal": float(p[0]), "recall_normal": float(r[0]), "f1_normal": float(f[0]),
            "precision_bache": float(p[1]), "recall_bache": float(r[1]), "f1_bache": float(f[1]),
            "support_normal": int(support[0]), "support_bache": int(support[1]), "macro_f1": float(f.mean())}


def evaluate_external(dataset: pd.DataFrame, config: ExternalConfig):
    dataset = dataset.copy()
    dataset["test_fold"] = session_folds(dataset, config)
    metrics, predictions = [], []
    for fold in range(config.folds):
        train, test = dataset[dataset.test_fold != fold], dataset[dataset.test_fold == fold]
        if set(test.label.unique()) != {0, 1}:
            raise ValueError("Test fold missing class")
        models = fit_models(train, config)
        for name, predicted in predict_models(models, test).items():
            metrics.append({"protocol": "EXTERNAL_SESSION_CV", "fold": fold, "model": name,
                            "train_n": len(train), "test_n": len(test),
                            "threshold": models[0] if name == "threshold" else .5,
                            **metrics_for(test.label, predicted)})
            part = test[["sample_id", "session_id", "window_start", "window_end", "block_id",
                         "label", "label_source", "test_fold"]].copy()
            part["model"], part["prediction"] = name, predicted
            part["outcome"] = np.where(part.label == 1, np.where(predicted == 1, "TP", "FN"),
                                       np.where(predicted == 1, "FP", "TN"))
            predictions.append(part)
    return dataset, pd.DataFrame(metrics), pd.concat(predictions, ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--local-input-dir", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("configs/campana_2026_09_25_retraso_2_5.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/reports/roadsens4m"))
    args = parser.parse_args()
    config = ExternalConfig()
    output = args.output_dir / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True, exist_ok=False)
    def write_json(name, value):
        (output / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    write_json("protocol.json", {"parameters": asdict(config), "features": FEATURES,
               "target": "Pothole vs author-declared normal sessions; Bump and unknown excluded",
               "local_use": "Evaluation only; previously explored campaign, not untouched validation",
               "input_sha256": sha256(args.zip), "manifest_sha256": sha256(args.manifest)})
    dataset, review, audits = external_dataset(args.zip, config)
    review.to_csv(output / "window_audit.csv", index=False)
    write_json("session_audit.json", audits)
    pd.DataFrame([block for a in audits for block in a.get("blocks", [])]).to_csv(output / "label_blocks.csv", index=False)
    if dataset.empty:
        raise ValueError("No accepted external windows")
    dataset, metrics, predictions = evaluate_external(dataset, config)
    dataset.to_csv(output / "external_windows.csv", index=False)
    metrics.to_csv(output / "external_fold_metrics.csv", index=False)
    predictions.to_csv(output / "external_predictions.csv", index=False)
    # Final estimators see external data only; local labels cannot tune this fit.
    models = fit_models(dataset, config)
    local, sources, candidates = prepare_local_transfer(args.local_input_dir, args.manifest)
    finite = np.isfinite(local[list(FEATURES)].to_numpy(float)).all(axis=1)
    if not finite.all():
        raise ValueError("Nonfinite local transfer features")
    local.to_csv(output / "local_windows.csv", index=False)
    candidates.to_csv(output / "local_annotation_review.csv", index=False)
    transfer_metrics, transfer_predictions = [], []
    for name, predicted in predict_models(models, local).items():
        part = local[["sample_id", "session_id", "corridor_id", "window_start", "window_end",
                      "timestamp_utc", "label", "label_source"]].copy()
        part["model"], part["prediction"] = name, predicted
        part["outcome"] = np.where(part.label == 1, np.where(predicted == 1, "TP", "FN"),
                                   np.where(predicted == 1, "FP", "TN"))
        transfer_predictions.append(part)
        for group, selection in [("ALL", part), *list(part.groupby("corridor_id"))]:
            transfer_metrics.append({"protocol": "EXTERNAL_TO_LOCAL_EXPLORATORY", "model": name,
                                     "group": group, **metrics_for(selection.label, selection.prediction)})
    pd.DataFrame(transfer_metrics).to_csv(output / "transfer_metrics.csv", index=False)
    pd.concat(transfer_predictions, ignore_index=True).to_csv(output / "transfer_predictions.csv", index=False)
    pooled = [{"model": name, **metrics_for(p.label, p.prediction)} for name, p in predictions.groupby("model")]
    write_json("external_pooled_metrics.json", pooled)
    write_json("provenance.json", {"external_name": args.zip.name, "external_sha256": sha256(args.zip),
               "local_sources": sources, "manifest_sha256": sha256(args.manifest),
               "source_sha256": {str(p): sha256(p) for p in sorted(Path("src").rglob("*.py"))},
               "versions": {"python": platform.python_version(), "numpy": np.__version__,
                            "pandas": pd.__version__, "sklearn": sklearn.__version__},
               "final_threshold": float(models[0]), "local_training_samples": 0})
    report = ["# RoadSens-4M: experimento exploratorio", "",
              "Tarea: clasificacion de ventanas BACHE/NORMAL, no deteccion continua.",
              f"Ventanas externas: {len(dataset)}; sesiones aceptadas: {dataset.session_id.nunique()}.",
              f"Clases externas: {dataset.label.value_counts().to_dict()}.",
              f"Ventanas locales: {len(local)}; ninguna usada para entrenar o ajustar.", "",
              "## Validacion externa por sesion (predicciones fuera de entrenamiento)", "",
              "| Modelo | Precision BACHE | Recall BACHE | F1 BACHE | F1 macro |",
              "|---|---:|---:|---:|---:|"]
    for row in pooled:
        report.append(f"| {row['model']} | {row['precision_bache']:.3f} | {row['recall_bache']:.3f} | {row['f1_bache']:.3f} | {row['macro_f1']:.3f} |")
    report.extend(["", "## Transferencia a campana local (exploratoria)", "",
                   "| Modelo | Grupo | TP | FP | FN | TN | F1 BACHE |",
                   "|---|---|---:|---:|---:|---:|---:|"])
    for row in transfer_metrics:
        report.append(f"| {row['model']} | {row['group']} | {row['tp']} | {row['fp']} | {row['fn']} | {row['tn']} | {row['f1_bache']:.3f} |")
    report.extend(["", "## Limites", "",
                   "- Negativos externos proceden solo de cinco sesiones declaradas normales; posible efecto de sesion.",
                   "- Separacion por archivo, no independencia geografica ni por defecto fisico demostrada.",
                   "- Filas sin etiqueta, Bump y ventanas mixtas excluidas: resultados no cubren esos casos.",
                   "- Ventanas homogeneas excluyen transiciones y eventos cortos; revisar label_blocks.csv.",
                   "- Dataset combinado a 100 Hz frente a muestras locales nativas: transferencia no homogeneiza filtros ni montaje.",
                   "- Features de magnitud reducen dependencia de ejes, no eliminan diferencias de dispositivo/vehiculo.",
                   "- Marcas locales retrospectivas y NORMAL candidato; FP son contra etiquetas provisionales.",
                   "- La campana local ya fue explorada; no es una prueba final independiente.",
                   "- No se modifico app.py ni se entreno con los ZIP nativos de la nueva APK.",
                   "- Revisar metricas por fold y errores, no solo agregados. No se calculo FP/km."])
    (output / "INFORME.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"REPORT: {output / 'INFORME.md'}", flush=True)


if __name__ == "__main__":
    main()
