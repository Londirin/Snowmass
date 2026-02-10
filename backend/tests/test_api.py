from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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
