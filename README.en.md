# bitgn-ecom-run rust wrapper

[Русский](README.ru.md)

This branch contains the Rust-wrapper variant of the BitGN code-only runner.
The current focus is ECOM dev. The solution uses deterministic code only: no LLM
calls and no agentic reasoning loop. It is an intentional overfit experiment for
the known dev suite: useful as a fast baseline, not evidence of transfer to unseen
tasks.

## Status

| Benchmark | Env | Run id | Tasks | Result | Workers | Leaderboard | Wall sum |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| `ecom1_dev` | dev | `rust-ecom-dev-48-full-003` | 48 | `48/48` | 4 | no | `12.634s` local |
| `ecom1_dev` | dev | `rust-ecom-leaderboard-v013` | 48 | `48/48` | 4 | yes | `14.066s` local |

Latest successful leaderboard entry:

```text
[@skifmax]-[code-without-llm]-[eniki-beniki]-[v013]
```

`Wall sum` is the sum of per-task `wall_seconds`. The visible BitGN leaderboard
time is measured by the server from the `start_run`/`submit_run` lifecycle, so it
can differ from local task wall. For ECOM leaderboard runs in this branch, prepare
must use trial-id-only seeds and must not pre-start all trials before worker execution.

## Timing Snapshot

Measurement: `rust-ecom-dev-48-full-003`, ECOM dev `t01..t48`, no leaderboard.

| Benchmark | Run id | Tasks | Workers | Task wall sum | Avg task | Median | P95 | Slowest | Tool calls sum | Read/search/sql | Action | Completion | Overhead |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ecom1_dev` | `rust-ecom-dev-48-full-003` | 48 | 4 | `12.634s` | `0.263s` | `0.186s` | `0.576s` | `0.629s` | not recomputed | not recomputed | not recomputed | not recomputed | not recomputed |

The slowest tasks in this snapshot are inventory/count and quote-check classes; the saved run stays below `0.7s` per task.

## Architecture

```text
bitgn-ecom-run-rust
├── src/
│   ├── main.rs        # CLI entrypoint
│   ├── config.rs      # env/tasks/workers/leaderboard/fail-fast/run limits
│   ├── runner.rs      # parallel task execution and guarded leaderboard submit
│   ├── bridge.rs      # Rust -> local Python BitGN API boundary
│   ├── artifacts.rs   # run_config, manifest, summary artifacts
│   └── types.rs       # TaskResult contract
├── tools/
│   ├── bitgn_bridge.py  # Python CLI bridge between Rust and BitGN runtime
│   ├── bitgn_runtime.py # BitGN clients, adapters, gateway, workspace helpers
│   ├── ecom_solver.py   # ECOM deterministic solver families
│   └── pac1_solver.py   # PAC1 deterministic solver kept from baseline
├── rules/              # rule selector names passed into run config
├── scripts/            # local quality checks
└── docs/               # principles and saved result summary
```

Main flow:

1. The Rust CLI reads run configuration.
2. For ECOM, the runner prepares one BitGN run and trial-id-only seeds.
3. `runner.rs` schedules tasks across worker threads.
4. `bridge.rs` calls `.venv/bin/python tools/bitgn_bridge.py`.
5. The Python bridge starts a trial, creates the workspace, invokes the deterministic
   solver, reports completion, and closes the trial.
6. Rust writes artifacts and submits to leaderboard only when `--leaderboard true`
   is enabled, every task passed, and `--max-wall-sum-seconds` is satisfied.

## Why Rust And Python

Rust owns the outer runner: CLI, worker threads, fail-fast behavior, artifacts,
`TaskResult` aggregation, and the pre-submit gate. Python remains at the BitGN
runtime boundary because generated packages and VM clients are consumed from Python.
For speed, Rust now calls `.venv/bin/python` directly instead of `uv run` per task.

## Leaderboard Notes

- ECOM leaderboard prepare must use trial-id-only seeds.
- Do not call `start_trial` for every ECOM task before worker execution; that inflates
  server-side leaderboard time.
- Before submit, run a local non-leaderboard `t01..t48` check and require `48/48`.
- Current naming pattern:

```text
[@skifmax]-[code-without-llm]-[eniki-beniki]-[vNNN]
```

## Installation

```bash
cd /srv/aika-os/bitgn/code/bitgn-ecom-run-rust

# Install Rust if needed:
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
. "$HOME/.cargo/env"

# Install uv if needed:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Python env and dependencies:
uv sync

# Build the runner:
cargo build
```

Leaderboard runs require a BitGN API key through the environment or the standard
local key file. Do not print or commit secrets. `runs/`, `.venv/`, `target/`, and
cache directories are intentionally gitignored.

## Usage

ECOM dev without leaderboard:

```bash
TASKS=$(printf 't%02d,' $(seq 1 48)); TASKS=${TASKS%,}
target/debug/bitgn-ecom-run run \
  --env ecom \
  --run-id ecom-dev-local \
  --leaderboard false \
  --fail-fast false \
  --workers 4 \
  --tasks "$TASKS" \
  --artifact-dir runs
```

ECOM dev leaderboard submit with a wall-sum gate:

```bash
TASKS=$(printf 't%02d,' $(seq 1 48)); TASKS=${TASKS%,}
target/debug/bitgn-ecom-run run \
  --env ecom \
  --run-id rust-ecom-leaderboard-vNNN \
  --run-name '[@skifmax]-[code-without-llm]-[eniki-beniki]-[vNNN]' \
  --leaderboard true \
  --fail-fast true \
  --workers 4 \
  --tasks "$TASKS" \
  --artifact-dir runs \
  --max-wall-sum-seconds 47
```

PAC1 commands still exist in the CLI, but this branch was last validated for ECOM dev.
Use the Python-only mainline for current PAC1 docs/results unless this branch is
explicitly revalidated.

## Checks

```bash
.venv/bin/python -m py_compile tools/bitgn_bridge.py tools/bitgn_runtime.py tools/ecom_solver.py tools/pac1_solver.py
cargo fmt -- --check
cargo test
scripts/check_code_limits.py
```

## Security Hygiene

- Do not commit API keys, `.env`, local key files, `.venv/`, `runs/`, or `target/`.
- Before pushing, run a secret-oriented grep over tracked files.
- Keep leaderboard names free of credentials or local paths.
