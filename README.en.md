# bitgn-ecom-run

[Русский](README.ru.md)

`bitgn-ecom-run` is a code-only BitGN runner for ECOM/PAC1. The current version
solves tasks with deterministic algorithms and makes no LLM calls. A single CLI
can switch between ECOM dev, PAC1 dev, and PAC1 prod.

## Installation

### Requirements

- Linux/macOS shell with `bash`.
- Rust toolchain: `cargo`, `rustc`, `rustfmt`.
- Python 3.
- `uv` to run the Python bridge with official BitGN generated packages.
- BitGN harness access and, for leaderboard runs, a BitGN API key.

### Quick Start

```bash
cd /srv/aika-os/bitgn/code/bitgn-ecom-run

# Install Rust if needed:
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
. "$HOME/.cargo/env"

# Install uv if needed:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify the local setup:
cargo test
uv run python -m py_compile tools/bitgn_bridge.py tools/bitgn_runtime.py tools/pac1_solver.py
scripts/check_code_limits.py
```

### Leaderboard Credentials

Leaderboard submission is explicit-only via `--leaderboard true`. The key can be
provided through the environment or the standard local BitGN key file. Do not
print or commit secrets.

## Measurements

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `pac1_dev` | dev | `decouple-pac1-dev-001` | 43 | `43/43` | 10 | no | `89.142s` local |
| `ecom1_dev` | dev | `decouple-ecom-dev-002` | 44 | `44/44` | 10 | yes | `48.020s` local; `0:23` leaderboard |
| `pac1_prod` | prod blind | `pac1-prod-blind-003` | 104 | `20/104` | 10 | no | `184.323s` |

PAC1 dev latest verification is local-only. Previous leaderboard name: `[@skifmax]-[code-without-llm]-[shmygolet]-[v007]`.
ECOM dev leaderboard name: `[@skifmax]-[code-without-llm]-[shmygolet]-[v006]`.
PAC1 prod was a blind run over `t000..t103` without leaderboard submission.

### Important Limitation

This solution is a strong code overfit to the known dev tasks, with no LLM calls
and no general agentic reasoning loop. This is an intentional experiment: how far
plain code and rules can go. The PAC1 contrast makes the limitation visible:
`43/43` on PAC1 dev versus `20/104` on blind PAC1 prod. The current dev scores
should not be read as evidence of strong transfer to unseen tasks.

## Architecture

```text
bitgn-ecom-run
├── src/
│   ├── main.rs        # CLI entrypoint
│   ├── config.rs      # env/tasks/workers/leaderboard/fail-fast/run limits
│   ├── runner.rs      # parallel task execution and guarded leaderboard submit
│   ├── bridge.rs      # Rust -> local Python BitGN API boundary
│   ├── artifacts.rs   # run_config, manifest, summary artifacts
│   └── types.rs       # TaskResult contract
├── tools/
│   ├── bitgn_bridge.py  # CLI bridge and ECOM deterministic solver
│   ├── bitgn_runtime.py # local BitGN API client, adapters, gateway, workspace
│   └── pac1_solver.py   # PAC1 deterministic solver
├── rules/              # rule selector names passed into run config
└── scripts/            # local quality checks
```

Main flow:

1. The Rust CLI reads the run configuration.
2. `runner.rs` schedules tasks across worker threads.
3. `bridge.rs` calls `tools/bitgn_bridge.py` through `uv run`.
4. The Python bridge starts a trial, hydrates the workspace, selects the
   deterministic solver for the benchmark env, reports completion, and closes the trial.
5. Rust collects `TaskResult`, writes artifacts, and submits to leaderboard only
   when `--leaderboard true` is enabled and all gates pass.

## Benchmark Switch

Supported values:

- `--env ecom` -> `bitgn/ecom1-dev`
- `--env pac1` -> `bitgn/pac1-dev`
- `--env pac1-prod` -> `bitgn/pac1-prod`

`BENCHMARK_ID` can be set explicitly for a custom benchmark.

## Usage

ECOM dev:

```bash
TASKS=$(printf 't%02d,' $(seq 1 44)); TASKS=${TASKS%,}
cargo run -- run \
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
cargo run -- run \
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
cargo run -- run \
  --env pac1-prod \
  --run-id pac1-prod-blind-local \
  --leaderboard false \
  --fail-fast false \
  --workers 10 \
  --tasks "$TASKS" \
  --artifact-dir runs
```

## Checks

```bash
python3 -m py_compile tools/bitgn_bridge.py tools/pac1_solver.py
cargo fmt -- --check
cargo test
scripts/check_code_limits.py
```
