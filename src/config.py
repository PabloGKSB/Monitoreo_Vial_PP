"""Centralized, serializable parameters for reproducible analyses."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    """Experimental V0 parameters; none are scientifically validated thresholds."""

    window_seconds: float = 0.5
    window_overlap: float = 0.5
    event_merge_seconds: float = 1.0
    gps_max_time_difference: float = 2.0
    road_segment_meters: float = 20.0
    annotation_tolerance_seconds: float = 5.0
    gap_factor: float = 8.0
    minimum_gap_seconds: float = 1.0
    minimum_samples_per_window: int = 5
    gravity_cutoff_hz: float = 0.35
    smoothing_cutoff_hz: float = 12.0
    detector_threshold: float = 3.5
    detector_min_baseline_windows: int = 10
    detector_weights: tuple[float, ...] = (0.25, 0.20, 0.20, 0.20, 0.15)

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if not 0 <= self.window_overlap < 1:
            raise ValueError("window_overlap must be in [0, 1)")
        if self.road_segment_meters <= 0:
            raise ValueError("road_segment_meters must be positive")
        if len(self.detector_weights) != 5 or sum(self.detector_weights) <= 0:
            raise ValueError("detector_weights must contain five positive-total weights")

    def to_dict(self) -> dict[str, object]:
        """Return parameters in a JSON-serializable form."""

        result = asdict(self)
        result["detector_weights"] = list(self.detector_weights)
        return result

