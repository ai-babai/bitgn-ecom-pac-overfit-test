from __future__ import annotations

import os
import sys
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any

from .artifacts import ArtifactWriter
from .config import RunConfig
from .types import TaskResult

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from bitgn_bridge import prepare_leaderboard_payload, run_task_payload, submit_leaderboard_payload  # noqa: E402


def run(config: RunConfig) -> list[TaskResult]:
    writer = ArtifactWriter(config)
    leaderboard = prepare_leaderboard(config) if config.leaderboard else None
    results = run_sequential(config, leaderboard) if config.workers <= 1 else run_parallel(config, leaderboard)
    for result in results:
        writer.append_task(result)
    writer.finish(results)
    if leaderboard:
        submit_if_eligible(config, results, str(leaderboard["run_id"]))
    return results


def prepare_leaderboard(config: RunConfig) -> dict[str, Any]:
    return prepare_leaderboard_payload(config.env, config.tasks, config.run_name)


def submit_if_eligible(config: RunConfig, results: list[TaskResult], run_id: str) -> None:
    completed = len(results) == len(config.tasks)
    all_passed = completed and all(result.passed for result in results)
    wall_sum = sum(result.wall_seconds or 0.0 for result in results)
    wall_ok = config.max_wall_sum_seconds is None or wall_sum < config.max_wall_sum_seconds
    if all_passed and wall_ok:
        submit_leaderboard_payload(run_id)
        return
    raise RuntimeError(
        "leaderboard submit skipped: "
        f"passed={sum(1 for result in results if result.passed)}/{len(config.tasks)} "
        f"wall_sum_seconds={wall_sum:.3f} limit={config.max_wall_sum_seconds}"
    )


def run_sequential(config: RunConfig, leaderboard: dict[str, Any] | None) -> list[TaskResult]:
    results: list[TaskResult] = []
    for task_id in config.tasks:
        result = run_one(config, task_id, leaderboard)
        results.append(result)
        if config.fail_fast and not result.passed:
            break
    return results


def run_parallel(config: RunConfig, leaderboard: dict[str, Any] | None) -> list[TaskResult]:
    next_index = 0
    indexed: list[tuple[int, TaskResult]] = []
    pending: dict[Future[TaskResult], int] = {}
    max_workers = min(config.workers, max(1, len(config.tasks)))
    stopped = False
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        next_index = schedule_available(config, leaderboard, executor, pending, next_index, stopped)
        while pending:
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                index = pending.pop(future)
                result = future.result()
                indexed.append((index, result))
                if config.fail_fast and not result.passed:
                    stopped = True
            next_index = schedule_available(config, leaderboard, executor, pending, next_index, stopped)
    indexed.sort(key=lambda item: item[0])
    return [result for _, result in indexed]


def schedule_available(
    config: RunConfig,
    leaderboard: dict[str, Any] | None,
    executor: ThreadPoolExecutor,
    pending: dict[Future[TaskResult], int],
    next_index: int,
    stopped: bool,
) -> int:
    while not stopped and next_index < len(config.tasks) and len(pending) < config.workers:
        task_id = config.tasks[next_index]
        future = executor.submit(run_one, config, task_id, leaderboard)
        pending[future] = next_index
        next_index += 1
    return next_index


def run_one(config: RunConfig, task_id: str, leaderboard: dict[str, Any] | None) -> TaskResult:
    try:
        seed = task_seed(leaderboard, task_id)
        payload = run_task_payload(
            env=config.env,
            task_id=task_id,
            run_id=config.run_id,
            artifact_dir=str(config.artifact_dir),
            leaderboard=config.leaderboard,
            trial_seed=seed,
        )
        return TaskResult.from_payload(payload)
    except Exception as exc:
        return TaskResult(
            task_id=task_id,
            passed=False,
            score=0.0,
            solver="error",
            workspace=Path(),
            error=str(exc),
            score_detail=[],
            wall_seconds=None,
        )


def task_seed(leaderboard: dict[str, Any] | None, task_id: str) -> dict[str, Any] | None:
    if not leaderboard:
        return None
    seeds = leaderboard.get("seeds") or {}
    seed = seeds.get(task_id)
    return seed if isinstance(seed, dict) else None


def print_summary(results: list[TaskResult]) -> None:
    passed = sum(1 for result in results if result.passed)
    wall_sum = sum(result.wall_seconds or 0.0 for result in results)
    print(f"passed={passed}/{len(results)} task_wall_sum_seconds={wall_sum:.3f}", flush=True)
    for result in results:
        status = "ok" if result.passed else "fail"
        wall = "n/a" if result.wall_seconds is None else f"{result.wall_seconds:.3f}s"
        print(f"{result.task_id}: {status} score={result.score:g} wall={wall} solver={result.solver}", flush=True)
