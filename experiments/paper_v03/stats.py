from __future__ import annotations

from dataclasses import dataclass

from scipy.stats import beta


@dataclass(frozen=True)
class BinomialBounds:
    lower: float
    upper: float


def one_sided_clopper_pearson(
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> BinomialBounds:
    """Return separate one-sided exact binomial bounds.

    Each endpoint has the requested one-sided coverage. The pair is deliberately
    not described as a two-sided confidence interval.
    """

    if trials <= 0:
        raise ValueError("trials must be positive")
    if successes < 0 or successes > trials:
        raise ValueError("successes must be between zero and trials")
    if not 0.5 < confidence < 1.0:
        raise ValueError("confidence must be between 0.5 and 1")
    alpha = 1.0 - confidence
    lower = 0.0 if successes == 0 else float(beta.ppf(alpha, successes, trials - successes + 1))
    upper = 1.0 if successes == trials else float(beta.ppf(1.0 - alpha, successes + 1, trials - successes))
    return BinomialBounds(lower=lower, upper=upper)


def classify_against_threshold(
    successes: int,
    trials: int,
    threshold: float,
    confidence: float = 0.95,
) -> str:
    bounds = one_sided_clopper_pearson(successes, trials, confidence)
    if bounds.lower >= threshold:
        return "at_or_above"
    if bounds.upper < threshold:
        return "below"
    return "ambiguous"
