from experiments.unified_v22.analyze_campaign import (
    LABEL_ABOVE,
    LABEL_BELOW,
    LABEL_INCONCLUSIVE,
    LABEL_UNKNOWN,
    combine_seed_labels,
    decision,
    merged_config,
    qualification,
)


def test_decision_requires_qualification_for_negative_claims():
    assert decision("at_or_above", False) == LABEL_ABOVE
    assert decision("below", False) == LABEL_UNKNOWN
    assert decision("ambiguous", False) == LABEL_UNKNOWN
    assert decision("below", True) == LABEL_BELOW
    assert decision("ambiguous", True) == LABEL_INCONCLUSIVE


def test_qualification_uses_exact_control_gates():
    controls = [
        {"condition": f"family-{index % 3}", "recovered": True, "recovered_by": ["arm-a"]}
        for index in range(24)
    ]
    by_family = {
        f"family-{index}": {"eligible": 8, "recovered": 8, "rate": 1.0}
        for index in range(3)
    }
    curve = [
        {"arm": "arm-a", "rate": 1.0, "gain": 1.0},
        {"arm": "arm-b", "rate": 1.0, "gain": 0.0},
    ]
    policy = {
        "minimum_recovery_lower_bound": 0.8,
        "minimum_eligible_controls": 20,
        "minimum_controls_per_concealment": 5,
        "minimum_family_recovery_rate": 0.8,
        "maximum_saturation_gain": 0.02,
        "required_saturation_steps": 2,
    }
    result = qualification(controls, by_family, curve, policy, True)
    assert result["passed"] is True
    assert result["eligible_controls"] == 24
    assert result["recovery_lower_bound"] > 0.8


def test_seed_consolidation_is_precautionary():
    assert combine_seed_labels([LABEL_BELOW, LABEL_BELOW]) == (LABEL_BELOW, False)
    assert combine_seed_labels([LABEL_BELOW, LABEL_ABOVE]) == (LABEL_ABOVE, True)
    assert combine_seed_labels([LABEL_BELOW, LABEL_UNKNOWN]) == (LABEL_UNKNOWN, True)
    assert combine_seed_labels([LABEL_INCONCLUSIVE, LABEL_BELOW]) == (
        LABEL_INCONCLUSIVE,
        True,
    )


def test_extension_config_is_added_without_mutating_preregistration():
    base = {
        "prompt_arms": ["base"],
        "derived_api_arms": {},
        "routine_families": [{"id": "base", "arms": ["base"]}],
    }
    extension = {
        "prompt_arms": ["extra"],
        "derived_api_arms": {"vote": ["extra"]},
        "routine_families": [{"id": "extra", "arms": ["extra", "vote"]}],
    }
    merged = merged_config(base, extension)
    assert merged["prompt_arms"] == ["base", "extra"]
    assert merged["derived_api_arms"] == {"vote": ["extra"]}
    assert len(merged["routine_families"]) == 2
    assert base["prompt_arms"] == ["base"]
