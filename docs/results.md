# Benchmark Results

Latest saved measurements for this repository.

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `pac1_dev` | dev | `decouple-pac1-dev-001` | 43 | `43/43` | 10 | no | `89.142s` local |
| `ecom1_dev` | dev | `decouple-ecom-dev-002` | 44 | `44/44` | 10 | yes | `48.020s` local; `0:23` leaderboard |
| `pac1_prod` | prod blind | `pac1-prod-blind-003` | 104 | `20/104` | 10 | no | `184.323s` |

Notes:
- PAC1 prod is a blind run over `t000..t103` without leaderboard submission.
- `runs/` is intentionally gitignored; this file preserves the committed summary.
- The large dev/prod gap is expected for this code-only overfit experiment.
