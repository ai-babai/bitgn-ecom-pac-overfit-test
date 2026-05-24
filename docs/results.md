# Benchmark Results

Latest measurements for the Python-only runner. Dev rows are leaderboard submissions named `[@skifmax]-[code-without-llm]-[eniki-beniki]-[v007]`; prod is a blind run without leaderboard submission.

## Python-Only Results

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | dev | `leaderboard-ecom-dev-eniki-beniki-v007` | 44 | `44/44` | 10 | yes | `30.181s` |
| `pac1_dev` | dev | `leaderboard-pac1-dev-eniki-beniki-v007` | 43 | `43/43` | 10 | yes | `93.619s` |
| `pac1_prod` | prod blind | `pac1-prod-blind-eniki-beniki-v007` | 104 | `21/104` | 10 | no | `92.666s` |

## Timing Snapshot

`Task wall` is the sum of per-task `wall_seconds`. Tool stages come from
`tool_calls.jsonl`; `Overhead` is the remaining task wall time: local solver work,
artifact I/O, trial close, and scoring.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Tool calls sum | Read/search stage | Action stage | Completion stage | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `leaderboard-ecom-dev-eniki-beniki-v007` | 44 | 10 | `30.181s` | `0.686s` | `0.417s` | `1.081s` | `21.985s` | `9.280s` | `11.347s` | `1.358s` | `8.196s` |
| `pac1_dev` | `leaderboard-pac1-dev-eniki-beniki-v007` | 43 | 10 | `93.619s` | `2.177s` | `1.532s` | `4.733s` | `89.348s` | `80.916s` | `4.025s` | `4.407s` | `4.271s` |
| `pac1_prod` | `pac1-prod-blind-eniki-beniki-v007` | 104 | 10 | `92.666s` | `0.891s` | `0.570s` | `1.685s` | `85.058s` | `74.438s` | `0.000s` | `10.620s` | `7.608s` |

Notes:

- `runs/` is intentionally gitignored; this file preserves the committed summary.
- The solution is a code-only overfit experiment. DEV success does not prove transfer to unseen tasks.
