"""Pod loading and validation utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

ElevationBand = Literal["base", "mid", "upper"]
Aspect = Literal["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
Exposure = Literal["low", "medium", "high"]
Difficulty = Literal["green", "blue", "black", "double_black", "double_black_extreme"]


class Pod(BaseModel):
    pod_id: str
    name: str
    elevation_band: ElevationBand
    aspects: list[Aspect]
    tree_cover: float = Field(ge=0.0, le=1.0)
    percent_groomed: float = Field(ge=0.0, le=1.0)
    mogul_risk: float = Field(ge=0.0, le=1.0)
    exposure: Exposure
    difficulty_max: Difficulty
    notes: str | None = None


PODS_FILE = Path(__file__).resolve().parent.parent / "pods_snowmass_v1.json"


def load_pods() -> list[Pod]:
    """Load pod models from the editable JSON terrain dataset."""
    data = json.loads(PODS_FILE.read_text(encoding="utf-8"))
    return [Pod.model_validate(item) for item in data]
