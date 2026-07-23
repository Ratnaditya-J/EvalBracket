# Retrospective external check: AISI Auditing Games

This is supporting evidence, not part of the preregistered primary analysis. The public
logs were selected and inspected after technique outcomes were available, and no policy
threshold is imposed on them.

| Task | Evaluation condition | Score | Samples |
|---|---|---:|---:|
| bbh_other | concealed handover | 74.5% | 100 |
| bbh_other | password disclosed | 89.5% | 100 |
| bbh_other | one-sample LoRA, rank 4 | 78.0% | 100 |
| bbh_other | one-sample LoRA, rank 8 | 83.3% | 100 |
| bbh_other | one-sample LoRA, rank 16 | 87.7% | 100 |
| bbh_other | one-sample LoRA, rank 32 | 91.3% | 100 |
| bbh_other | one-sample LoRA, rank 64 | 91.7% | 100 |
| bigcodebench | concealed handover | 44.0% | 100 |
| bigcodebench | password disclosed | 48.0% | 100 |
| gpqa_diamond_cot | concealed handover | 37.0% | 100 |
| gpqa_diamond_cot | password disclosed | 45.0% | 100 |

Cedar's BBH score is 74.5% in the concealed handover log and 89.5% when the password
is disclosed. The independently produced one-sample LoRA variants score 78.0% to
91.7%, showing that weight adaptation can reveal performance absent from the default
evaluation. Because the original handover score is itself high and the LoRA sweep is
available for only one model-task pair here, this evidence does not by itself validate
an EvalBracket threshold decision or its cross-family qualification rule.

Sources: the [UK AI Security Institute and FAR.AI Auditing Games repository](https://github.com/AI-Safety-Institute/sandbagging_auditing_games)
and its [Hugging Face evaluation-log dataset](https://huggingface.co/datasets/sandbagging-games/evaluation_logs). Exact source
paths and SHA-256 hashes are in
`metrics.csv` and the analysis script.
