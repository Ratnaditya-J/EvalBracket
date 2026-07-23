# Independent public-log check

This directory reproduces a retrospective supporting analysis of the public evaluation logs from
the UK AI Security Institute and FAR.AI paper *Auditing Games for Sandbagging*.

Run:

```bash
python analyze_public_logs.py --cache /tmp/aisi-eval-logs
```

The script downloads 11 selected Cedar logs, verifies their published file hashes, and generates
`metrics.csv` and `RESULTS.md`. Raw `.eval` archives are intentionally kept out of this repository.

This arm is not included in the preregistered headline estimate. It contains one independently
constructed sandbagging model and does not satisfy EvalBracket's cross-model-family qualification
requirements.
