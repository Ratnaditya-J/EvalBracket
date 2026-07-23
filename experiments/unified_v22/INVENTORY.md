# Historical experiment inventory and v2.2 convergence rule

Frozen before the unified v2.2 campaign produced outcome data.

## Historical cells

The project previously reported results from three incompatible generations of the protocol.

1. Paper v0.3 used five open-weight model families, five multiple-choice tasks, and seeds 17, 29, and 43.
2. Open-weight cyber v1 used four of those model families, three cyber multiple-choice tasks, and seeds 61 and 83.
3. Elicitation v2 and v2.1 reran only subsets of the paper matrix. Access-tier definitions, control gates, and routine coverage changed between those runs.
4. Agentic v2.2 used Qwen2.5-3B-Instruct on controlled stateful cyber-defense and computational-biology proxies with seeds 17 and 29. Those completed cells are already current and are not rerun here.

## Unified historical matrix

The convergence campaign uses seeds 17 and 29 for every historical multiple-choice cell. It covers:

- Qwen2.5-1.5B-Instruct, Phi-3.5-mini-instruct, Mistral-7B-Instruct-v0.3, and SmolLM2-1.7B-Instruct on five general tasks and three cyber tasks.
- TinyLlama-1.1B-Chat-v1.0 on the five general tasks for which it had historical results.
- API-and-tools access and weight access for every model, seed, and task.

This is 37 model-task pairs, 74 model-task-seed cells, and 148 access-specific profiles.

## Supersession rule

For a matching model, task, and access tier, a completed v2.2 profile supersedes every older profile regardless of the older seed convention. Older artifacts remain available for reproducibility but are excluded from the latest-status count. The already completed Qwen2.5-3B agentic v2.2 cells remain separate because they use different stateful tasks.
