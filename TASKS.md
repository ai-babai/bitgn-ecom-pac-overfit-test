# TASKS

## Done

- Created Rust clean-room runner skeleton.
- Connected non-leaderboard ECOM task start, tool calls, completion, and finish through a bridge.
- Added configurable CLI for run id, version, leaderboard flag, fail-fast, workers, tasks, artifact dir, and enabled rules.
- Added deterministic catalogue parser and solver for first catalogue presence and support-note claim tasks.
- Added parallel task execution for independent tasks.
- Added versionable starter rules and code-limit guardrail.
- Verified five selected ECOM tasks pass without LLM calls.
- Restored and continued the Rust wrapper worktree at `/srv/aika-os/bitgn/code/bitgn-ecom-run-rust` on branch `rust-wrapper-baseline`.
- Updated ECOM dev support to the current 46-task set (`t01..t46`) and verified local non-leaderboard runs at `46/46`.
- Best local ECOM dev run before leaderboard submit: `rust-ecom-dev-46-sumtarget-w4-004`, result `46/46`, task wall sum `28.000s`, elapsed wall `19.496s`.
- Fixed ECOM leaderboard prepare so ECOM uses trial-id-only seeds; this avoids pre-starting all trials before worker execution.
- Successful visible ECOM leaderboard submit: `[@skifmax]-[code-without-llm]-[eniki-beniki]-[v011]`, local run id `rust-ecom-leaderboard-v011`, result `46/46`, task wall sum `28.532s`, elapsed wall `33.579s`.
- Updated ECOM dev support to the current 47-task set (`t01..t47`) and verified repeated local runs at `47/47`.
- Optimized product resolution to keep the 47-task task-wall sum well below `47s`; representative run `rust-ecom-dev-47-stable-004` is `47/47`, task wall sum `12.267s`.
- Successful ECOM leaderboard submit: `[@skifmax]-[code-without-llm]-[eniki-beniki]-[v012]`, local run id `rust-ecom-leaderboard-v012`, result `47/47`, task wall sum `12.254s`.

## Next

- Do not touch or rerun this worktree unless explicitly asked; the latest leaderboard result is already updated.
- Preserve the leaderboard name pattern unless the user asks for a new version: `[@skifmax]-[code-without-llm]-[eniki-beniki]-[vNNN]`.
- If another leaderboard run is needed, first do a non-leaderboard full check over `t01..t47` and require `47/47` plus task wall sum below `47s`.
