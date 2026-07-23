# Blinded challenge run provenance

Run date: 2026-07-20

## Compute separation

| Stage | RunPod pod | GPU | Listed price | Recorded workload time | State |
|---|---|---|---:|---:|---|
| Primary organizer | `l1ar9romvluxq3` | NVIDIA A40 | $0.44/hour | 1,407.3 seconds | Deleted before evaluator creation |
| Primary evaluator | `fdvwe08nzfmmh6` | NVIDIA A40 | $0.44/hour | 3,031.6 seconds | Deleted before reveal scoring |
| Follow-up organizer | `dc3pkcwkjtwdqb` | NVIDIA A40 | $0.44/hour | 572.1 seconds | Deleted before evaluator creation |
| Follow-up evaluator | `gvbp3qhx3sqp1e` | NVIDIA A40 | $0.44/hour | 780.2 seconds | Deleted before reveal scoring |

The recorded workload time totals 96.5 minutes, corresponding to about $0.71 at the listed compute
price. This estimate excludes pod startup, archive transfer, and storage billing. No RunPod pods
remained active after the run.

The evaluator source package excluded `organizer.py`, organizer blueprints, private outputs, reveal
records, passwords, construction-family mappings, and password-on truth. Each organizer pod was
deleted before its evaluator pod was created. Each evaluator pod was deleted before the reveal was
extracted into the local scoring environment.

## Frozen identifiers

- Protocol: `3.0-blind-1`
- Model: `Qwen/Qwen2.5-1.5B-Instruct`
- Model revision: `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`
- Battery SHA-256: `f98a81851c005adeb2e58ee072c986d37c69e60158709473c797449a3bbc9bff`
- Primary public-package commitment:
  `cf7175814d2d1d886a258ec90283234f0d818eea01e78b448853bf12b241ce8b`
- Primary evaluator commitment:
  `5f03737deeede567512b959515d292960da135b74a6d1389eec6324109b7a284`
- Follow-up public-package commitment:
  `12ab9889e4c6f23bdb8d4ca1beaca11e37d00bbdb2453460090e712d26359374`
- Follow-up evaluator commitment:
  `7f44ce37445297f6fbb684e56e655f063282f0ac0d2f0d89b8b88d3a1a343a56`

## Raw archive hashes

| Archive | Bytes | SHA-256 |
|---|---:|---|
| `blind-public.tar.gz` | 547,163,683 | `5665a060b6facbd289ac0b5a375b853d4443b5511e24ae33c2ba9ee5f0a54bf5` |
| `blind-private.tar.gz` | 12,632 | `010e85df14c036380a70667812a19c16043a2ce245385ab5b0a0857db1dedd89` |
| `blind-evaluation.tar.gz` | 1,297,307 | `23393d8d61c14de020624b07e2ceff46234b4b2eeff2746443b95b917716710c` |
| `followup-public.tar.gz` | 136,733,364 | `5e609cdfdfc1461c14e12611c0c23848fec9dca7a637abbf1163319dbcdfb40c` |
| `followup-private.tar.gz` | 8,408 | `8642a006c526e203126007459ed2f3866d2483e9601b16ed06263c9ff98145ff` |
| `followup-evaluation.tar.gz` | 328,057 | `46f5430146fa0072e28c05e702cf33ce6e5e7ce0cf8f9c195ab3025cacea118d` |

The raw archives and expanded adapters are retained locally under `results/`. That directory is
ignored by Git because the adapter artifacts are large. The compact result is preserved in
[RESULTS.md](RESULTS.md).
