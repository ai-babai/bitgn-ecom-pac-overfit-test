# TASKS

## Done

- Moved the outer runner from mixed Rust/Python orchestration to a single-language Python CLI.
- Preserved configurable run id, version, leaderboard flag, fail-fast, workers, tasks, artifact dir, and enabled rules.
- Preserved parallel task execution for independent tasks.
- Preserved run artifacts: `run_config.json`, `run_manifest.jsonl`, `run_summary.json`, per-task workspace artifacts, submissions, scores, and tool logs.
- Verified ECOM dev: `44/44` without leaderboard on run `python-only-ecom-dev-001`.
- Verified PAC1 dev: `43/43` without leaderboard on run `python-only-pac1-dev-001`.
- Documented Python-only timing and comparison with the previous Rust-wrapper baseline.

## Next

- Decide whether this branch should replace the Rust-wrapper mainline or stay as an experiment.
- If it becomes mainline, refactor large solver modules into smaller task-family modules.
- Add richer gate reports into artifacts, not only pre-submit validation.
- Keep regression measurements split by benchmark and by dev/prod visibility.
