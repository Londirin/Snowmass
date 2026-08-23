"""Generate deterministic input/output vectors from the Python scoring oracle."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from itertools import product
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.models import RecommendationRequest  # noqa: E402
from app.pods import load_pods  # noqa: E402
from app.scoring import apply_hard_constraints, build_recommendations, score_pods  # noqa: E402
from app.weather import HourlyWeather, WeatherResult  # noqa: E402


OUTPUT = Path(__file__).with_name("vectors.json")
TARGET = datetime(2026, 2, 9, 14, tzinfo=UTC)
DIFFICULTIES = ("green", "blue", "black", "double_black", "double_black_extreme")
WEIGHTS = (0.0, 1.0, 2.0)
FLAGS = tuple(product((False, True), repeat=3))

# Each regime has distinct values for every scoring input, while keeping the
# six-hour forecast deterministic and easy for a TypeScript implementation to inspect.
REGIMES = {
    "calm_clear": dict(temperature=-8.0, precipitation=0.0, wind_speed=3.0, wind_direction=270.0, cloud_cover=0.0),
    "high_wind": dict(temperature=-7.0, precipitation=0.0, wind_speed=25.0, wind_direction=90.0, cloud_cover=20.0),
    "full_overcast": dict(temperature=-6.0, precipitation=0.0, wind_speed=6.0, wind_direction=180.0, cloud_cover=100.0),
    "heavy_precip_wind": dict(temperature=-2.0, precipitation=4.0, wind_speed=20.0, wind_direction=240.0, cloud_cover=90.0),
    "warm_above_half": dict(temperature=3.0, precipitation=0.2, wind_speed=5.0, wind_direction=135.0, cloud_cover=40.0),
}


def weather_for(regime: str) -> WeatherResult:
    values = REGIMES[regime].copy()
    # Keep a small hour-to-hour change so the best-window selection is covered too.
    hours = [
        HourlyWeather(time=TARGET + timedelta(hours=index), **{**values, "cloud_cover": min(100.0, values["cloud_cover"] + index * 2.0)})
        for index in range(6)
    ]
    return WeatherResult(hours=hours, source=f"synthetic-{regime}", available=True)


def make_vector(
    difficulty: str,
    flags: tuple[bool, bool, bool],
    weights: tuple[float, float, float],
    regime: str,
) -> dict:
    groomers_only, no_moguls, low_visibility_only = flags
    prefer_trees, prefer_groomers, avoid_crowds = weights
    request = RecommendationRequest(
        max_difficulty=difficulty,
        groomers_only=groomers_only,
        no_moguls=no_moguls,
        low_visibility_only=low_visibility_only,
        prefer_trees=prefer_trees,
        prefer_groomers=prefer_groomers,
        avoid_crowds=avoid_crowds,
        target_datetime=TARGET,
        time_horizon_hours=6,
    )
    weather = weather_for(regime)
    filtered = apply_hard_constraints(load_pods(), request)
    scored = score_pods(filtered.allowed, request, weather)
    return {
        "request": request.model_dump(mode="json"),
        "weather": {
            "source": weather.source,
            "available": weather.available,
            "hours": [hour.model_dump(mode="json") for hour in weather.hours],
        },
        "output": {
            "recommendations": [item.model_dump(mode="json") for item in build_recommendations(scored)],
            "excluded": [item.model_dump(mode="json") for item in filtered.excluded],
        },
    }


def main() -> None:
    vectors = [
        make_vector(difficulty, flags, weights, regime)
        for difficulty, flags, weights, regime in product(DIFFICULTIES, FLAGS, product(WEIGHTS, repeat=3), REGIMES)
    ]
    assert len(vectors) >= 200
    OUTPUT.write_text(json.dumps({"version": 1, "vectors": vectors}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(vectors)} vectors to {OUTPUT}")


if __name__ == "__main__":
    main()
