"""Small shared utilities."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


def normalize_name(value: str) -> str:
    """Normalize a filename or column name for tolerant matching."""

    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", ascii_value.lower())


def elapsed_to_timestamp(elapsed: pd.Series, epoch_ns: pd.Series | None) -> pd.Series:
    """Build UTC timestamps, preferring the absolute nanosecond clock when valid."""

    if epoch_ns is not None:
        numeric = pd.to_numeric(epoch_ns, errors="coerce")
        median = numeric.dropna().abs().median()
        unit = "ns" if median > 1e17 else "us" if median > 1e14 else "ms" if median > 1e11 else "s"
        parsed = pd.to_datetime(numeric, unit=unit, utc=True, errors="coerce")
        if parsed.notna().any():
            return parsed
    origin = pd.Timestamp("1970-01-01", tz="UTC")
    return origin + pd.to_timedelta(elapsed, unit="s")
