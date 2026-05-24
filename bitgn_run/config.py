from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from pathlib import Path

SUPPORTED_ENVS = {"ecom", "pac1", "pac1-prod"}
DEFAULT_RULES = {"catalog", "inventory", "security"}


@dataclass(frozen=True)
class RunConfig:
    run_id: str
    run_name: str
    env: str
    version: str
    leaderboard: bool
    fail_fast: bool
    workers: int
    tasks: list[str]
    artifact_dir: Path
    enabled_rules: set[str] = field(default_factory=lambda: set(DEFAULT_RULES))
    max_wall_sum_seconds: float | None = None


def config_from_args(argv: list[str] | None = None) -> RunConfig:
    parser = argparse.ArgumentParser(prog="bitgn-ecom-pac-lab")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--run-id", default=f"det-{int(time.time())}")
    run.add_argument("--run-name", default="")
    run.add_argument("--env", default="ecom")
    run.add_argument("--version", default="0.1.0")
    run.add_argument("--leaderboard", default="false")
    run.add_argument("--fail-fast", default="false")
    run.add_argument("--workers", type=int, default=1)
    run.add_argument("--tasks", default="")
    run.add_argument("--artifact-dir", default="runs")
    run.add_argument("--rules", default=",".join(sorted(DEFAULT_RULES)))
    run.add_argument("--max-wall-sum-seconds", type=float, default=None)
    args = parser.parse_args(argv)
    env = args.env.strip().lower()
    if env not in SUPPORTED_ENVS:
        parser.error(f"unsupported env: {env}")
    tasks = parse_tasks(args.tasks) or default_tasks()
    return RunConfig(
        run_id=args.run_id,
        run_name=args.run_name,
        env=env,
        version=args.version,
        leaderboard=parse_bool(args.leaderboard),
        fail_fast=parse_bool(args.fail_fast),
        workers=max(1, int(args.workers)),
        tasks=tasks,
        artifact_dir=Path(args.artifact_dir),
        enabled_rules=set(parse_tasks(args.rules)),
        max_wall_sum_seconds=args.max_wall_sum_seconds,
    )


def default_tasks() -> list[str]:
    return [f"t{number:02}" for number in range(1, 6)]


def parse_tasks(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_bool(value: object) -> bool:
    raw = str(value).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid bool: {value}")
