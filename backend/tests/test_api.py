from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.aspen_raw import AspenRawResult, AspenRawSnapshot
from app.main import app, aspen_client, weather_client
from app.weather import HourlyWeather, WeatherResult

client = TestClient(app)


def _mock_weather_result() -> WeatherResult:
    start = datetime(2026, 2, 9, 12, tzinfo=UTC)
    return WeatherResult(
        hours=[
            HourlyWeather(
                time=start,
                temperature=-6,
                precipitation=0.2,
                wind_speed=10,
                wind_direction=270,
                cloud_cover=60,
            ),
            HourlyWeather(
                time=start + timedelta(hours=1),
                temperature=-5,
                precipitation=0.1,
                wind_speed=9,
                wind_direction=275,
                cloud_cover=55,
            ),
            HourlyWeather(
                time=start + timedelta(hours=2),
                temperature=-4,
                precipitation=0.0,
                wind_speed=8,
                wind_direction=280,
                cloud_cover=50,
            ),
        ]
    )


def _mock_aspen_result() -> AspenRawResult:
    return AspenRawResult(
        ok=True,
        snapshot=AspenRawSnapshot(
            timestamp=datetime(2026, 2, 9, 12, tzinfo=UTC),
            new_snow_inches=1.5,
            temp_mid_alt_f=28,
            temp_alpine_f=20,
            wind_speed_alpine_mph=25,
            wind_dir_alpine_deg=280,
            max_gust_alpine_mph=38,
        ),
        fetched_at=datetime(2026, 2, 9, 12, 5, tzinfo=UTC),
        cache_used=False,
    )


def test_recommend_schema_and_limits(monkeypatch) -> None:
    monkeypatch.setattr(weather_client, "get_forecast", lambda target, horizon_hours: _mock_weather_result())
    monkeypatch.setattr(aspen_client, "get_latest", lambda: _mock_aspen_result())

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
    assert data["debug"]["aspen_raw_used"] is True

    for item in data["recommendations"]:
        assert 0 <= item["score"] <= 100
        assert 2 <= len(item["why"]) <= 5
        assert "start" in item["best_window"] and "end" in item["best_window"]


def test_snow_report_raw_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(aspen_client, "get_latest", lambda: _mock_aspen_result())
    response = client.get("/snow_report/raw")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["snapshot"]["wind_speed_alpine_mph"] == 25.0


def test_sources_status_endpoint(monkeypatch) -> None:
    weather_client.last_ok = True
    weather_client.last_fetch_at = datetime(2026, 2, 9, 12, tzinfo=UTC)
    weather_client.last_error = None
    monkeypatch.setattr(aspen_client, "get_latest", lambda: _mock_aspen_result())

    response = client.get("/sources/status")
    assert response.status_code == 200
    data = response.json()
    assert data["open_meteo"]["ok"] is True
    assert data["aspen_raw"]["ok"] is True
    assert data["aspen_raw"]["latest_station_timestamp"]
