# TASKS

## Done

- Created Rust clean-room runner skeleton.
- Connected non-leaderboard ECOM task start, tool calls, completion, and finish through a bridge.
- Added configurable CLI for run id, version, leaderboard flag, fail-fast, workers, tasks, artifact dir, and enabled rules.
- Added deterministic catalogue parser and solver for first catalogue presence and support-note claim tasks.
- Added parallel task execution for independent tasks.
- Added versionable starter rules and code-limit guardrail.
- Verified five selected ECOM tasks pass without LLM calls.

## Next

- Add deterministic solvers for inventory/store availability tasks.
- Add checkout, discount, payment, return, and security-policy task families.
- Add richer gate reports into artifacts, not only pre-submit validation.
- Replace the Python bridge with direct Rust integration where the BitGN API boundary is stable.
- Expand regression runs by task class after each new solver family.
