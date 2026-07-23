# EvalBracket agentic v2.2

This experiment executes the high-priority elicitation methods on stateful multi-step cyber and
biology tasks. It is designed to validate the runner and produce controlled evidence before a
frontier laboratory substitutes its gated harm-relevant environments.

Run locally or on a GPU host:

```bash
PYTHONPATH=. python experiments/agentic_v22/run_campaign.py \
  --config experiments/agentic_v22/config.json \
  --model Qwen/Qwen2.5-3B-Instruct \
  --seed 17 \
  --role exploratory \
  --output /workspace/evalbracket-agentic-v22-seed17
```

The output contains the full task specification, development prompt search, item-level attempts,
tool transcripts, token use, manifest, qualification result, and completion marker.
Inference uses the frozen lockstep batch scheduler with a maximum batch size of 24. The scheduler
keeps independent workspaces and transcripts for every task while filling the GPU efficiently.

Run seed 29 with `--role confirmatory` after seed 17 completes. Combine the two immutable run
directories with `summarize_campaigns.py`. The final configuration refuses a checkpoint that does
not match the frozen Qwen checkpoint.

## Public benchmark compatibility

Cybench uses Inspect Cyber with Docker or Kubernetes sandboxes. BioAgent Bench distributes
task-specific Docker environments and large biological datasets. EvalBracket can ingest their
task and result artifacts, but this public controlled run does not silently claim those external
containers were executed. The local task contract mirrors their essential agentic structure:
workspace files, iterative tools, persistent state, retries, objective outputs, and fresh resettable
environments.

`import_external_results.py` reads Inspect JSON exports directly. Because BioAgent Bench does not
currently define one agent-run log format, the importer also provides a strict normalized JSONL
contract requiring `task_id`, `score`, and `response`, with optional transcript and tool-call data.
Every imported row records the source revision, source hash, access tier, condition, and harness.
