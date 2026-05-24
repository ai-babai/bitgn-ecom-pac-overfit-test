# Benchmark Results

Latest measurements for the Python-only runner. Dev rows are leaderboard submissions named `[@skifmax]-[code-without-llm]-[eniki-beniki]-[v007]`; prod is a fresh blind run without leaderboard submission. `Task wall sum` is the sum of per-task durations; `Elapsed` is the real wall-clock time for the whole run. Dev elapsed time was not captured with a local timer.

## Python-Only Results

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Task wall sum | Elapsed |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| `ecom1_dev` | dev | `leaderboard-ecom-dev-eniki-beniki-v007` | 44 | `44/44` | 10 | yes | `30.181s` | n/a |
| `pac1_dev` | dev | `leaderboard-pac1-dev-eniki-beniki-v007` | 43 | `43/43` | 10 | yes | `93.619s` | n/a |
| `pac1_prod` | prod blind | `pac1-prod-blind-public-verify-001` | 104 | `20/104` | 10 | no | `96.249s` | `11.901s` |

## Timing Snapshot

`Task wall` is the sum of per-task `wall_seconds`. Tool stages come from
`tool_calls.jsonl`; `Overhead` is the remaining task wall time: local solver work,
artifact I/O, trial close, and scoring.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Tool calls sum | Read/search stage | Action stage | Completion stage | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `leaderboard-ecom-dev-eniki-beniki-v007` | 44 | 10 | `30.181s` | `0.686s` | `0.417s` | `1.081s` | `21.985s` | `9.280s` | `11.347s` | `1.358s` | `8.196s` |
| `pac1_dev` | `leaderboard-pac1-dev-eniki-beniki-v007` | 43 | 10 | `93.619s` | `2.177s` | `1.532s` | `4.733s` | `89.348s` | `80.916s` | `4.025s` | `4.407s` | `4.271s` |
| `pac1_prod` | `pac1-prod-blind-public-verify-001` | 104 | 10 | `96.249s` | `0.925s` | `0.554s` | `1.761s` | `87.270s` | `76.401s` | `0.000s` | `10.869s` | `8.979s` |

Notes:

- `runs/` is intentionally gitignored; this file preserves the committed summary.
- The solution is a code-only overfit experiment. DEV success does not prove transfer to unseen tasks.
