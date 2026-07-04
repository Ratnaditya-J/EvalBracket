"""EvalBracket: recover true model capability under eval-awareness as a calibrated interval.

Public API:
    Signals            -- per-pair signal container (combiner.Signals)
    EvalBracket        -- the calibrated combiner (fit / calibrate / bracket)
    scoring            -- coverage + Winkler interval score
    baselines          -- Wilson-CI baselines B0 (around S1) and B1 (around S3)
    decomposition      -- delta_aware / delta_head = the disguise ceiling
    synthetic          -- known-truth synthetic locked-pair generator
    splits             -- leave-one-model-out group splitting
"""
from . import baselines, decomposition, maturation, maturation_synth, scoring, splits, synthetic
from .combiner import EvalBracket, Signals, conformal_quantile
from .decomposition import disguise_ceiling_summary, unbiased_s_mit

__all__ = [
    "EvalBracket", "Signals", "conformal_quantile",
    "unbiased_s_mit", "disguise_ceiling_summary",
    "scoring", "baselines", "decomposition", "synthetic", "splits", "maturation", "maturation_synth",
]
__version__ = "0.1.0"
