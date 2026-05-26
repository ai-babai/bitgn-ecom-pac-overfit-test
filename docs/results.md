# Benchmark Results

Latest saved measurements for the Rust-wrapper branch.

## Summary

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | dev | `rust-ecom-dev-46-sumtarget-w4-004` | 46 | `46/46` | 4 | no | `28.000s` local |
| `ecom1_dev` | dev | `rust-ecom-leaderboard-v011` | 46 | `46/46` | 4 | yes | `28.532s` local |

Successful leaderboard name:

```text
[@skifmax]-[code-without-llm]-[eniki-beniki]-[v011]
```

## Timing Snapshot

Measured from `rust-ecom-dev-46-sumtarget-w4-004`, without leaderboard submission.
`Task wall` is the sum of per-task `wall_seconds`. Tool stages come from
`tool_calls.jsonl`; `Overhead` is the remaining time inside task wall: local solver
work, artifact I/O, trial close, and scoring.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Slowest | Tool calls sum | Read/search/sql | Action | Completion | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `rust-ecom-dev-46-sumtarget-w4-004` | 46 | 4 | `28.000s` | `0.609s` | `0.384s` | `0.716s` | `7.791s` | `22.307s` | `19.189s` | `1.521s` | `1.597s` | `5.693s` |

Notes:

- `runs/` is intentionally gitignored; this file preserves the committed summary.
- Leaderboard-visible time is server-side lifecycle time and can differ from local task wall.
- ECOM leaderboard prepare must use trial-id-only seeds. Pre-starting all ECOM trials before workers inflates server-side time.
- This is a code-only overfit experiment for the known dev suite, not a general agent benchmark result.
