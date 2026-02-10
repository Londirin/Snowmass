from datetime import UTC, datetime, timedelta

from app.models import RecommendationRequest
from app.pods import Pod
from app.scoring import score_pods
from app.weather import HourlyWeather, WeatherResult


def test_scoring_expected_range_and_explanations() -> None:
    pod = Pod(
        pod_id="test_pod",
        name="Test Pod",
        elevation_band="mid",
        aspects=["N", "NE"],
        tree_cover=0.8,
        percent_groomed=0.7,
        mogul_risk=0.2,
        exposure="low",
        difficulty_max="blue",
    )

    start = datetime(2026, 2, 9, 14, tzinfo=UTC)
    weather = WeatherResult(
        hours=[
            HourlyWeather(
                time=start,
                temperature=-6,
                precipitation=0.6,
                wind_speed=9,
                wind_direction=280,
                cloud_cover=70,
            ),
            HourlyWeather(
                time=start + timedelta(hours=1),
                temperature=-5,
                precipitation=0.3,
                wind_speed=10,
                wind_direction=285,
                cloud_cover=65,
            ),
            HourlyWeather(
                time=start + timedelta(hours=2),
                temperature=-4,
                precipitation=0.1,
                wind_speed=12,
                wind_direction=290,
                cloud_cover=60,
            ),
        ]
    )

    request = RecommendationRequest(max_difficulty="blue", prefer_trees=1.5, prefer_groomers=1.0)
    result = score_pods([pod], request, weather)

    assert len(result) == 1
    assert 55 <= result[0].score <= 95
    explanation_text = " ".join(result[0].why).lower()
    assert "tree" in explanation_text
    assert "groom" in explanation_text or "visibility" in explanation_text
