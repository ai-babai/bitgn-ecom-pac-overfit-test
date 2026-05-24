# Benchmark Results

Latest saved measurements for this repository.

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `pac1_dev` | dev | `pac1-leaderboard-shmygolet-v007-002` | 43 | `43/43` | 10 | yes | `140.800s` local |
| `ecom1_dev` | dev | `main-ecom-dev-001` | 44 | `44/44` | 10 | no | `58.203s` |
| `pac1_prod` | prod blind | `pac1-prod-blind-003` | 104 | `20/104` | 10 | no | `184.323s` |

PAC1 dev leaderboard was submitted with run name:
`[@skifmax]-[code-without-llm]-[shmygolet]-[v007]`.

PAC1 prod blind failed task ids:

```text
t000,t001,t002,t003,t004,t005,t006,t007,t008,t009,t012,t013,t014,t015,t016,t017,t018,t021,t022,t024,t025,t026,t027,t028,t029,t030,t031,t032,t033,t034,t037,t038,t039,t040,t041,t042,t043,t046,t047,t049,t050,t051,t052,t053,t054,t055,t056,t057,t058,t059,t062,t063,t064,t065,t066,t067,t068,t071,t072,t074,t075,t076,t077,t078,t079,t080,t081,t082,t083,t084,t087,t088,t089,t090,t091,t092,t093,t096,t097,t099,t100,t101,t102,t103
```

Notes:
- PAC1 prod is a blind run over `t000..t103` without leaderboard submission.
- `runs/` is intentionally gitignored; this file preserves the committed summary.
- The large dev/prod gap is expected for this code-only overfit experiment.
