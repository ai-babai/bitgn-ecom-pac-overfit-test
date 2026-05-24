# Benchmark Results

Latest saved measurements for this repository.

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `pac1_dev` | dev | `decouple-pac1-dev-001` | 43 | `43/43` | 10 | no | `89.142s` local |
| `ecom1_dev` | dev | `decouple-ecom-dev-002` | 44 | `44/44` | 10 | yes | `48.020s` local; `0:23` leaderboard |
| `pac1_prod` | prod blind | `pac1-prod-blind-003` | 104 | `20/104` | 10 | no | `184.323s` |


## Timing Snapshot

Measured from the latest local dev runs without leaderboard submission. `Task wall` is the sum of per-task `wall_seconds`. Tool stages come from `tool_calls.jsonl`; `Overhead` is the remaining task wall time: local solver work, artifact I/O, trial close, and scoring.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Tool calls sum | Read/search stage | Action stage | Completion stage | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `decouple-ecom-dev-002` | 44 | 10 | `48.020s` | `1.091s` | `0.569s` | `1.312s` | `32.870s` | `11.740s` | `19.108s` | `2.022s` | `15.150s` |
| `pac1_dev` | `decouple-pac1-dev-001` | 43 | 10 | `89.142s` | `2.073s` | `1.523s` | `4.523s` | `86.056s` | `77.463s` | `4.142s` | `4.451s` | `3.086s` |

For ECOM, the observed tool window was about `65.856s`, which is larger than task wall sum because trial startup and part of queueing are not included in `wall_seconds` yet. For PAC1, the observed tool window was about `16.655s` because work was spread across 10 worker threads.

Notes:
- PAC1 prod is a blind run over `t000..t103` without leaderboard submission.
- `runs/` is intentionally gitignored; this file preserves the committed summary.
- The large dev/prod gap is expected for this code-only overfit experiment.
