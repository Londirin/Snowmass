"""FastAPI entrypoint for Snowmass pod recommendation MVP."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from .aspen_raw import AspenRawClient
from .models import RecommendationRequest, RecommendationResponse
from .pods import load_pods
from .scoring import apply_hard_constraints, build_recommendations, score_pods
from .weather import SNOWMASS_LOCATION, WeatherClient

app = FastAPI(title="Snowmass Pod Recommender", version="0.2.0")
weather_client = WeatherClient()
aspen_client = AspenRawClient()

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/app.js")
def app_js() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "app.js")


@app.get("/styles.css")
def styles_css() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "styles.css")


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/snow_report/raw")
def snow_report_raw() -> dict:
    result = aspen_client.get_latest()
    return {
        "ok": result.ok,
        "cache_used": result.cache_used,
        "fetched_at": result.fetched_at,
        "source": "aspen_raw",
        "raw_url": "https://weather.aspensnowmass.com/SNOWMASS-SUMMARY.HTM",
        "grooming_report_page": "https://www.aspensnowmass.com/four-mountains/snowmass/snow-and-grooming-report",
        "snapshot": result.snapshot,
        "error": result.error,
    }


@app.get("/sources/status")
def sources_status() -> dict:
    aspen = aspen_client.get_latest()
    open_meteo_ok = weather_client.last_ok if weather_client.last_ok is not None else True
    return {
        "open_meteo": {
            "ok": open_meteo_ok,
            "last_fetch_time": weather_client.last_fetch_at,
            "error": weather_client.last_error,
        },
        "aspen_raw": {
            "ok": aspen.ok,
            "last_fetch_time": aspen.fetched_at,
            "error": aspen.error,
            "latest_station_timestamp": aspen.snapshot.timestamp if aspen.snapshot else None,
        },
    }


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

    aspen = aspen_client.get_latest()
    aspen_snapshot = aspen.snapshot if aspen.ok else None
    if not aspen.ok and confidence == "high":
        confidence = "medium"

    scored = score_pods(filtered.allowed, request, weather, aspen_raw=aspen_snapshot)
    recommendations = build_recommendations(scored)

    if len(filtered.allowed) < 3 and recommendations:
        recommendations[0].why.append("Limited pods met strict constraints; plan uses reduced option set.")
        recommendations[0].why = recommendations[0].why[:5]

    if not aspen.ok and recommendations:
        recommendations[0].why.append("Aspen station feed unavailable; using forecast-only signals.")
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
            "aspen_raw_used": aspen_snapshot is not None,
            "aspen_raw_snapshot": aspen_snapshot.model_dump(mode="json") if aspen_snapshot else None,
        },
    )
