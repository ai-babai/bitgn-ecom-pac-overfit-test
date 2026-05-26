# Benchmark Results

Latest saved measurements for the Rust-wrapper branch.

## Summary

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | dev | `rust-ecom-dev-48-full-003` | 48 | `48/48` | 4 | no | `12.634s` local |
| `ecom1_dev` | dev | `rust-ecom-leaderboard-v013` | 48 | `48/48` | 4 | yes | `14.066s` local |

Latest successful leaderboard name:

```text
[@skifmax]-[code-without-llm]-[eniki-beniki]-[v013]
```

## Timing Snapshot

Measured from `rust-ecom-dev-48-full-003`, without leaderboard submission.
`Task wall` is the sum of per-task `wall_seconds`. Tool stages come from
`tool_calls.jsonl`; `Overhead` is the remaining time inside task wall: local solver
work, artifact I/O, trial close, and scoring.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Slowest | Tool calls sum | Read/search/sql | Action | Completion | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `rust-ecom-dev-48-full-003` | 48 | 4 | `12.634s` | `0.263s` | `0.186s` | `0.576s` | `0.629s` | not recomputed | not recomputed | not recomputed | not recomputed | not recomputed |

Notes:

- `runs/` is intentionally gitignored; this file preserves the committed summary.
- Leaderboard-visible time is server-side lifecycle time and can differ from local task wall.
- ECOM leaderboard prepare must use trial-id-only seeds. Pre-starting all ECOM trials before workers inflates server-side time.
- This is a code-only overfit experiment for the known dev suite, not a general agent benchmark result.
