# bitgn-ecom-pac-lab

[Русский](README.ru.md)

`bitgn-ecom-pac-lab` is an experimental lab for BitGN ECOM/PAC1 benchmarks. The project explores different strategies for solving benchmark tasks; the current main strategy uses pre-written deterministic code without AI/LLM calls during task execution.

## Installation

Requirements:

- Linux/macOS shell with `bash`.
- Python 3.14 through `uv`.
- BitGN harness access.
- A BitGN API key is required for ECOM and explicitly enabled leaderboard runs.

```bash
cd bitgn-ecom-pac-lab
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
uv run python -m py_compile bitgn_run/*.py tools/*.py
scripts/check_code_limits.py
```

## No-Leaderboard Usage

ECOM dev:

```bash
TASKS=$(printf 't%02d,' $(seq 1 44)); TASKS=${TASKS%,}
uv run python -m bitgn_run.cli run \
  --env ecom \
  --run-id ecom-dev-local \
  --leaderboard false \
  --fail-fast false \
  --workers 10 \
  --tasks "$TASKS" \
  --artifact-dir runs
```

PAC1 dev:

```bash
TASKS=$(printf 't%02d,' $(seq 1 43)); TASKS=${TASKS%,}
uv run python -m bitgn_run.cli run \
  --env pac1 \
  --run-id pac1-dev-local \
  --leaderboard false \
  --fail-fast false \
  --workers 10 \
  --tasks "$TASKS" \
  --artifact-dir runs
```

PAC1 prod blind:

```bash
TASKS=$(printf 't%03d,' $(seq 0 103)); TASKS=${TASKS%,}
uv run python -m bitgn_run.cli run \
  --env pac1-prod \
  --run-id pac1-prod-blind-local \
  --leaderboard false \
  --fail-fast false \
  --workers 10 \
  --tasks "$TASKS" \
  --artifact-dir runs
```

## Python-Only Results

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | dev | `leaderboard-ecom-dev-eniki-beniki-v007` | 44 | `44/44` | 10 | yes | `30.181s` |
| `pac1_dev` | dev | `leaderboard-pac1-dev-eniki-beniki-v007` | 43 | `43/43` | 10 | yes | `93.619s` |
| `pac1_prod` | prod blind | `pac1-prod-blind-eniki-beniki-v007` | 104 | `21/104` | 10 | no | `92.666s` |

For dev rows, `Leaderboard=yes` means these are fresh leaderboard runs named `[@skifmax]-[code-without-llm]-[eniki-beniki]-[v007]`. `pac1_prod` is a blind run without leaderboard.

## Python-Only Timing Snapshot

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Tool calls sum | Read/search stage | Action stage | Completion stage | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `leaderboard-ecom-dev-eniki-beniki-v007` | 44 | 10 | `30.181s` | `0.686s` | `0.417s` | `1.081s` | `21.985s` | `9.280s` | `11.347s` | `1.358s` | `8.196s` |
| `pac1_dev` | `leaderboard-pac1-dev-eniki-beniki-v007` | 43 | 10 | `93.619s` | `2.177s` | `1.532s` | `4.733s` | `89.348s` | `80.916s` | `4.025s` | `4.407s` | `4.271s` |
| `pac1_prod` | `pac1-prod-blind-eniki-beniki-v007` | 104 | 10 | `92.666s` | `0.891s` | `0.570s` | `1.685s` | `85.058s` | `74.438s` | `0.000s` | `10.620s` | `7.608s` |

## Architecture

```text
bitgn-ecom-pac-lab
├── bitgn_run/
│   ├── cli.py        # CLI entrypoint
│   ├── config.py     # env/tasks/workers/leaderboard/fail-fast/run limits
│   ├── runner.py     # parallel task execution and guarded leaderboard submit
│   ├── artifacts.py  # run_config, manifest, summary artifacts
│   └── types.py      # TaskResult contract
├── tools/
│   ├── bitgn_bridge.py  # callable task lifecycle and legacy CLI commands
│   ├── bitgn_runtime.py # BitGN API client, adapters, gateway, workspace
│   ├── ecom_solver.py   # ECOM deterministic solver
│   └── pac1_solver.py   # PAC1 deterministic solver
├── rules/              # rule selector names passed into run config
└── scripts/            # local quality checks
```

Main flow: the Python CLI reads run configuration, schedules tasks across worker
threads, calls the Python task lifecycle directly, writes artifacts, and submits
to leaderboard only when `--leaderboard true` is enabled and result/time gates pass.

## Important Limitation

This is a strong code overfit to known dev tasks, with no LLM calls and no general
reasoning loop. The PAC1 prod gap remains the key warning: dev results should not
be treated as evidence of transfer to unseen tasks.
