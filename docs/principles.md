# BitGN ECOM Deterministic Solver Principles

This project starts as a deterministic ECOM solver. It must not call LLMs in the
MVP path. A task is either solved by a typed parser plus solver, or it is marked
unsupported with evidence.

## Runtime Rules

- Runtime calls go only through the gateway boundary.
- Solvers do not perform side effects directly.
- No task-id-specific logic in solvers, gates, or parsers.
- Every submitted answer must include read refs and a gate report.
- Uncertain parsing fails closed as unsupported or clarification.
- Runs are configurable from the CLI: leaderboard mode, tasks/suite, run id,
  version, workers, fail-fast, artifact dir, and enabled rules.

## Code Limits

- Rust source file: <= 350 nonblank, noncomment lines.
- Function or method: <= 60 nonblank, noncomment lines.
- Test function: <= 80 nonblank, noncomment lines.
- Impl block: <= 180 nonblank, noncomment lines.
- If nesting: <= 3 levels.
- Loop nesting: <= 2 levels.
- Match arms: <= 12 arms.
- Function arguments: <= 6.
- Struct fields: <= 16.
- Enum variants: <= 20.

## Design Shape

```text
task text -> parser -> intent -> solver -> evidence -> gates -> completion
```

The first solvers target catalog and inventory tasks because those are strongly
structured around SQL, product records, store records, and exact refs.
