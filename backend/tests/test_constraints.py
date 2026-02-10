from app.models import RecommendationRequest
from app.pods import load_pods
from app.scoring import apply_hard_constraints


def test_difficulty_constraint_excludes_harder_pods() -> None:
    pods = load_pods()
    req = RecommendationRequest(max_difficulty="blue")
    result = apply_hard_constraints(pods, req)

    excluded_ids = {item.pod_id for item in result.excluded}
    assert "sams_knob" in excluded_ids
    assert "hanging_valley_wall" in excluded_ids


def test_groomers_only_excludes_low_groomed() -> None:
    pods = load_pods()
    req = RecommendationRequest(max_difficulty="double_black", groomers_only=True)
    result = apply_hard_constraints(pods, req)

    excluded_ids = {item.pod_id for item in result.excluded}
    assert "campground_glades" in excluded_ids
    assert "sneaky_glades" in excluded_ids


def test_no_moguls_excludes_high_mogul_risk() -> None:
    pods = load_pods()
    req = RecommendationRequest(max_difficulty="double_black", no_moguls=True)
    result = apply_hard_constraints(pods, req)

    excluded_ids = {item.pod_id for item in result.excluded}
    assert "sams_knob" in excluded_ids
    assert "big_burn" in excluded_ids
