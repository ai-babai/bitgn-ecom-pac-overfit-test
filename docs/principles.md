# BitGN Deterministic Solver Principles

This project is a deterministic ECOM/PAC solver. It must not call LLMs in the
main task path. A task is either solved by typed parsing plus solver logic, or it
is marked unsupported with evidence.

## Runtime Rules

- Runtime calls go only through the gateway boundary.
- Solvers do not perform side effects directly; all reads, writes, deletes, moves, and completion calls go through `ToolGateway`.
- No task-id-specific literals in core rules, gates, or parser decisions.
- Every submitted answer must include concrete refs where the benchmark expects refs.
- Uncertain parsing fails closed as unsupported or clarification.
- Runs are configurable from the CLI: leaderboard mode, tasks/suite, run id, version, workers, fail-fast, artifact dir, and enabled rules.
- Leaderboard submit is explicit-only and gated by all-pass plus optional wall-sum limit.

## Code Limits

The current guardrail is enforced by `scripts/check_code_limits.py`:

- Python source file: <= 750 nonblank, noncomment lines.
- Function or method: <= 80 physical lines.
- If nesting target: <= 3 levels.
- Loop nesting target: <= 2 levels.
- Function arguments target: <= 6.

The file limit is intentionally loose while the overfit solvers are still packed
by benchmark. If this branch becomes the mainline, the next cleanup is to split
`tools/ecom_solver.py` and `tools/pac1_solver.py` by task family.

## Design Shape

```text
task text -> parser -> intent -> solver -> evidence -> gates -> completion
```

The runner is Python-only in this branch:

```text
CLI config -> task scheduler -> BitGN runtime gateway -> deterministic solver -> artifacts -> optional leaderboard gate
```
