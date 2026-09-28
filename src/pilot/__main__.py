"""Run with python -m src.pilot --input-dir <directory> [--manifest <json>]."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import logging
from pathlib import Path
import platform

import pandas as pd

from .data import PilotConfig, load_pilot_trip
from .dataset import build_dataset
from .evaluation import evaluate, nearest_route_distance
from .reporting import save_annotation_plot, write_report
from .review import write_review

ROOT = Path(__file__).resolve().parents[2]


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def run(manifest_path: Path, input_dir: Path, output_root: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config = PilotConfig(**manifest["parameters"])
    routes = manifest["routes"]
    if len({r["route_id"] for r in routes}) != len(routes):
        raise ValueError("Duplicate route_id in manifest")
    inputs, datasets, candidates, annotations, audits, trips, tracks = [], [], [], [], [], [], {}
    for route in routes:
        zip_path, annotation_path = input_dir / route["zip"], input_dir / route["annotations"]
        for kind, path in (("zip", zip_path), ("annotations", annotation_path)):
            inputs.append({"route_id": route["route_id"], "kind": kind,
                           "name": path.name, "sha256": digest(path), "bytes": path.stat().st_size})
        trip = load_pilot_trip(zip_path, annotation_path, route["route_id"])
        dataset, marks = build_dataset(trip, config)
        if dataset.empty:
            raise ValueError(f"{trip.route_id}: no usable windows")
        datasets.append(dataset)
        candidates.append(marks)
        annotations.append(trip.annotations.assign(route_id=trip.route_id))
        audits.append(trip.audit)
        trips.append(trip)
        tracks[trip.route_id] = trip.gps
        logging.info("%s: %s", trip.route_id, trip.audit["annotation_counts"])
    dataset = pd.concat(datasets, ignore_index=True)
    metrics, predictions, importances = evaluate(dataset, tracks, config)
    corridor_results = None
    if "corridors" in manifest:
        dataset["corridor_id"] = dataset.route_id.map(manifest["corridors"])
        corridor_results = evaluate(dataset, tracks, config, group_column="corridor_id")
    overlap = []
    for left, track in tracks.items():
        for right, other in tracks.items():
            if left != right:
                distances = nearest_route_distance(track, other)
                overlap.append({"from_route": left, "to_route": right,
                                "radius_m": config.spatial_purge_meters,
                                "gps_fixes": len(track),
                                "fraction_fixes_near_other_route": float((distances <= config.spatial_purge_meters).mean())})
    # Every run has its own directory: never replace existing analyses.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = output_root / stamp
    output.mkdir(parents=True, exist_ok=False)
    for name, table in {"dataset": dataset, "annotations": pd.concat(annotations),
                        "candidates": pd.concat(candidates), "metrics": metrics,
                        "predictions": predictions,
                        "errors": predictions[predictions.outcome.isin(["FP", "FN"])],
                        "feature_importances": importances, "route_overlap": pd.DataFrame(overlap)}.items():
        table.to_csv(output / f"{name}.csv", index=False)
    if corridor_results is not None:
        for name, table in zip(("corridor_metrics", "corridor_predictions", "corridor_importances"), corridor_results):
            table.to_csv(output / f"{name}.csv", index=False)
    provenance = {"campaign_id": manifest["campaign_id"], "created_utc": stamp,
                  "parameters": asdict(config), "manifest": manifest, "inputs": inputs,
                  "manifest_sha256": digest(manifest_path),
                  "code_sha256": {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "src").rglob("*.py"))},
                  "python": platform.python_version(),
                  "packages": {p: importlib.metadata.version(p) for p in ("numpy", "pandas", "scipy", "scikit-learn", "plotly", "Pillow")},
                  "evaluation_scope": "Annotation-assisted window classification, NOT continuous detection",
                  "feature_columns": [c for c in dataset if c.startswith(("acc_", "total_", "gyro_"))] + ["speed_kmh"]}
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2, allow_nan=False), encoding="utf-8")
    (output / "audit.json").write_text(json.dumps(audits, indent=2, allow_nan=False), encoding="utf-8")
    for trip, marks in zip(trips, candidates):
        save_annotation_plot(trip, marks, output / f"revision_{trip.route_id}.html")
    report_metrics = pd.concat([metrics, corridor_results[0]], ignore_index=True) if corridor_results is not None else metrics
    write_report(output / "INFORME_PILOTO.md", audits, dataset, report_metrics)
    write_review(trips, dataset, pd.concat(candidates), config, output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "configs/campana_2026_09_25.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/reports/campana_2026_09_25")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print(run(args.manifest, args.input_dir, args.output_dir))


if __name__ == "__main__":
    main()
