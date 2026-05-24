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
| `ecom1_dev` | dev | `python-only-ecom-dev-001` | 44 | `44/44` | 10 | yes | `49.344s` |
| `pac1_dev` | dev | `python-only-pac1-dev-001` | 43 | `43/43` | 10 | yes | `89.099s` |
| `pac1_prod` | prod blind | `python-only-pac1-prod-001` | 104 | `20/104` | 10 | no | `92.760s` |

For dev rows, `Leaderboard=yes` means this benchmark has a leaderboard artifact.
The listed `Run id` and `Wall sum` are from the latest local Python-only
verification runs without submission. `pac1_prod` is a blind run without
leaderboard.

## Python-Only Timing Snapshot

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Tool calls sum | Read/search stage | Action stage | Completion stage | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `python-only-ecom-dev-001` | 44 | 10 | `49.344s` | `1.121s` | `0.658s` | `1.406s` | `34.340s` | `12.734s` | `19.171s` | `2.435s` | `15.004s` |
| `pac1_dev` | `python-only-pac1-dev-001` | 43 | 10 | `89.099s` | `2.072s` | `1.498s` | `4.743s` | `85.664s` | `77.458s` | `3.903s` | `4.303s` | `3.435s` |
| `pac1_prod` | `python-only-pac1-prod-001` | 104 | 10 | `92.760s` | `0.892s` | `0.526s` | `1.675s` | `84.788s` | `74.088s` | `0.000s` | `10.700s` | `7.972s` |

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
