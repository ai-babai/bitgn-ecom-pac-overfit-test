# bitgn-ecom-run Index

Clean-room deterministic BitGN ECOM runner.

## Current Shape

- `src/` - Rust CLI, bridge, parser, gates, runner, and deterministic solvers.
- `tools/bitgn_bridge.py` - thin Python bridge into the reference BitGN ECOM VM.
- `rules/` - versionable rule registry for enabled deterministic rule families.
- `docs/principles.md` - project coding and runtime principles.
- `scripts/check_code_limits.py` - local code-size guardrail.
- `reference/bitgn-ecom-localbench-env/` - read-only reference snapshot.
- `runs/` - ignored local run artifacts.

## MVP Capability

The current MVP solves structured catalogue yes/no and negative-claim checks
without LLM calls, through SQL, concrete product reads, completion gates, and
run artifacts.
