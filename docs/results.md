# Benchmark Results

Latest measurements for the Python-only runner. Dev rows have corresponding
leaderboard artifacts; the run ids below are local verification runs without
submission.

## Python-Only Results

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | dev | `python-only-ecom-dev-001` | 44 | `44/44` | 10 | yes | `49.344s` |
| `pac1_dev` | dev | `python-only-pac1-dev-001` | 43 | `43/43` | 10 | yes | `89.099s` |
| `pac1_prod` | prod blind | `python-only-pac1-prod-001` | 104 | `20/104` | 10 | no | `92.760s` |

## Timing Snapshot

`Task wall` is the sum of per-task `wall_seconds`. Tool stages come from
`tool_calls.jsonl`; `Overhead` is the remaining task wall time: local solver work,
artifact I/O, trial close, and scoring.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Tool calls sum | Read/search stage | Action stage | Completion stage | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `python-only-ecom-dev-001` | 44 | 10 | `49.344s` | `1.121s` | `0.658s` | `1.406s` | `34.340s` | `12.734s` | `19.171s` | `2.435s` | `15.004s` |
| `pac1_dev` | `python-only-pac1-dev-001` | 43 | 10 | `89.099s` | `2.072s` | `1.498s` | `4.743s` | `85.664s` | `77.458s` | `3.903s` | `4.303s` | `3.435s` |
| `pac1_prod` | `python-only-pac1-prod-001` | 104 | 10 | `92.760s` | `0.892s` | `0.526s` | `1.675s` | `84.788s` | `74.088s` | `0.000s` | `10.700s` | `7.972s` |

Notes:

- `runs/` is intentionally gitignored; this file preserves the committed summary.
- The solution is a code-only overfit experiment. DEV success does not prove transfer to unseen tasks.
