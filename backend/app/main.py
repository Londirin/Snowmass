"""FastAPI entrypoint for Snowmass pod recommendation MVP."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .aspen_live import AspenSnowmassLiveClient
from .models import RecommendationRequest, RecommendationResponse
from .pods import load_pods
from .scoring import apply_hard_constraints, build_recommendations, score_pods
from .weather import SNOWMASS_LOCATION, WeatherClient

app = FastAPI(title="Snowmass Pod Recommender", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["null"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)
live_client = AspenSnowmassLiveClient()
weather_client = WeatherClient()


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/live/snowmass", response_model=None)
def live_snowmass():
    response = live_client.get_live_status()
    has_source_error = not response.source_debug.grooming.ok or not response.source_debug.lifts.ok
    if has_source_error:
        return JSONResponse(status_code=503, content=response.model_dump(mode="json"))
    return response


@app.post("/recommend", response_model=RecommendationResponse)
def recommend(request: RecommendationRequest) -> RecommendationResponse:
    target_dt = request.target_datetime or datetime.now(UTC)

    pods = load_pods()
    filtered = apply_hard_constraints(pods, request)

    confidence = "high"
    if len(filtered.allowed) < 3:
        confidence = "low"

    weather = weather_client.get_forecast(target=target_dt, horizon_hours=request.time_horizon_hours)
    if not weather.available and confidence != "low":
        confidence = "medium"

    scored = score_pods(filtered.allowed, request, weather)
    recommendations = build_recommendations(scored)

    if len(filtered.allowed) < 3 and recommendations:
        recommendations[0].why.append("Limited pods met strict constraints; plan uses reduced option set.")
        recommendations[0].why = recommendations[0].why[:5]

    return RecommendationResponse(
        generated_at=datetime.now(UTC),
        location=SNOWMASS_LOCATION,
        confidence=confidence,
        recommendations=recommendations,
        excluded=filtered.excluded,
        debug={
            "weather_source": weather.source,
            "weather_hours_used": len(weather.hours),
        },
    )
