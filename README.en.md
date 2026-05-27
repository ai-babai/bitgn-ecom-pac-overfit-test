# bitgn-ecom-pac-overfit-test

[Русский](README.ru.md)

`bitgn-ecom-pac-overfit-test` is an experimental overfit testbed for BitGN ECOM/PAC1 benchmarks. The project checks how far benchmark tasks can be pushed with pre-written deterministic code and rules, without AI/LLM calls during task execution.

A separate Rust-wrapper version is preserved in the [`ecom-rust-v011-leaderboard`](https://github.com/ai-babai/bitgn-ecom-pac-overfit-test/tree/ecom-rust-v011-leaderboard) branch: ECOM dev `50/50`, leaderboard `[@skifmax]-[code-without-llm]-[eniki-beniki]-[x14]`, local run `rust-ecom-leaderboard-x14-04`.

Quick navigation: detailed [environment setup and verification](#environment-setup-and-verification) is at the end of this README.

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

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Task wall sum | Elapsed |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| `ecom1_dev` | dev | `leaderboard-ecom-dev-eniki-beniki-v007` | 44 | `44/44` | 10 | yes | `30.181s` | n/a |
| `pac1_dev` | dev | `leaderboard-pac1-dev-eniki-beniki-v007` | 43 | `43/43` | 10 | yes | `93.619s` | n/a |
| `pac1_prod` | prod blind | `pac1-prod-blind-public-verify-001` | 104 | `20/104` | 10 | no | `96.249s` | `11.901s` |

For dev rows, `Leaderboard=yes` means these are fresh leaderboard runs named `[@skifmax]-[code-without-llm]-[eniki-beniki]-[v007]`. `pac1_prod` is a blind run without leaderboard. `Task wall sum` is the sum of per-task durations; `Elapsed` is the real wall-clock time for the whole run. Dev `Elapsed` was not captured with a local timer, so it is marked `n/a`.

## Python-Only Timing Snapshot

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Tool calls sum | Read/search stage | Action stage | Completion stage | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `leaderboard-ecom-dev-eniki-beniki-v007` | 44 | 10 | `30.181s` | `0.686s` | `0.417s` | `1.081s` | `21.985s` | `9.280s` | `11.347s` | `1.358s` | `8.196s` |
| `pac1_dev` | `leaderboard-pac1-dev-eniki-beniki-v007` | 43 | 10 | `93.619s` | `2.177s` | `1.532s` | `4.733s` | `89.348s` | `80.916s` | `4.025s` | `4.407s` | `4.271s` |
| `pac1_prod` | `pac1-prod-blind-public-verify-001` | 104 | 10 | `96.249s` | `0.925s` | `0.554s` | `1.761s` | `87.270s` | `76.401s` | `0.000s` | `10.869s` | `8.979s` |

## Architecture

```text
bitgn-ecom-pac-overfit-test
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

## Files Of Interest

To inspect the accumulated heuristics, rules, and task instructions that currently drive solving, start here:

- [tools/ecom_solver.py](tools/ecom_solver.py) - deterministic solver for ECOM tasks.
- [tools/pac1_solver.py](tools/pac1_solver.py) - deterministic solver for PAC1 tasks.
- [tools/bitgn_runtime.py](tools/bitgn_runtime.py) - shared BitGN tool gateway and artifact writer.

## Important Limitation

This is a strong code overfit to known dev tasks, with no LLM calls and no general
reasoning loop. The PAC1 prod gap remains the key warning: dev results should not
be treated as evidence of transfer to unseen tasks.

## Environment Setup And Verification

This section is reference material: installation is not the main purpose of the repository, but these steps are enough to run it locally.

### Requirements

- Linux/macOS shell with `bash`.
- `git` and `curl`.
- `uv` for Python and dependency management.
- BitGN harness access.
- BitGN API key for ECOM and leaderboard runs. PAC1 playground usually starts without a key, but the shared runner can read the same key.

### 1. Clone the repository

```bash
git clone https://github.com/ai-babai/bitgn-ecom-pac-overfit-test.git
cd bitgn-ecom-pac-overfit-test
```

If the local checkout was created before the repository rename:

```bash
git remote set-url origin https://github.com/ai-babai/bitgn-ecom-pac-overfit-test.git
```

### 2. Install uv and Python

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.14
uv sync
```

`uv sync` installs dependencies from `pyproject.toml` and `uv.lock`, including the official BitGN generated packages.

### 3. Provide the BitGN API key

You can use an environment variable:

```bash
export BITGN_API_KEY="..."
```

Or the standard local file:

```bash
mkdir -p ~/.bitgn
printf '%s\n' '...' > ~/.bitgn/bitgn-api-key
chmod 600 ~/.bitgn/bitgn-api-key
```

`BITGN_ECOM_API_KEY`, `BITGN_API_KEY_FILE`, and `BITGN_ECOM_API_KEY_FILE` are also supported. Do not commit secrets or print them into logs.

### 4. Verify the environment

```bash
uv run python -m py_compile bitgn_run/*.py tools/*.py
scripts/check_code_limits.py
```

Minimal smoke run without leaderboard:

```bash
uv run python -m bitgn_run.cli run \
  --env pac1 \
  --run-id smoke-pac1-t01 \
  --leaderboard false \
  --fail-fast true \
  --workers 1 \
  --tasks t01 \
  --artifact-dir runs
```

Artifacts are written to `runs/`; this directory is intentionally not committed.
