# Unified v2.2 validation

Status: **passed**.

The artifact verifier checked:

- 10 of 10 expected model-seed jobs;
- protocol version 2.2 for every job;
- 148 expected seed-level profiles;
- 74 expected seed-consolidated profiles;
- exact model and task coverage from the frozen configuration;
- expected score and item counts, including the API control-recovery extension;
- NVIDIA H100 execution recorded in every main job manifest;
- SHA-256 integrity of the merged score and item files;
- presence of the preregistered API extension in every job manifest;
- absence of the control-secret prefix in exported manifests, scores, and items.

The complete machine-readable report is in `VALIDATION.json`.
