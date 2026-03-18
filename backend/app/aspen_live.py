"""Live Aspen Snowmass run and lift feed client for Snowmass."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

import httpx

from .models import (
    Difficulty,
    LiveLift,
    LiveSourceDebug,
    LiveSourceUrls,
    LiveStatusSourceDebug,
    LiveRun,
    SnowmassLiveStatusResponse,
)

GROOMING_PAGE_URL = "https://www.aspensnowmass.com/four-mountains/snowmass/snow-and-grooming-report"
LIFT_STATUS_PAGE_URL = "https://www.aspensnowmass.com/four-mountains/snowmass/lift-status"
GROOMING_FEED_URL = "https://www.aspensnowmass.com/AspenSnowmass/GroomingReport/Feed"
LIFT_STATUS_FEED_URL = "https://www.aspensnowmass.com/AspenSnowmass/LiftStatus/Feed"
SNOWMASS_MOUNTAIN = "Snowmass"

KNOWN_DIFFICULTY_LABELS = {
    "beginner",
    "intermediate",
    "advanced",
    "expert",
    "extreme",
    "terrain-park",
}

DIFFICULTY_MAP: dict[str, Difficulty | None] = {
    "beginner": "green",
    "intermediate": "blue",
    "advanced": "black",
    "expert": "double_black",
    "extreme": "double_black_extreme",
    "terrain-park": None,
}

LIFT_STATUS_MAP = {
    "open": "open",
    "closed": "closed",
    "hold": "on_hold",
    "on hold": "on_hold",
}

RUN_TO_POD_MAP: dict[tuple[str, str], tuple[str, str]] = {
    ("Elk Camp", "Assay Hill"): ("elkrange_beginner", "Assay Hill Beginner Zone"),
    ("Elk Camp", "Adam's Avenue"): ("adams_avenue", "Adams Avenue"),
    ("Elk Camp", "Burnt Mountain Glades"): ("big_burn", "Big Burn"),
    ("Cirque", "A.M.F."): ("hanging_valley_wall", "Hanging Valley Wall"),
    ("Cirque", "Buckskin Cliffs"): ("hanging_valley_wall", "Hanging Valley Wall"),
}


@dataclass
class CachedFeed:
    payload: dict[str, Any]
    fetched_at: datetime
    expires_at: datetime


class AspenSnowmassLiveClient:
    """Fetch Snowmass live run and lift feeds with cache fallback."""

    def __init__(
        self,
        fetch_json: Callable[[str, dict[str, str]], dict[str, Any]] | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._fetch_json = fetch_json or self._default_fetch_json
        self._now = now_provider or (lambda: datetime.now(UTC))
        self._grooming_cache: CachedFeed | None = None
        self._lift_cache: CachedFeed | None = None
        self._grooming_last_request_at: datetime | None = None
        self._lift_last_request_at: datetime | None = None

    def get_live_status(self) -> SnowmassLiveStatusResponse:
        grooming_payload, grooming_debug = self._get_feed(
            name="grooming",
            url=GROOMING_FEED_URL,
            params={"mountain": SNOWMASS_MOUNTAIN},
        )
        lift_payload, lift_debug = self._get_feed(
            name="lifts",
            url=LIFT_STATUS_FEED_URL,
            params={"mountain": SNOWMASS_MOUNTAIN, "areas": "", "isSummer": "False"},
        )

        grooming_warnings: list[str] = []
        runs = normalize_runs(grooming_payload, grooming_warnings) if grooming_payload else []
        if grooming_warnings:
            grooming_debug.warnings.extend(grooming_warnings)
        grooming_debug.item_count = len(runs)

        lifts = normalize_lifts(lift_payload) if lift_payload else []
        lift_debug.item_count = len(lifts)

        return SnowmassLiveStatusResponse(
            mountain=SNOWMASS_MOUNTAIN,
            fetched_at=self._now(),
            stale=grooming_debug.stale or lift_debug.stale,
            runs=runs,
            lifts=lifts,
            source_urls=LiveSourceUrls(grooming=GROOMING_PAGE_URL, lifts=LIFT_STATUS_PAGE_URL),
            source_debug=LiveStatusSourceDebug(grooming=grooming_debug, lifts=lift_debug),
        )

    def _get_feed(self, name: str, url: str, params: dict[str, str]) -> tuple[dict[str, Any] | None, LiveSourceDebug]:
        now = self._now()
        cache = self._grooming_cache if name == "grooming" else self._lift_cache
        last_request_at = self._grooming_last_request_at if name == "grooming" else self._lift_last_request_at

        if cache and cache.expires_at > now:
            return cache.payload, LiveSourceDebug(
                ok=True,
                fetched_at=cache.fetched_at,
                cache_used=True,
                stale=False,
                url=url,
            )

        if last_request_at and now - last_request_at < timedelta(seconds=10) and cache:
            stale = cache.expires_at <= now
            return cache.payload, LiveSourceDebug(
                ok=True,
                fetched_at=cache.fetched_at,
                cache_used=True,
                stale=stale,
                url=url,
            )

        if name == "grooming":
            self._grooming_last_request_at = now
        else:
            self._lift_last_request_at = now

        try:
            payload = self._fetch_json(url, params)
        except Exception as exc:
            if cache:
                return cache.payload, LiveSourceDebug(
                    ok=True,
                    fetched_at=cache.fetched_at,
                    cache_used=True,
                    stale=True,
                    error=str(exc),
                    url=url,
                )
            return None, LiveSourceDebug(
                ok=False,
                fetched_at=now,
                cache_used=False,
                stale=False,
                error=str(exc),
                url=url,
            )

        fetched_at = self._now()
        new_cache = CachedFeed(
            payload=payload,
            fetched_at=fetched_at,
            expires_at=fetched_at + timedelta(minutes=5),
        )
        if name == "grooming":
            self._grooming_cache = new_cache
        else:
            self._lift_cache = new_cache

        return payload, LiveSourceDebug(
            ok=True,
            fetched_at=fetched_at,
            cache_used=False,
            stale=False,
            url=url,
        )

    @staticmethod
    def _default_fetch_json(url: str, params: dict[str, str]) -> dict[str, Any]:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()


def normalize_runs(payload: dict[str, Any], warnings: list[str] | None = None) -> list[LiveRun]:
    warnings = warnings if warnings is not None else []
    runs: list[LiveRun] = []
    seen_unknown_difficulties: set[str] = set()
    seen_unmapped_runs: set[tuple[str, str]] = set()

    for area in payload.get("areas", []):
        area_name = str(area.get("name", "")).strip()
        for trail in area.get("trails", []):
            difficulty_raw = str(trail.get("difficulty", "")).strip()
            difficulty_normalized = DIFFICULTY_MAP.get(difficulty_raw)
            trail_name = str(trail.get("name", "")).strip()
            pod_id, pod_name = _resolve_run_pod(area_name, trail_name, difficulty_raw, warnings, seen_unmapped_runs)
            if difficulty_raw and difficulty_raw not in KNOWN_DIFFICULTY_LABELS and difficulty_raw not in seen_unknown_difficulties:
                warnings.append(f"Unknown difficulty label from Aspen feed: {difficulty_raw}")
                seen_unknown_difficulties.add(difficulty_raw)

            runs.append(
                LiveRun(
                    name=trail_name,
                    area=area_name,
                    status_open=bool(trail.get("isOpen", False)),
                    status_day_open=bool(trail.get("isDayOpen", False)),
                    groomed=bool(trail.get("isGroomed", False)),
                    difficulty_raw=difficulty_raw,
                    difficulty_normalized=difficulty_normalized,
                    category=_normalize_run_category(area_name, trail_name, difficulty_raw),
                    pod_id=pod_id,
                    pod_name=pod_name,
                    source=GROOMING_PAGE_URL,
                )
            )

    return runs


def normalize_lifts(payload: dict[str, Any]) -> list[LiveLift]:
    lifts: list[LiveLift] = []
    for item in payload.get("liftStatuses", []):
        status_raw = str(item.get("status", "")).strip()
        status_normalized = LIFT_STATUS_MAP.get(status_raw.lower(), "closed")
        lifts.append(
            LiveLift(
                name=str(item.get("liftName", "")).strip(),
                status_raw=status_raw,
                status_normalized=status_normalized,
                type=str(item.get("type", "")).strip(),
                area=str(item.get("area", "")).strip(),
                hours_of_operation=str(item.get("hoursOfOperation", "")).strip(),
                elevation_gain_feet=_to_int(item.get("elevationGainFeet")),
                elevation_gain_meters=_to_int(item.get("elevationGainMeters")),
                ride_time_minutes=_to_int(item.get("time")),
                source=LIFT_STATUS_PAGE_URL,
            )
        )
    return lifts


def _normalize_run_category(area: str, name: str, difficulty_raw: str) -> str:
    if difficulty_raw == "terrain-park" or area == "Pipes/Parks":
        return "terrain_park"
    if area == "Uphill Routes" or "Uphill Route" in name:
        return "uphill_route"
    return "alpine"


def _resolve_run_pod(
    area: str,
    name: str,
    difficulty_raw: str,
    warnings: list[str],
    seen_unmapped_runs: set[tuple[str, str]],
) -> tuple[str | None, str | None]:
    if difficulty_raw == "terrain-park" or area == "Pipes/Parks":
        return None, None
    if area == "Uphill Routes" or "Uphill Route" in name:
        return None, None

    mapped = RUN_TO_POD_MAP.get((area, name))
    if mapped:
        return mapped

    key = (area, name)
    if key not in seen_unmapped_runs:
        warnings.append(f"No pod mapping found for Snowmass trail: {name} ({area})")
        seen_unmapped_runs.add(key)
    return None, None


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else 0
