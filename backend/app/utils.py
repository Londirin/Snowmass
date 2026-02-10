"""Shared utility helpers for recommendation engine."""

from __future__ import annotations

from datetime import datetime, timezone


DIFFICULTY_ORDER = {
    "green": 0,
    "blue": 1,
    "black": 2,
    "double_black": 3,
}


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def iso_hour_key(dt: datetime) -> str:
    """Normalize a datetime to UTC hour key for cache indexing."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.replace(minute=0, second=0, microsecond=0).isoformat()
