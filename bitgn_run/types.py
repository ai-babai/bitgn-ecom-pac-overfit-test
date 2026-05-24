from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    passed: bool
    score: float
    solver: str
    workspace: Path
    error: str | None
    score_detail: list[str]
    wall_seconds: float | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TaskResult":
        return cls(
            task_id=str(payload.get("task_id", "")),
            passed=bool(payload.get("passed", False)),
            score=float(payload.get("score", 0.0) or 0.0),
            solver=str(payload.get("solver", "unknown")),
            workspace=Path(str(payload.get("workspace", ""))),
            error=str(payload["error"]) if payload.get("error") is not None else None,
            score_detail=[str(item) for item in payload.get("score_detail", [])],
            wall_seconds=float(payload["wall_seconds"]) if payload.get("wall_seconds") is not None else None,
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "passed": self.passed,
            "score": self.score,
            "solver": self.solver,
            "workspace": str(self.workspace),
            "error": self.error,
            "score_detail": self.score_detail,
            "wall_seconds": self.wall_seconds,
        }
