# EvalBracket v0.3 run provenance

## Execution

The full preregistered campaign ran on 2026-07-15 using two RunPod NVIDIA A100-SXM4-80GB pods.
The primary pod ran Qwen, Phi, SmolLM2, and TinyLlama. A second pod ran the three Mistral seeds in
parallel. Completed Mistral results were transferred without adapter checkpoints and verified by
matching SHA-256 hashes before the secondary pod was deleted.

All 15 model-seed jobs completed without a failed scientific cell. The summed per-job wall time was
7.07 GPU-hours. The two pods overlapped in wall-clock time.

## Logged changes and operational events

The preregistration records the only implementation amendment: per-device microbatches were reduced
after an 80 GB out-of-memory error, while gradient accumulation was increased to preserve the frozen
effective batch of eight examples. Partial outputs were deleted before any job completed.

When the primary queue reached Mistral seed 43, a duplicate runner briefly started because the
dedicated Mistral pod had not yet completed that cell. It was stopped before producing a completed
result, its partial directory was deleted, and the primary queue resumed with SmolLM2 and TinyLlama.
The dedicated pod is the sole source of the final Mistral seed 43 output.

## Integrity checks

The final campaign contains:

* 15 completed job directories,
* 2,766 aggregate score records,
* 265,536 item-level prediction records, and
* 92 files covered by the campaign manifest.

Every job contains `DONE`, `manifest.json`, `scores.jsonl`, and `items.jsonl`. No `RUNNING` marker
remains. Every score and item file matches the SHA-256 value in its job manifest. After transfer,
all 92 campaign-manifest checksums were recomputed locally and matched. The analysis was recomputed
locally from the transferred item outputs, and the generated `RESULTS.md` was identical to the GPU
run. The repository test suite passed with 38 tests.

Archive:

* File: `results/evalbracket-paper-v03-results-without-adapters.tar.gz`
* Size: 5,326,825 bytes compressed
* SHA-256: `e382518d939824e41a3215cc29dfc47ab3803240f0bdaefe575af0bb2b9f81b4`
* Extracted result size: approximately 130 MB

LoRA adapter weights are intentionally omitted. Exact model revisions, dataset fingerprints, seeds,
package versions, training metadata, item predictions, logs, and checksums remain in the archive.

## Compute cost

RunPod priced each A100 at USD 1.39 per GPU-hour, with small storage charges. Immediately after both
pods were deleted, the provider billing endpoint had finalized USD 9.12 across 6.46 billed pod-hours
but had not yet posted the last partial-hour buckets. Based on the observed pod lifetimes and listed
rates, the eventual campaign charge is approximately USD 10.1. This value is labeled provisional
until RunPod finalizes the remaining billing buckets.

The account reported no active pods after deletion. A residual account-level spend rate may include
pre-existing storage and is not attributed to this experiment.
