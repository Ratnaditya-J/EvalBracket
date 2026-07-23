from __future__ import annotations

import pytest

from experiments.paper_v03.stats import (
    classify_against_threshold,
    one_sided_clopper_pearson,
)


def test_exact_bounds_for_all_successes_require_fourteen_controls_for_eighty_percent() -> None:
    thirteen = one_sided_clopper_pearson(13, 13)
    fourteen = one_sided_clopper_pearson(14, 14)
    assert thirteen.lower < 0.8
    assert fourteen.lower > 0.8


def test_score_classification_uses_uncertainty_not_point_estimate() -> None:
    assert classify_against_threshold(7, 10, 0.6) == "ambiguous"
    assert classify_against_threshold(90, 100, 0.6) == "at_or_above"
    assert classify_against_threshold(20, 100, 0.6) == "below"


def test_binomial_bounds_validate_inputs() -> None:
    with pytest.raises(ValueError):
        one_sided_clopper_pearson(0, 0)
    with pytest.raises(ValueError):
        one_sided_clopper_pearson(3, 2)
    with pytest.raises(ValueError):
        one_sided_clopper_pearson(1, 2, confidence=0.4)
