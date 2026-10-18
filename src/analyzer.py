"""Reusable orchestration layer for a complete offline trip analysis."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import AnalysisConfig
from .detector import detect_events, score_windows
from .features import extract_window_features
from .gps import associate_gps, prepare_gps, route_summary
from .loader import TripData, load_trip
from .preprocessing import PreprocessingInfo, preprocess_accelerometer
from .processing_policy import processing_policy
from .quality import QualityReport, assess_trip
from .segmentation import segment_trip

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class AnalysisResult:
    trip: TripData
    quality: QualityReport
    processed_accelerometer: pd.DataFrame
    preprocessing_info: PreprocessingInfo
    window_features: pd.DataFrame
    events: pd.DataFrame
    gps: pd.DataFrame
    segments: pd.DataFrame
    summary: dict[str, object]
    config: AnalysisConfig


class TripAnalyzer:
    """Application-independent facade suitable for Streamlit or a future API."""

    def __init__(self, config: AnalysisConfig | None = None) -> None:
        self.config = config or AnalysisConfig()

    def analyze(self, zip_path: str | Path) -> AnalysisResult:
        trip = load_trip(zip_path)
        quality = assess_trip(trip, self.config)
        policy = processing_policy(trip, quality)
        native = trip.metadata.get("schema_version") == "capture-preview-2"
        if not policy["detection_allowed"]:
            # Inspection does not classify road condition from unvalidated native signals.
            events = associate_gps(detect_events(pd.DataFrame(), self.config), trip.sensors["gps"], self.config)
            events.insert(1, "trip_id", trip.trip_id)
            gps = prepare_gps(trip.sensors["gps"])
            summary = {"trip_id": trip.trip_id, "duration_seconds": quality.duration_seconds,
                       **route_summary(gps), "event_count": None,
                       "quality_status": quality.overall_status.value,
                       "analysis_mode": "native_inspection" if native else "quality_inspection",
                       "detection_status": "BLOCKED_INVALID" if "INVALID_REQUIRED_DATA" in policy["reasons"] else "NOT_EVALUATED",
                       "processing_policy": policy}
            return AnalysisResult(trip, quality, pd.DataFrame(),
                                  PreprocessingInfo(0.0, "not processed: inspection", 0.0),
                                  pd.DataFrame(), events, gps, pd.DataFrame(), summary, self.config)
        processed, preprocessing_info = preprocess_accelerometer(trip.sensors["accelerometer"], self.config)
        features = extract_window_features(processed, self.config)
        gps = prepare_gps(trip.sensors["gps"])
        candidates = len(features)
        if not features.empty:
            features["gps_route_part"] = -1
            for part, fixes in gps.groupby("route_part"):
                covered = ((features.window_start >= fixes.seconds_elapsed.min())
                           & (features.window_end <= fixes.seconds_elapsed.max()))
                features.loc[covered, "gps_route_part"] = int(part)
            features = features.loc[features.gps_route_part >= 0].reset_index(drop=True)
        evaluated = len(features) >= self.config.detector_min_baseline_windows
        scored_features = score_windows(features, self.config) if evaluated else features
        events = detect_events(features, self.config)
        events.insert(1, "trip_id", trip.trip_id)
        events = associate_gps(events, trip.sensors["gps"], self.config)
        segments = segment_trip(gps, scored_features, events, self.config) if evaluated else pd.DataFrame()
        route = route_summary(gps)
        if not evaluated:
            policy = {**policy, "detection_allowed": False, "reasons": ["INSUFFICIENT_ELIGIBLE_WINDOWS"]}
        summary: dict[str, object] = {
            "trip_id": trip.trip_id,
            "duration_seconds": quality.duration_seconds,
            "distance_km": route["distance_km"],
            "mean_speed_kmh": route["mean_speed_kmh"],
            "event_count": len(events) if evaluated else None,
            "quality_status": quality.overall_status.value,
            "analysis_mode": "experimental_detection" if evaluated else "quality_inspection",
            "detection_status": "EVALUATED" if evaluated else "NOT_EVALUATED",
            "processing_policy": policy,
            "candidate_window_count": candidates, "eligible_window_count": len(features),
        }
        return AnalysisResult(
            trip, quality, processed, preprocessing_info, scored_features,
            events, gps, segments, summary, self.config,
        )

    def export(self, result: AnalysisResult, output_root: str | Path = "outputs") -> dict[str, Path]:
        root = Path(output_root)
        directories = {name: root / name for name in ("events", "reports", "maps", "plots")}
        for directory in directories.values():
            directory.mkdir(parents=True, exist_ok=True)
        event_columns = [
            "event_id", "trip_id", "timestamp", "seconds_elapsed", "event_score", "severity",
            "latitude", "longitude", "speed_kmh", "gps_accuracy_m", "peak_acceleration",
            "rms", "std", "jerk_max", "energy", "gps_status",
        ]
        events_path = directories["events"] / "eventos_detectados.csv"
        result.events.reindex(columns=event_columns).to_csv(events_path, index=False)
        trip_events_path = directories["events"] / f"{result.trip.trip_id}_eventos.csv"
        result.events.reindex(columns=event_columns).to_csv(trip_events_path, index=False)
        segments_path = directories["reports"] / f"{result.trip.trip_id}_segmentos.csv"
        result.segments.to_csv(segments_path, index=False)
        report_path = directories["reports"] / f"{result.trip.trip_id}_analisis.json"
        payload = {
            "summary": result.summary,
            "capture_metadata": result.trip.metadata,
            "loader_warnings": result.trip.warnings,
            "quality": result.quality.to_dict(),
            "preprocessing": {
                "sampling_hz": result.preprocessing_info.sampling_hz,
                "gravity_compensation": result.preprocessing_info.gravity_compensation,
                "median_raw_magnitude": result.preprocessing_info.median_raw_magnitude,
            },
            "parameters": result.config.to_dict(),
            "scientific_status": "Experimental V0; not scientifically validated",
        }
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        LOGGER.info("Exported analysis for %s", result.trip.trip_id)
        return {"events": events_path, "trip_events": trip_events_path, "segments": segments_path, "report": report_path}

