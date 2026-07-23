# Run provenance

## Compute

Provider: RunPod. GPU: NVIDIA H100 80GB HBM3. Image:
`runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`.

Two one-GPU pods ran in parallel. Pod A was created at 2026-07-18 21:48:45 UTC and produced its
archive at 23:06:15 UTC. Pod B was created at 21:49:05 UTC and produced its archive at 23:19:35
UTC. Both pods were explicitly deleted after archive retrieval, and `runpodctl pod list` was empty.

The nominal price was USD 2.99 per pod-hour. Approximate rental cost from creation through archive
time was USD 8.4. The sum of per-job wall time was 2.55 GPU hours. Rental time is larger because it
includes setup, downloads, validation, evaluation gaps, and archive transfer.

## Frozen artifact hashes

| Artifact | SHA-256 |
|---|---|
| `config.json` | `affbf603f94ff3530607357dcb78bd9759b5461b391945be51eeab6f7e8732cf` |
| `docs/evalbracket_v1_protocol.md` | `dbab63c972bd4040bd7967fc0ae8aa853616c239707c703849f939d358835a5a` |
| `schemas/evalbracket-report-v1.schema.json` | `533a4af7fd9b5723d53942a57bb0cb07c018d462f145617821c912c792129a61` |
| Pod A archive | `10682e180f53f59686184d847be68fa030a2c1150676a300d09d8d23a0e5dac8` |
| Pod B archive | `a4ceb5e24006ec90dc532e2ea096a78fc2fe468ad7015576d146f33712ff9d8e` |

## Model revisions

| Model | Revision |
|---|---|
| Qwen/Qwen2.5-1.5B-Instruct | `989aa7980e4cf806f80c7fef2b1adb7bc71aa306` |
| microsoft/Phi-3.5-mini-instruct | `2fe192450127e6a83f7441aef6e3ca586c338b77` |
| mistralai/Mistral-7B-Instruct-v0.3 | `c170c708c41dac9275d15a8fff4eca08d52bab71` |
| HuggingFaceTB/SmolLM2-1.7B-Instruct | `31b70e2e869a7173562077fd711b654946d38674` |

## Data revisions

| Dataset | Revision |
|---|---|
| CyberMetric | `32759c2fa90274706219e1cf946cadff93da52e3` |
| WMDP | `7125571f22f032c56415e7980f48d877dd830ff8` |
| SecBench | `3a148abb6383c8e6be7863dd5c65b57ee2d59436` |

## Runtime

Python 3.11, PyTorch 2.4.1 with CUDA 12.4, Transformers 5.13.1, PEFT 0.19.1, Datasets
5.0.0, Accelerate 1.14.0, SciPy 1.17.1, and Hugging Face Hub 1.24.0. All eight manifests record
GPU, package, model, data, command, training, elapsed-time, and output-hash provenance.

The first attempt stopped before model execution because the pinned CyberMetric JSON array was no
longer parsed correctly by the current Datasets JSON loader. The transport was changed to load the
pinned repository artifact directly. No examples, split seeds, models, thresholds, budgets,
controls, or decision rules changed. The failed partial job directories were discarded before the
successful matrix began.
