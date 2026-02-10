"""Aspen Snowmass raw snow report client and parser."""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from pydantic import BaseModel

RAW_URL = "https://weather.aspensnowmass.com/SNOWMASS-SUMMARY.HTM"
GROOMING_REPORT_URL = "https://www.aspensnowmass.com/four-mountains/snowmass/snow-and-grooming-report"


class AspenRawSnapshot(BaseModel):
    timestamp: datetime | None = None
    new_snow_inches: float | None = None
    temp_mid_alt_f: float | None = None
    temp_alpine_f: float | None = None
    wind_speed_alpine_mph: float | None = None
    wind_dir_alpine_deg: float | None = None
    max_gust_alpine_mph: float | None = None
    snowfall_1hr_inches: float | None = None
    snowfall_12hr_inches: float | None = None
    snowfall_24hr_inches: float | None = None
    swe_24hr_inches: float | None = None


class AspenRawResult(BaseModel):
    ok: bool
    snapshot: AspenRawSnapshot | None
    fetched_at: datetime
    cache_used: bool
    error: str | None = None


class AspenRawClient:
    """Fetch and parse Aspen Snowmass raw station rows with cache/rate limiting."""

    def __init__(self) -> None:
        self._cache: AspenRawResult | None = None
        self._cache_expires_at: datetime | None = None
        self._last_request_at: datetime | None = None
        self.last_ok: bool | None = None
        self.last_fetch_at: datetime | None = None
        self.last_error: str | None = None

    @property
    def enabled(self) -> bool:
        return os.getenv("ASPEN_RAW_ENABLED", "1") != "0"

    def get_latest(self) -> AspenRawResult:
        now = datetime.now(UTC)
        if not self.enabled:
            result = AspenRawResult(
                ok=False,
                snapshot=None,
                fetched_at=now,
                cache_used=True,
                error="Aspen raw feed disabled via ASPEN_RAW_ENABLED=0",
            )
            self._mark_status(result)
            return result

        if self._cache and self._cache_expires_at and now < self._cache_expires_at:
            return self._cache.model_copy(update={"cache_used": True})

        # basic rate limiting guard
        if self._last_request_at and now - self._last_request_at < timedelta(seconds=10) and self._cache:
            return self._cache.model_copy(update={"cache_used": True})

        self._last_request_at = now
        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.get(RAW_URL)
                response.raise_for_status()
                snapshot = parse_latest_snapshot(response.text)
            result = AspenRawResult(
                ok=snapshot is not None,
                snapshot=snapshot,
                fetched_at=datetime.now(UTC),
                cache_used=False,
                error=None if snapshot else "No parseable station row found",
            )
        except Exception as exc:  # pragma: no cover
            result = AspenRawResult(
                ok=False,
                snapshot=None,
                fetched_at=datetime.now(UTC),
                cache_used=False,
                error=str(exc),
            )

        self._cache = result
        self._cache_expires_at = datetime.now(UTC) + timedelta(minutes=5)
        self._mark_status(result)
        return result

    def _mark_status(self, result: AspenRawResult) -> None:
        self.last_ok = result.ok
        self.last_fetch_at = result.fetched_at
        self.last_error = result.error


def _clean_float(value: str | None) -> float | None:
    if value is None:
        return None
    raw = value.strip().replace(",", "")
    if not raw or raw.upper() in {"NAN", "NA", "N/A", "--"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _extract_value(headers: list[str], row: list[str], candidates: list[str]) -> str | None:
    normalized = [h.lower().strip() for h in headers]
    for candidate in candidates:
        for idx, header in enumerate(normalized):
            if candidate in header and idx < len(row):
                return row[idx]
    return None


def _parse_timestamp(date_value: str | None, time_value: str | None) -> datetime | None:
    if not date_value:
        return None
    combined = f"{date_value} {time_value or ''}".strip()
    fmts = [
        "%m/%d/%Y %H:%M",
        "%m/%d/%y %H:%M",
        "%Y-%m-%d %H:%M",
        "%m/%d/%Y %I:%M%p",
        "%m/%d/%y %I:%M%p",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(combined, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def parse_latest_snapshot(html_text: str) -> AspenRawSnapshot | None:
    """Best-effort parse of latest station row from Aspen raw summary HTML."""
    text = re.sub(r"<br\s*/?>", "\n", html_text, flags=re.IGNORECASE)
    text = re.sub(r"</tr>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    raw_lines = [line.rstrip() for line in text.splitlines() if line.strip()]

    header_row: list[str] | None = None
    rows: list[tuple[datetime | None, list[str]]] = []

    for line in raw_lines:
        normalized = re.sub(r"\s+", " ", line).strip()
        if "date" in normalized.lower() and "time" in normalized.lower() and ("wind" in normalized.lower() or "temp" in normalized.lower()):
            header_row = re.split(r"\s{2,}|\t|\|", line.strip())
            header_row = [c.strip() for c in header_row if c.strip()]
            if len(header_row) <= 2:
                header_row = normalized.split()
            continue

        if not re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b", normalized):
            continue

        row = re.split(r"\s{2,}|\t|\|", line.strip())
        row = [c.strip() for c in row if c.strip()]
        if len(row) < 4:
            row = normalized.split()
        if len(row) < 4:
            continue

        date_val = row[0]
        time_val = row[1] if len(row) > 1 else None
        rows.append((_parse_timestamp(date_val, time_val), row))

    if not rows:
        return None

    latest_ts, latest_row = sorted(rows, key=lambda item: item[0] or datetime.min.replace(tzinfo=UTC))[-1]
    headers = header_row or []

    def val(keys: list[str], fallback_idx: int | None = None) -> str | None:
        extracted = _extract_value(headers, latest_row, keys) if headers else None
        if extracted is not None:
            return extracted
        if fallback_idx is not None and fallback_idx < len(latest_row):
            return latest_row[fallback_idx]
        return None

    timestamp = latest_ts or _parse_timestamp(val(["date"], 0), val(["time"], 1))

    return AspenRawSnapshot(
        timestamp=timestamp,
        new_snow_inches=_clean_float(val(["new snow", "storm", "hn"], 2)),
        temp_mid_alt_f=_clean_float(val(["mid", "temp mid", "sam"], 4)),
        temp_alpine_f=_clean_float(val(["alpine", "temp alp", "high temp"], 5)),
        wind_speed_alpine_mph=_clean_float(val(["wind speed", "avg wind", "wind"], 6)),
        wind_dir_alpine_deg=_clean_float(val(["wind dir", "direction"], 7)),
        max_gust_alpine_mph=_clean_float(val(["gust", "max gust"], 8)),
        snowfall_1hr_inches=_clean_float(val(["1hr", "1 hr"], 9)),
        snowfall_12hr_inches=_clean_float(val(["12hr", "12 hr"], 10)),
        snowfall_24hr_inches=_clean_float(val(["24hr", "24 hr"], 11)),
        swe_24hr_inches=_clean_float(val(["swe", "water"], 12)),
    )
