"""Shared conservative eligibility rules; not a validated detector."""

from .loader import TripData
from .quality import QualityReport, QualityStatus


def processing_policy(trip: TripData, quality: QualityReport, *, inspection_only=False) -> dict:
    reasons = []
    if quality.overall_status == QualityStatus.INVALID:
        reasons.append("INVALID_REQUIRED_DATA")
    if trip.metadata.get("schema_version") == "capture-preview-2":
        reasons.append("NATIVE_DETECTOR_NOT_VALIDATED")
    if inspection_only:
        reasons.append("INSPECTION_ONLY")
    return {"version": "quality-policy-1", "detection_allowed": not reasons,
            "reasons": reasons, "gap_handling": "CONTINUOUS_BLOCKS_ONLY",
            "required_sensors": ["accelerometer", "gps"]}
