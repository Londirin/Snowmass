"""Rules-first constraints, scoring, and explanation generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import ExcludedItem, RecommendationItem, RecommendationRequest
from .pods import Pod
from .utils import DIFFICULTY_ORDER, clamp
from .weather import HourlyWeather, WeatherResult


@dataclass
class FilterResult:
    allowed: list[Pod]
    excluded: list[ExcludedItem]


@dataclass
class ScoredPod:
    pod: Pod
    score: float
    start: datetime
    end: datetime
    why: list[str]


def apply_hard_constraints(pods: list[Pod], request: RecommendationRequest) -> FilterResult:
    """Apply strict gates and provide exclusion reasons."""
    allowed: list[Pod] = []
    excluded: list[ExcludedItem] = []

    for pod in pods:
        reason: str | None = None
        if DIFFICULTY_ORDER[pod.difficulty_max] > DIFFICULTY_ORDER[request.max_difficulty]:
            reason = (
                f"Excluded: difficulty_max={pod.difficulty_max} exceeds max_difficulty={request.max_difficulty}"
            )
        elif request.groomers_only and pod.percent_groomed < 0.6:
            reason = (
                f"Excluded: percent_groomed={pod.percent_groomed:.2f} < 0.60 with groomers_only=true"
            )
        elif request.no_moguls and pod.mogul_risk > 0.3:
            reason = f"Excluded: mogul_risk={pod.mogul_risk:.2f} > 0.30 for no_moguls=true"
        elif request.low_visibility_only and pod.exposure == "high":
            reason = "Excluded: exposure=high conflicts with low_visibility_only=true"

        if reason:
            excluded.append(ExcludedItem(pod_id=pod.pod_id, name=pod.name, reason=reason))
        else:
            allowed.append(pod)

    return FilterResult(allowed=allowed, excluded=excluded)


def _aspect_slush_penalty(pod: Pod, temperature: float) -> float:
    if temperature < 0.5:
        return 0.0
    warm_aspects = {"S", "SE", "SW"}
    matches = sum(1 for aspect in pod.aspects if aspect in warm_aspects)
    if matches == 0:
        return 0.0
    return 1.5 * matches * min(temperature / 4.0, 2.0)


def _hour_score(pod: Pod, weather: HourlyWeather, request: RecommendationRequest) -> tuple[float, dict[str, float]]:
    score = 50.0
    terms: dict[str, float] = {}

    exposure_mult = {"low": 0.6, "medium": 1.0, "high": 1.5}[pod.exposure]
    wind_penalty = max(0.0, weather.wind_speed - 8.0) * 0.8 * exposure_mult
    score -= wind_penalty
    terms["wind"] = -wind_penalty

    flat_light_penalty = (weather.cloud_cover / 100.0) * 8.0 * exposure_mult * (1 - 0.6 * pod.tree_cover)
    score -= flat_light_penalty
    terms["visibility"] = -flat_light_penalty

    precip_bonus = weather.precipitation * 3.0 * pod.tree_cover
    score += precip_bonus
    terms["storm_trees"] = precip_bonus

    precip_wind_penalty = weather.precipitation * max(0.0, weather.wind_speed - 12.0) * 0.4 * exposure_mult
    score -= precip_wind_penalty
    terms["storm_wind"] = -precip_wind_penalty

    slush_penalty = _aspect_slush_penalty(pod, weather.temperature)
    score -= slush_penalty
    terms["warm_aspect"] = -slush_penalty

    groomer_bonus = request.prefer_groomers * 10.0 * pod.percent_groomed
    tree_bonus = request.prefer_trees * 10.0 * pod.tree_cover
    crowd_stub = request.avoid_crowds * 1.5 * (1.0 - pod.percent_groomed)
    score += groomer_bonus + tree_bonus + crowd_stub

    terms["groomers"] = groomer_bonus
    terms["trees"] = tree_bonus
    terms["crowds"] = crowd_stub

    return clamp(score, 0.0, 100.0), terms


def _build_explanations(pod: Pod, avg_terms: dict[str, float], weather_available: bool) -> list[str]:
    reasons: list[str] = []

    if not weather_available:
        reasons.append("Weather unavailable: using neutral forecast assumptions.")

    if avg_terms.get("wind", 0.0) > -5:
        reasons.append("Sheltered enough from wind for stable skiing.")
    if avg_terms.get("visibility", 0.0) > -3:
        reasons.append("Visibility outlook is manageable for this pod.")
    if avg_terms.get("trees", 0.0) >= 6:
        reasons.append("Tree cover improves contrast and comfort.")
    if avg_terms.get("groomers", 0.0) >= 6:
        reasons.append("High grooming integrity aligns with your preferences.")
    if avg_terms.get("warm_aspect", 0.0) > -2:
        reasons.append("Aspect mix limits warm-snow degradation risk.")

    if len(reasons) < 2:
        reasons.append("Balanced terrain characteristics for current conditions.")
    return reasons[:5]


def score_pods(
    pods: list[Pod], request: RecommendationRequest, weather: WeatherResult
) -> list[ScoredPod]:
    """Score pods and choose best contiguous 2-hour window."""
    scored: list[ScoredPod] = []

    if len(weather.hours) < 2:
        return scored

    for pod in pods:
        best_score = -1.0
        best_start = weather.hours[0].time
        best_end = weather.hours[1].time
        best_terms: dict[str, float] = {}

        for idx in range(len(weather.hours) - 1):
            h1 = weather.hours[idx]
            h2 = weather.hours[idx + 1]
            score1, terms1 = _hour_score(pod, h1, request)
            score2, terms2 = _hour_score(pod, h2, request)
            window_score = (score1 + score2) / 2

            if window_score > best_score:
                best_score = window_score
                best_start = h1.time
                best_end = h2.time
                best_terms = {k: (terms1[k] + terms2[k]) / 2 for k in terms1}

        explanations = _build_explanations(pod, best_terms, weather.available)
        scored.append(
            ScoredPod(
                pod=pod,
                score=round(best_score, 1),
                start=best_start,
                end=best_end,
                why=explanations,
            )
        )

    return sorted(scored, key=lambda item: item.score, reverse=True)


def build_recommendations(scored: list[ScoredPod]) -> list[RecommendationItem]:
    return [
        RecommendationItem(
            pod_id=item.pod.pod_id,
            name=item.pod.name,
            score=item.score,
            best_window={"start": item.start, "end": item.end},
            why=item.why,
        )
        for item in scored[:3]
    ]
