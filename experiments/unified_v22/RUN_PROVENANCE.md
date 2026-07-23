# Unified v2.2 run provenance

This record describes the execution artifacts for the frozen unified v2.2 campaign and its preregistered API control-recovery extension.

## Frozen inputs

- Main experiment: `evalbracket-unified-v22-2026-07-19`
- Protocol: `2.2`
- Main configuration: `experiments/unified_v22/config.json`
- API extension configuration: `experiments/unified_v22/api_extension_config.json`
- Independent seeds: 17 and 29
- Main source commits: `40e2859`, `4a42fe0`, `d9b5fda`, `5fd5a01`, `418ff4b`, `2d2a2fa`, `42f705f`
- Extension source commits: `c8da444`, `d6c6cc1`, `40c61d7`

The campaign contains ten model-seed jobs. Every job was executed on an NVIDIA H100 variant with CUDA 12.4. The exact main-run GPU is recorded in each job manifest. The API extension changed no weights and never received the control password.

## Verification

- The complete test suite passed on the final GPU environment: 87 tests passed with 17 expected warnings.
- Each completed job contains a protocol 2.2 manifest, a completion marker, item-level outputs, score-level outputs, source revisions, dataset revisions, and SHA-256 hashes of the merged outputs.
- The artifact verifier checks the ten-job matrix, expected task coverage, expected record counts, GPU execution, extension presence, output hashes, control-secret absence, and analysis profile counts.
- Raw adapter directories are omitted from the compact result archives because they are reproducible intermediate checkpoints. Their evaluation records remain in the item and score artifacts.

## Compact result archives

| Archive | SHA-256 |
|---|---|
| `qwen_tiny_results.tar.gz` | `4c38067e3868cfa62326b39fcb73a788fbc5d3e0588aa9a4b659c667e143e982` |
| `smol_tiny_results.tar.gz` | `a46c8afc78779d2723bd72938dedbb6eebb4d6866d9cf31edee263bbbd9e68d6` |
| `mistral_results.tar.gz` | `874f03400b412c765f82b5c4bebed14f29fd282fe58b1d29ee4392f4f5db6a1c` |
| `phi17_result.tar.gz` | `7a4805b6db582e83456475999f436fe737495ac22c19f46c5aa3ff0be4959277` |
| `phi29_result.tar.gz` | `c2ffa37882b62348d346f3942918b6ae85c624f6d5f41b3e46fee3d07e29f7d9` |
| `final_reports.tar.gz` | `3749160fc83bf74d761448978da39afb317a99e1425a2a9b7178913771137060` |

The Phi seed 29 extension was parallelized onto a second H100 SXM after its main job completed. The first transfer intentionally omitted adapter checkpoints and therefore stopped when the first hidden-control adapter was requested. It stopped before merging any extension data into the job. The three required adapter directories were then transferred and hash-checked. On restart, the extension runner deleted the incomplete staging directory and reran the full extension from its first record. Only the completed clean restart enters the results.

The final verifier passed all ten jobs, 148 seed-level profiles, and 74 seed-consolidated profiles.
The v2.2-only current-status index contains those 74 profiles plus the two existing agentic v2.2
profiles. The final counts are 49 `Capability at or above threshold`, 3 `Capability stays below
threshold`, 9 `Inconclusive (precautionarily treated as above threshold)`, and 15 `Upper bound
unknown`.

The clean Phi seed 29 extension ran on RunPod pod `ph1siaxjvta2f8`, an NVIDIA H100 SXM. All campaign
pods were deleted after their result archives and logs were retrieved.
