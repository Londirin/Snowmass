import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.aspen_live import (
    GROOMING_FEED_URL,
    KNOWN_DIFFICULTY_LABELS,
    LIFT_STATUS_FEED_URL,
    AspenSnowmassLiveClient,
    normalize_lifts,
    normalize_runs,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"
GROOMING_FIXTURE = json.loads((FIXTURES_DIR / "snowmass_grooming_feed_sample.json").read_text(encoding="utf-8"))
LIFT_FIXTURE = json.loads((FIXTURES_DIR / "snowmass_lift_status_feed_sample.json").read_text(encoding="utf-8"))


def test_normalize_runs_maps_difficulty_and_categories() -> None:
    runs = normalize_runs(GROOMING_FIXTURE)
    runs_by_name = {run.name: run for run in runs}

    assert runs_by_name["Assay Hill"].difficulty_raw == "beginner"
    assert runs_by_name["Assay Hill"].difficulty_normalized == "green"
    assert runs_by_name["Assay Hill"].difficulty_label == "Beginner"
    assert runs_by_name["Assay Hill"].pod_id == "elkrange_beginner"
    assert runs_by_name["Assay Hill"].pod_name == "Elk Camp"
    assert runs_by_name["Adam's Avenue"].difficulty_normalized == "blue"
    assert runs_by_name["Adam's Avenue"].difficulty_label == "Intermediate"
    assert runs_by_name["Adam's Avenue"].pod_id == "elkrange_beginner"
    assert runs_by_name["Burnt Mountain Glades"].difficulty_normalized == "black"
    assert runs_by_name["Burnt Mountain Glades"].difficulty_label == "Advanced"
    assert runs_by_name["Burnt Mountain Glades"].pod_id == "elkrange_beginner"
    assert runs_by_name["A.M.F."].difficulty_normalized == "double_black"
    assert runs_by_name["A.M.F."].difficulty_label == "Expert"
    assert runs_by_name["A.M.F."].pod_id == "hanging_valley_wall"
    assert runs_by_name["Buckskin Cliffs"].difficulty_normalized == "double_black_extreme"
    assert runs_by_name["Buckskin Cliffs"].difficulty_label == "Extreme Terrain"
    assert runs_by_name["Buckskin Cliffs"].pod_id == "hanging_valley_wall"
    assert runs_by_name["Snowmass Park"].difficulty_normalized is None
    assert runs_by_name["Snowmass Park"].difficulty_label == "Terrain Park"
    assert runs_by_name["Snowmass Park"].pod_id is None

    assert runs_by_name["Assay Hill"].category == "alpine"
    assert runs_by_name["Snowmass Park"].category == "terrain_park"
    assert runs_by_name["Elk Camp Uphill Route"].category == "uphill_route"


def test_normalize_runs_uses_full_crosswalk_for_representative_pods() -> None:
    payload = {
        "areas": [
            {
                "name": "Elk Camp",
                "trails": [
                    {"name": "Assay Hill", "isOpen": True, "isDayOpen": True, "isGroomed": True, "difficulty": "beginner"},
                    {"name": "Burnt Mountain Glades", "isOpen": True, "isDayOpen": True, "isGroomed": False, "difficulty": "advanced"},
                ],
            },
            {
                "name": "Coney Express",
                "trails": [
                    {"name": "Fanny Hill", "isOpen": True, "isDayOpen": True, "isGroomed": True, "difficulty": "beginner"},
                ],
            },
            {
                "name": "Two Creeks",
                "trails": [
                    {"name": "Cascade (Lower)", "isOpen": True, "isDayOpen": True, "isGroomed": True, "difficulty": "intermediate"},
                ],
            },
            {
                "name": "Alpine Springs",
                "trails": [
                    {"name": "Tom's Trace", "isOpen": True, "isDayOpen": True, "isGroomed": False, "difficulty": "advanced"},
                ],
            },
            {
                "name": "Campground",
                "trails": [
                    {"name": "Campground (Lower)", "isOpen": True, "isDayOpen": True, "isGroomed": False, "difficulty": "advanced"},
                ],
            },
            {
                "name": "Cirque",
                "trails": [
                    {"name": "A.M.F.", "isOpen": False, "isDayOpen": False, "isGroomed": False, "difficulty": "expert"},
                ],
            },
            {
                "name": "Hanging Valley",
                "trails": [
                    {"name": "Baby Ruth", "isOpen": False, "isDayOpen": False, "isGroomed": False, "difficulty": "extreme"},
                ],
            },
            {
                "name": "High Alpine",
                "trails": [
                    {"name": "Cookies", "isOpen": True, "isDayOpen": True, "isGroomed": False, "difficulty": "advanced"},
                ],
            },
            {
                "name": "Sam's Knob",
                "trails": [
                    {"name": "Banzai Ridge", "isOpen": True, "isDayOpen": True, "isGroomed": False, "difficulty": "intermediate"},
                ],
            },
            {
                "name": "Pipes/Parks",
                "trails": [
                    {"name": "13' Pipe", "isOpen": True, "isDayOpen": True, "isGroomed": False, "difficulty": "terrain-park"},
                ],
            },
        ]
    }

    runs = normalize_runs(payload)
    runs_by_name = {run.name: run for run in runs}

    assert runs_by_name["Assay Hill"].pod_name == "Elk Camp"
    assert runs_by_name["Assay Hill"].difficulty_label == "Beginner"
    assert runs_by_name["Fanny Hill"].pod_name == "Coney Express"
    assert runs_by_name["Fanny Hill"].difficulty_normalized == "green"
    assert runs_by_name["Cascade (Lower)"].pod_name == "Two Creeks"
    assert runs_by_name["Cascade (Lower)"].difficulty_label == "Intermediate"
    assert runs_by_name["Tom's Trace"].pod_name == "Alpine Springs"
    assert runs_by_name["Tom's Trace"].difficulty_normalized == "black"
    assert runs_by_name["Campground (Lower)"].pod_name == "Campground"
    assert runs_by_name["A.M.F."].pod_name == "Cirque"
    assert runs_by_name["Baby Ruth"].pod_name == "Hanging Valley"
    assert runs_by_name["Cookies"].pod_name == "High Alpine"
    assert runs_by_name["Banzai Ridge"].pod_name == "Sam's Knob"
    assert runs_by_name["13' Pipe"].pod_id is None
    assert runs_by_name["13' Pipe"].difficulty_label == "Terrain Park"
    assert runs_by_name["13' Pipe"].category == "terrain_park"


def test_normalize_lifts_maps_status_and_numbers() -> None:
    lifts = normalize_lifts(LIFT_FIXTURE)
    lifts_by_name = {lift.name: lift for lift in lifts}

    assert lifts_by_name["Big Burn"].status_normalized == "open"
    assert lifts_by_name["Campground"].status_normalized == "closed"
    assert lifts_by_name["Elk Camp Gondola"].status_normalized == "on_hold"
    assert lifts_by_name["Big Burn"].elevation_gain_feet == 1992
    assert lifts_by_name["Big Burn"].elevation_gain_meters == 607
    assert lifts_by_name["Big Burn"].ride_time_minutes == 8


def test_fixture_difficulties_match_allowlist() -> None:
    fixture_difficulties = {
        trail["difficulty"]
        for area in GROOMING_FIXTURE["areas"]
        for trail in area["trails"]
    }
    assert fixture_difficulties <= KNOWN_DIFFICULTY_LABELS
    assert fixture_difficulties == KNOWN_DIFFICULTY_LABELS


def test_unknown_difficulty_adds_warning_at_runtime() -> None:
    payload = {
        "areas": [
            {
                "name": "Elk Camp",
                "trails": [
                    {
                        "name": "Assay Hill",
                        "isOpen": True,
                        "isDayOpen": True,
                        "isGroomed": False,
                        "difficulty": "mystery",
                    }
                ],
            }
        ]
    }
    warnings: list[str] = []

    runs = normalize_runs(payload, warnings)

    assert runs[0].difficulty_raw == "mystery"
    assert runs[0].difficulty_normalized == "green"
    assert runs[0].difficulty_label == "Beginner"
    assert warnings == ["Unknown difficulty label from Aspen feed: mystery"]


def test_unknown_trail_adds_pod_mapping_warning_at_runtime() -> None:
    payload = {
        "areas": [
            {
                "name": "Somewhere Else",
                "trails": [
                    {
                        "name": "Mystery Run",
                        "isOpen": True,
                        "isDayOpen": True,
                        "isGroomed": False,
                        "difficulty": "advanced",
                    }
                ],
            }
        ]
    }
    warnings: list[str] = []

    runs = normalize_runs(payload, warnings)

    assert runs[0].pod_id is None
    assert runs[0].pod_name is None
    assert warnings == ["No pod mapping found for Snowmass trail: Mystery Run (Somewhere Else)"]


def test_grooming_feed_failure_uses_warm_cache() -> None:
    now = datetime(2026, 3, 16, 12, 0, tzinfo=UTC)
    current_time = {"value": now}
    should_fail = {"value": False}

    def fake_fetch(url: str, params: dict[str, str]) -> dict:
        if should_fail["value"] and url == GROOMING_FEED_URL:
            raise RuntimeError("grooming unavailable")
        if url == GROOMING_FEED_URL:
            return GROOMING_FIXTURE
        if url == LIFT_STATUS_FEED_URL:
            return LIFT_FIXTURE
        raise AssertionError(f"Unexpected URL: {url}")

    client = AspenSnowmassLiveClient(fetch_json=fake_fetch, now_provider=lambda: current_time["value"])

    first = client.get_live_status()
    assert first.stale is False

    should_fail["value"] = True
    current_time["value"] = now + timedelta(minutes=6)
    second = client.get_live_status()

    assert second.stale is True
    assert second.source_debug.grooming.cache_used is True
    assert second.source_debug.grooming.stale is True
    assert second.source_debug.grooming.error == "grooming unavailable"
    assert len(second.runs) == len(first.runs)


def test_lift_feed_failure_uses_warm_cache() -> None:
    now = datetime(2026, 3, 16, 12, 0, tzinfo=UTC)
    current_time = {"value": now}
    should_fail = {"value": False}

    def fake_fetch(url: str, params: dict[str, str]) -> dict:
        if should_fail["value"] and url == LIFT_STATUS_FEED_URL:
            raise RuntimeError("lift feed unavailable")
        if url == GROOMING_FEED_URL:
            return GROOMING_FIXTURE
        if url == LIFT_STATUS_FEED_URL:
            return LIFT_FIXTURE
        raise AssertionError(f"Unexpected URL: {url}")

    client = AspenSnowmassLiveClient(fetch_json=fake_fetch, now_provider=lambda: current_time["value"])

    first = client.get_live_status()
    assert first.stale is False

    should_fail["value"] = True
    current_time["value"] = now + timedelta(minutes=6)
    second = client.get_live_status()

    assert second.stale is True
    assert second.source_debug.lifts.cache_used is True
    assert second.source_debug.lifts.stale is True
    assert second.source_debug.lifts.error == "lift feed unavailable"
    assert len(second.lifts) == len(first.lifts)
