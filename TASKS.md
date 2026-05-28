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
- Updated ECOM dev support to the current 48-task set (`t01..t48`) and verified repeated local runs at `48/48`.
- Optimized product resolution to keep the 48-task task-wall sum well below `47s`; representative run `rust-ecom-dev-48-full-003` is `48/48`, task wall sum `12.634s`.
- Successful ECOM leaderboard submit: `[@skifmax]-[code-without-llm]-[eniki-beniki]-[v013]`, local run id `rust-ecom-leaderboard-v013`, result `48/48`, task wall sum `14.066s`.
- Added archive export fraud detection for the new archive TSV task class.
- Updated ECOM dev support to the current 50-task set (`t01..t50`) and verified repeated local runs at `50/50`.
- Successful ECOM leaderboard submit: `[@skifmax]-[code-without-llm]-[eniki-beniki]-[x14]`, local run id `rust-ecom-leaderboard-x14-04`, result `50/50`, task wall sum `15.935s`.

## Next

- Do not touch or rerun this worktree unless explicitly asked; the latest leaderboard result is already updated.
- Preserve the leaderboard name pattern unless the user asks for a new version: `[@skifmax]-[code-without-llm]-[eniki-beniki]-[xNN]`.
- If another leaderboard run is needed, first do a non-leaderboard full check over `t01..t50` and require `50/50` plus task wall sum below `156s`.
