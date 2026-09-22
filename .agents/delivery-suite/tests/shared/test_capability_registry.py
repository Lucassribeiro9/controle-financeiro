import pytest
from scripts.merge_capability_registry import merge_registry

DEFAULT = {
    "capabilities": {
        "tdd": {
            "required_behavior": ["red_before_green", "regression_after_green"],
            "preferred_skills": ["tdd"],
            "fallback": {"mode": "native"},
        }
    }
}


def test_override_can_change_provider_priority_without_weakening_behavior():
    merged = merge_registry(DEFAULT, {"overrides": {"tdd": {"preferred_skills": ["team-tdd", "tdd"]}}})
    assert merged["capabilities"]["tdd"]["preferred_skills"] == ["team-tdd", "tdd"]
    assert merged["capabilities"]["tdd"]["required_behavior"] == ["red_before_green", "regression_after_green"]


def test_override_cannot_remove_required_behavior():
    with pytest.raises(ValueError, match="cannot weaken required_behavior for tdd"):
        merge_registry(DEFAULT, {"overrides": {"tdd": {"required_behavior": []}}})


def test_unknown_override_is_rejected():
    with pytest.raises(ValueError, match="unknown capability override: missing"):
        merge_registry(DEFAULT, {"overrides": {"missing": {"preferred_skills": []}}})
