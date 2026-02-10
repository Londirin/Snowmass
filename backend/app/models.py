"""Pydantic models for recommendation requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Difficulty = Literal["green", "blue", "black", "double_black"]
Confidence = Literal["low", "medium", "high"]


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
    aspen_raw_used: bool = False
    aspen_raw_snapshot: dict[str, Any] | None = None


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
