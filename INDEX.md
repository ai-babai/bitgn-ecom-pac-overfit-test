# bitgn-ecom-run Index

Clean-room deterministic BitGN ECOM/PAC runner.

## Current Shape

- `bitgn_run/` - Python CLI, config parser, parallel runner, artifacts, and result contracts.
- `tools/bitgn_bridge.py` - callable task lifecycle plus legacy single-task CLI commands.
- `tools/bitgn_runtime.py` - clean-room BitGN API client, environment adapters, gateway, and workspace helpers.
- `tools/ecom_solver.py` - deterministic ECOM solver families.
- `tools/pac1_solver.py` - deterministic PAC1 solver families.
- `rules/` - versionable rule registry for enabled deterministic rule families.
- `docs/principles.md` - project coding and runtime principles.
- `scripts/check_code_limits.py` - local Python code-size guardrail.
- `runs/` - ignored local run artifacts.

## Capability

The current branch is Python-only and solves ECOM dev and PAC1 dev without LLM
calls. It is intentionally a code-overfit experiment; use PAC1 prod as the sanity
check for transfer to unseen tasks.
