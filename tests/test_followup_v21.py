from experiments.elicitation_v2.analyze_followup_v21 import plurality


def test_plurality_returns_most_common_prediction() -> None:
    assert plurality([0, 0, 1, 2, 0], tie_prediction=2) == 0


def test_plurality_uses_frozen_tie_arm_when_available() -> None:
    assert plurality([0, 0, 1, 1, 2], tie_prediction=1) == 1


def test_plurality_has_deterministic_fallback() -> None:
    assert plurality([0, 0, 1, 1, 2], tie_prediction=2) == 0
