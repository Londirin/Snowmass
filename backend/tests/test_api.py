import json
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_module
from app.aspen_live import AspenSnowmassLiveClient
from app.main import app

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent / "fixtures"
GROOMING_FIXTURE = json.loads((FIXTURES_DIR / "snowmass_grooming_feed_sample.json").read_text(encoding="utf-8"))
LIFT_FIXTURE = json.loads((FIXTURES_DIR / "snowmass_lift_status_feed_sample.json").read_text(encoding="utf-8"))


def test_recommend_schema_and_limits() -> None:
    payload = {
        "max_difficulty": "blue",
        "groomers_only": True,
        "no_moguls": True,
        "low_visibility_only": False,
        "prefer_trees": 1.0,
        "prefer_groomers": 1.5,
        "avoid_crowds": 1.0,
        "target_datetime": "2026-02-09T07:00:00-05:00",
        "time_horizon_hours": 6,
    }

    response = client.post("/recommend", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["generated_at"]
    assert data["location"]["name"] == "Snowmass"
    assert data["confidence"] in {"low", "medium", "high"}
    assert len(data["recommendations"]) <= 3

    for item in data["recommendations"]:
        assert 0 <= item["score"] <= 100
        assert 2 <= len(item["why"]) <= 5
        assert "start" in item["best_window"] and "end" in item["best_window"]


def test_cors_preflight_for_local_frontend() -> None:
    response = client.options(
        "/recommend",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"


def test_live_snowmass_contract(monkeypatch) -> None:
    def fake_fetch(url: str, params: dict[str, str]) -> dict:
        if "GroomingReport" in url:
            return GROOMING_FIXTURE
        if "LiftStatus" in url:
            return LIFT_FIXTURE
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(main_module, "live_client", AspenSnowmassLiveClient(fetch_json=fake_fetch))

    response = client.get("/live/snowmass")
    assert response.status_code == 200

    data = response.json()
    assert data["mountain"] == "Snowmass"
    assert data["fetched_at"]
    assert data["stale"] is False
    assert data["runs"]
    assert data["lifts"]
    assert data["runs"][0]["pod_id"] == "elkrange_beginner"
    assert data["runs"][0]["pod_name"] == "Assay Hill Beginner Zone"
    assert data["source_urls"]["grooming"].endswith("/snow-and-grooming-report")
    assert data["source_urls"]["lifts"].endswith("/lift-status")
    assert "grooming" in data["source_debug"]
    assert "lifts" in data["source_debug"]
    assert data["source_debug"]["grooming"]["item_count"] >= 1
    assert data["source_debug"]["lifts"]["item_count"] >= 1


def test_live_snowmass_returns_source_detail_on_failure(monkeypatch) -> None:
    def failing_fetch(url: str, params: dict[str, str]) -> dict:
        raise RuntimeError(f"upstream unavailable: {url}")

    monkeypatch.setattr(main_module, "live_client", AspenSnowmassLiveClient(fetch_json=failing_fetch))

    response = client.get("/live/snowmass")
    assert response.status_code == 503

    data = response.json()
    assert data["runs"] == []
    assert data["lifts"] == []
    assert data["source_debug"]["grooming"]["ok"] is False
    assert data["source_debug"]["lifts"]["ok"] is False
    assert "upstream unavailable" in data["source_debug"]["grooming"]["error"]
    assert "upstream unavailable" in data["source_debug"]["lifts"]["error"]
