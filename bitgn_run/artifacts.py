from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import RunConfig
from .types import TaskResult


class ArtifactWriter:
    def __init__(self, config: RunConfig) -> None:
        self.run_dir = config.artifact_dir / config.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            self.run_dir / "run_config.json",
            {
                "run_id": config.run_id,
                "run_name": config.run_name,
                "env": config.env,
                "version": config.version,
                "leaderboard": config.leaderboard,
                "fail_fast": config.fail_fast,
                "workers": config.workers,
                "tasks": config.tasks,
                "enabled_rules": sorted(config.enabled_rules),
                "max_wall_sum_seconds": config.max_wall_sum_seconds,
            },
        )

    def append_task(self, result: TaskResult) -> None:
        append_jsonl(self.run_dir / "run_manifest.jsonl", result.to_json())

    def finish(self, results: list[TaskResult]) -> None:
        passed = sum(1 for result in results if result.passed)
        wall_sum = sum(result.wall_seconds or 0.0 for result in results)
        write_json(
            self.run_dir / "run_summary.json",
            {
                "tasks_total": len(results),
                "passed": passed,
                "failed": len(results) - passed,
                "pass_rate": passed / len(results) if results else 0.0,
                "task_wall_time_sum_seconds": wall_sum,
                "results": [result.to_json() for result in results],
            },
        )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=True, default=str) + "\n")
