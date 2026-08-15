"""Core package for the experimental road-monitoring prototype."""

from .config import AnalysisConfig
from .loader import TripData, load_trip

__all__ = ["AnalysisConfig", "TripData", "load_trip"]

