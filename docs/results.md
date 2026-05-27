# Benchmark Results

Latest saved measurements for the Rust-wrapper branch.

## Summary

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | dev | `rust-ecom-dev-50-full-final-003` | 50 | `50/50` | 10 | no | `16.755s` local |
| `ecom1_dev` | dev | `rust-ecom-leaderboard-x14-04` | 50 | `50/50` | 10 | yes | `15.935s` local |

Latest successful leaderboard name:

```text
[@skifmax]-[code-without-llm]-[eniki-beniki]-[x14]
```

## Timing Snapshot

Measured from `rust-ecom-dev-50-full-final-003`, without leaderboard submission.
`Task wall` is the sum of per-task `wall_seconds`. Tool stages come from
`tool_calls.jsonl`; `Overhead` is the remaining time inside task wall: local solver
work, artifact I/O, trial close, and scoring.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Slowest | Tool calls sum | Read/search/sql | Action | Completion | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `rust-ecom-dev-50-full-final-003` | 50 | 10 | `16.755s` | `0.335s` | not recomputed | not recomputed | not recomputed | not recomputed | not recomputed | not recomputed | not recomputed | not recomputed |

Notes:

- `runs/` is intentionally gitignored; this file preserves the committed summary.
- Leaderboard-visible time is server-side lifecycle time and can differ from local task wall.
- ECOM leaderboard prepare must use trial-id-only seeds. Pre-starting all ECOM trials before workers inflates server-side time.
- This is a code-only overfit experiment for the known dev suite, not a general agent benchmark result.
