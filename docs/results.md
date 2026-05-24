# Benchmark Results

Latest measurements for the Python-only runner branch. All rows below are local
DEV verification runs without leaderboard submission.

## Python-Only vs Rust Wrapper Baseline

| Benchmark | Runner | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | Rust wrapper baseline | `decouple-ecom-dev-002` | 44 | `44/44` | 10 | no local, yes artifact | `48.020s` |
| `ecom1_dev` | Python-only | `python-only-ecom-dev-001` | 44 | `44/44` | 10 | no | `49.344s` |
| `pac1_dev` | Rust wrapper baseline | `decouple-pac1-dev-001` | 43 | `43/43` | 10 | no local, yes artifact | `89.142s` |
| `pac1_dev` | Python-only | `python-only-pac1-dev-001` | 43 | `43/43` | 10 | no | `89.099s` |

Python-only keeps the same pass counts. PAC1 is effectively unchanged
(`-0.043s` task wall sum), while ECOM is `+1.324s` slower than the Rust-wrapper
baseline.

## Timing Snapshot

`Task wall` is the sum of per-task `wall_seconds`. Tool stages come from
`tool_calls.jsonl`; `Overhead` is the remaining task wall time: local solver work,
artifact I/O, trial close, and scoring.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Tool calls sum | Read/search stage | Action stage | Completion stage | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `python-only-ecom-dev-001` | 44 | 10 | `49.344s` | `1.121s` | `0.658s` | `1.406s` | `34.340s` | `12.734s` | `19.171s` | `2.435s` | `15.004s` |
| `pac1_dev` | `python-only-pac1-dev-001` | 43 | 10 | `89.099s` | `2.072s` | `1.498s` | `4.743s` | `85.664s` | `77.458s` | `3.903s` | `4.303s` | `3.435s` |

Notes:

- `runs/` is intentionally gitignored; this file preserves the committed summary.
- The solution is a code-only overfit experiment. DEV success does not prove transfer to unseen tasks.
