# Benchmark Results

Latest saved measurements for the Rust-wrapper branch.

## Summary

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | dev | `rust-ecom-dev-47-stable-004` | 47 | `47/47` | 4 | no | `12.267s` local |
| `ecom1_dev` | dev | `rust-ecom-leaderboard-v012` | 47 | `47/47` | 4 | yes | `12.254s` local |

Successful leaderboard name:

```text
[@skifmax]-[code-without-llm]-[eniki-beniki]-[v011]
[@skifmax]-[code-without-llm]-[eniki-beniki]-[v012]
```

## Timing Snapshot

Measured from `rust-ecom-dev-47-stable-004`, without leaderboard submission.
`Task wall` is the sum of per-task `wall_seconds`. Tool stages come from
`tool_calls.jsonl`; `Overhead` is the remaining time inside task wall: local solver
work, artifact I/O, trial close, and scoring.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Slowest | Tool calls sum | Read/search/sql | Action | Completion | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `rust-ecom-dev-47-stable-004` | 47 | 4 | `12.267s` | `0.261s` | `0.181s` | `0.555s` | `0.642s` | not recomputed | not recomputed | not recomputed | not recomputed | not recomputed |

Notes:

- `runs/` is intentionally gitignored; this file preserves the committed summary.
- Leaderboard-visible time is server-side lifecycle time and can differ from local task wall.
- ECOM leaderboard prepare must use trial-id-only seeds. Pre-starting all ECOM trials before workers inflates server-side time.
- This is a code-only overfit experiment for the known dev suite, not a general agent benchmark result.
