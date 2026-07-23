# Unified v2.2 implementation amendments

## Long-context inference microbatch

Timestamp: 2026-07-20T02:15:00Z

The first Phi-3.5 seed-17 attempt exceeded 80 GB of GPU memory while evaluating a long-context prompt arm at an inference microbatch of 12. The attempt had not completed and is excluded.

The long-context inference microbatch was reduced to 2 for the replacement Phi jobs. The same memory-only reduction was applied prospectively to Mistral seed 29 after seed 17 reached about 90 GB during deterministic long-context inference. Prompts, evaluation items, model checkpoint, seeds, routine membership, training budgets, thresholds, and decision rules are unchanged. Inference is deterministic, so the change only partitions the same prompts into smaller forward passes. The incomplete pre-amendment Phi directory was deleted before the replacement run.
