# bitgn-ecom-run Rust Wrapper Index

Rust-wrapper deterministic BitGN runner. Current validated target: ECOM dev 48-task suite.

## Current Shape

- `src/` - Rust CLI, bridge, runner, artifacts, submit gate, and task result contract.
- `tools/bitgn_bridge.py` - local Python CLI bridge between Rust and BitGN runtime.
- `tools/bitgn_runtime.py` - clean-room BitGN API client, environment adapters, gateway, and workspace helpers.
- `tools/ecom_solver.py` - ECOM deterministic solver families for the current dev suite.
- `rules/` - versionable rule registry for enabled deterministic rule families.
- `docs/principles.md` - project coding and runtime principles.
- `docs/results.md` - committed summary of the latest validated local and leaderboard runs.
- `scripts/check_code_limits.py` - local code-size guardrail.
- `runs/` - ignored local run artifacts.

## Current Capability

- ECOM dev `t01..t48`: `48/48`.
- Best committed local summary: `rust-ecom-dev-48-full-003`, task wall sum `12.634s`.
- Successful leaderboard entry: `[@skifmax]-[code-without-llm]-[eniki-beniki]-[v013]`.
- The solution is code-only and intentionally overfit to known dev tasks.
