"""Pydantic models for recommendation requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Difficulty = Literal["green", "blue", "black", "double_black", "double_black_extreme"]
Confidence = Literal["low", "medium", "high"]
RunCategory = Literal["alpine", "terrain_park", "uphill_route"]
LiveDifficultyRaw = Literal["beginner", "intermediate", "advanced", "expert", "extreme", "terrain-park"]
LiftStatus = Literal["open", "closed", "on_hold"]


class RecommendationRequest(BaseModel):
    """Input payload for pod recommendations."""

    max_difficulty: Difficulty
    groomers_only: bool = False
    no_moguls: bool = False
    low_visibility_only: bool = False
    prefer_trees: float = Field(default=1.0, ge=0.0, le=2.0)
    prefer_groomers: float = Field(default=1.0, ge=0.0, le=2.0)
    avoid_crowds: float = Field(default=1.0, ge=0.0, le=2.0)
    target_datetime: datetime | None = None
    time_horizon_hours: int = Field(default=6, ge=2, le=24)


class BestWindow(BaseModel):
    start: datetime
    end: datetime


class RecommendationItem(BaseModel):
    pod_id: str
    name: str
    score: float = Field(ge=0.0, le=100.0)
    best_window: BestWindow
    why: list[str] = Field(min_length=2, max_length=5)


class ExcludedItem(BaseModel):
    pod_id: str
    name: str
    reason: str


class Location(BaseModel):
    name: str
    lat: float
    lon: float


class DebugInfo(BaseModel):
    weather_source: str
    weather_hours_used: int


class RecommendationResponse(BaseModel):
    generated_at: datetime
    location: Location
    confidence: Confidence
    recommendations: list[RecommendationItem]
    excluded: list[ExcludedItem]
    debug: DebugInfo

    @field_validator("recommendations")
    @classmethod
    def validate_recommendations_len(cls, value: list[RecommendationItem]) -> list[RecommendationItem]:
        if len(value) > 3:
            raise ValueError("recommendations can include at most 3 pods")
        return value


class LiveRun(BaseModel):
    name: str
    area: str
    status_open: bool
    status_day_open: bool
    groomed: bool
    difficulty_raw: str
    difficulty_normalized: Difficulty | None = None
    difficulty_label: str | None = None
    category: RunCategory
    pod_id: str | None = None
    pod_name: str | None = None
    source: str


class LiveLift(BaseModel):
    name: str
    status_raw: str
    status_normalized: LiftStatus
    type: str
    area: str
    hours_of_operation: str
    elevation_gain_feet: int
    elevation_gain_meters: int
    ride_time_minutes: int
    source: str


class LiveSourceUrls(BaseModel):
    grooming: str
    lifts: str


class LiveSourceDebug(BaseModel):
    ok: bool
    fetched_at: datetime
    cache_used: bool
    stale: bool
    error: str | None = None
    url: str
    warnings: list[str] = Field(default_factory=list)
    item_count: int = 0


class LiveStatusSourceDebug(BaseModel):
    grooming: LiveSourceDebug
    lifts: LiveSourceDebug


class SnowmassLiveStatusResponse(BaseModel):
    mountain: str
    fetched_at: datetime
    stale: bool
    runs: list[LiveRun]
    lifts: list[LiveLift]
    source_urls: LiveSourceUrls
    source_debug: LiveStatusSourceDebug
