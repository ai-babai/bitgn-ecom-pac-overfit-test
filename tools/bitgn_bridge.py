#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bitgn.harness_connect import HarnessServiceClientSync
from bitgn.harness_pb2 import EndTrialRequest, GetBenchmarkRequest, GetRunRequest, GetTrialRequest, StartRunRequest, StartTrialRequest, SubmitRunRequest
from bitgn_runtime import BITGN_URL, BitgnAdapter, ToolGateway, call_with_rate_retry, create_task_workspace, open_task_workspace, start_run_with_retry
from ecom_solver import EcomDeterministicSolver
from pac1_solver import Pac1DeterministicSolver


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, default=str), flush=True)


def log(_message: str) -> None:
    return None



def setup_adapter(env: str) -> BitgnAdapter:
    return BitgnAdapter(env=(env or "ecom").strip().lower())


def parse_tasks(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def prepare_leaderboard(args: argparse.Namespace) -> int:
    adapter = setup_adapter(args.env)
    api_key = bitgn_api_key()
    if not api_key:
        raise SystemExit("leaderboard mode requires BITGN_ECOM_API_KEY, BITGN_API_KEY, or ~/.bitgn/bitgn-api-key")
    task_ids = parse_tasks(args.tasks)
    if not task_ids:
        raise SystemExit("prepare-leaderboard requires at least one task")
    client = HarnessServiceClientSync(os.getenv("BENCHMARK_HOST") or BITGN_URL)
    run_name = args.run_name or os.getenv("BITGN_RUN_NAME") or "code-without-llm"
    run = start_run_with_retry(client, StartRunRequest(benchmark_id=adapter.benchmark_id, name=run_name, api_key=api_key))
    run_id = str(run.run_id)
    trial_ids = [str(item) for item in run.trial_ids]
    if len(trial_ids) < len(task_ids):
        raise SystemExit(f"leaderboard run {run_id} returned only {len(trial_ids)} trial ids for {len(task_ids)} tasks")
    if args.env.startswith("pac1"):
        seeds = prepare_trial_id_only_seeds(run_id, trial_ids, task_ids)
    else:
        seeds = prepare_trial_seeds(client, run_id, trial_ids, task_ids)
    emit({"ok": True, "run_id": run_id, "run_name": run_name, "seeds": seeds})
    return 0


def list_tasks(args: argparse.Namespace) -> int:
    adapter = setup_adapter(args.env)
    client = HarnessServiceClientSync(os.getenv("BENCHMARK_HOST") or BITGN_URL)
    data = call_with_rate_retry(lambda: client.get_benchmark(GetBenchmarkRequest(benchmark_id=adapter.benchmark_id)))
    tasks = [str(item.task_id) for item in data.tasks]
    emit({"ok": True, "benchmark_id": adapter.benchmark_id, "tasks": tasks})
    return 0


def bitgn_api_key() -> str:
    for name in ["BITGN_ECOM_API_KEY", "BITGN_API_KEY"]:
        raw = (os.getenv(name) or "").strip()
        if raw:
            return raw
    for name in ["BITGN_ECOM_API_KEY_FILE", "BITGN_API_KEY_FILE"]:
        raw_path = (os.getenv(name) or "").strip()
        if raw_path:
            value = read_secret_file(Path(raw_path).expanduser())
            if value:
                return value
    return read_secret_file(Path.home() / ".bitgn" / "bitgn-api-key")


def read_secret_file(path: Path) -> str:
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


def prepare_trial_seeds(
    client: HarnessServiceClientSync,
    run_id: str,
    trial_ids: list[str],
    task_ids: list[str],
) -> dict[str, dict[str, str]]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    requested = set(task_ids)
    seeds: dict[str, dict[str, str]] = {}

    def start_seed(trial_id: str) -> dict[str, str] | None:
        local_client = HarnessServiceClientSync(os.getenv("BENCHMARK_HOST") or BITGN_URL)
        trial = call_with_rate_retry(lambda: local_client.start_trial(StartTrialRequest(trial_id=trial_id)))
        task_id = str(trial.task_id)
        if task_id not in requested:
            return None
        return {
            "trial_id": str(trial.trial_id),
            "task_id": task_id,
            "instruction": str(trial.instruction),
            "harness_url": str(trial.harness_url),
            "run_id": run_id,
        }

    workers = min(12, max(1, len(trial_ids)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(start_seed, trial_id) for trial_id in trial_ids]
        for future in as_completed(futures):
            seed = future.result()
            if not seed:
                continue
            task_id = seed["task_id"]
            if task_id not in seeds:
                seeds[task_id] = seed
            if len(seeds) == len(requested):
                break
    missing = [task_id for task_id in task_ids if task_id not in seeds]
    if missing:
        raise SystemExit(f"leaderboard run {run_id} did not include requested tasks: {', '.join(missing)}")
    return seeds



def prepare_trial_id_only_seeds(
    run_id: str,
    trial_ids: list[str],
    task_ids: list[str],
) -> dict[str, dict[str, str]]:
    seeds: dict[str, dict[str, str]] = {}
    for task_id in task_ids:
        index = ordered_task_index(task_id)
        if index >= len(trial_ids):
            raise SystemExit(f"leaderboard run returned no trial id for {task_id}")
        trial_id = trial_ids[index]
        seeds[task_id] = {"trial_id": trial_id, "task_id": task_id, "run_id": run_id}
    return seeds


def ordered_task_index(task_id: str) -> int:
    import re
    m = re.fullmatch(r"t(\d+)", task_id.strip().lower())
    if not m:
        raise SystemExit(f"ordered ECOM task id expected, got {task_id!r}")
    return int(m.group(1)) - 1

def submit_leaderboard(args: argparse.Namespace) -> int:
    client = HarnessServiceClientSync(os.getenv("BENCHMARK_HOST") or BITGN_URL)
    call_with_rate_retry(lambda: client.submit_run(SubmitRunRequest(run_id=args.run_id, force=True)))
    emit({"ok": True, "run_id": args.run_id, "submitted": True})
    return 0


def finalize_run(args: argparse.Namespace) -> int:
    client = HarnessServiceClientSync(os.getenv("BENCHMARK_HOST") or BITGN_URL)
    call_with_rate_retry(lambda: client.submit_run(SubmitRunRequest(run_id=args.run_id, force=True)))
    run = call_with_rate_retry(lambda: client.get_run(GetRunRequest(run_id=args.run_id)))
    trials = []
    for head in run.trials:
        trial = call_with_rate_retry(lambda tid=str(head.trial_id): client.get_trial(GetTrialRequest(trial_id=tid)))
        trials.append(trial_score_payload(trial))
    emit({
        "ok": True,
        "run_id": args.run_id,
        "score_available": bool(run.score_available),
        "score": float(run.score) if run.score_available else None,
        "trials": trials,
    })
    return 0


def trial_score_payload(value: Any) -> dict[str, Any]:
    available = bool(getattr(value, "score_available", False))
    score = float(value.score) if available else None
    return {
        "trial_id": str(value.trial_id),
        "task_id": str(value.task_id),
        "score_available": available,
        "score": score,
        "passed": score == 1.0 if available else None,
        "score_detail": [str(item) for item in value.score_detail],
        "error": str(getattr(value, "error", "") or "") or None,
    }

def start(args: argparse.Namespace) -> int:
    os.environ.setdefault("BENCHMARK_ID", "bitgn/ecom1-dev")
    os.environ.setdefault("AGENT_ENV", "ecom")
    adapter = setup_adapter("ecom")
    client = HarnessServiceClientSync(os.getenv("BENCHMARK_HOST") or BITGN_URL)
    if args.leaderboard:
        raise SystemExit("leaderboard mode is not implemented in the bridge yet")
    trial = adapter.start_trial(client=client, task_id=args.task_id, trial_seed=None, api_key=bitgn_api_key(), log=log)
    ws = create_task_workspace(
        base_dir=args.artifact_dir,
        benchmark_id=os.environ["BENCHMARK_ID"],
        task_id=args.task_id,
        env="ecom",
        model="deterministic",
        local_run_id=args.run_id,
    )
    ws.instruction_path.write_text(trial.instruction + "\n", encoding="utf-8")
    adapter.write_context(workspace=ws, task_id=args.task_id, run_id=args.run_id, harness_url=trial.harness_url)
    adapter.hydrate_workspace(workspace=ws, instruction=trial.instruction)
    ws.write_json(ws.root / "bridge_trial.json", {"trial_id": trial.trial_id, "task_id": args.task_id, "started_at": now()})
    emit({"ok": True, "task_id": args.task_id, "trial_id": trial.trial_id, "workspace": str(ws.root), "instruction": trial.instruction})
    return 0

def tool(args: argparse.Namespace) -> int:
    ws = open_task_workspace(args.workspace)
    gateway = ToolGateway.from_workspace_context(ws)
    payload = json.loads(args.args or "{}")
    result = gateway.call(step=int(args.step), tool=args.tool, args=payload)
    if args.tool == "report_completion":
        refs = payload.get("grounding_refs") or payload.get("supporting_refs") or []
        ws.write_json(ws.submission_path, {"message": payload.get("message", ""), "answer": payload.get("answer", payload.get("message", "")), "outcome": payload.get("outcome", "OUTCOME_NONE_UNSUPPORTED"), "grounding_refs": refs})
    emit({"ok": True, "tool": args.tool, "result": protobuf_to_jsonable(result)})
    return 0


def finish(args: argparse.Namespace) -> int:
    ws = open_task_workspace(args.workspace)
    meta = json.loads((ws.root / "bridge_trial.json").read_text(encoding="utf-8"))
    client = HarnessServiceClientSync(os.getenv("BENCHMARK_HOST") or BITGN_URL)
    result = call_with_rate_retry(lambda: client.end_trial(EndTrialRequest(trial_id=str(meta["trial_id"]))))
    score_payload = end_trial_score_payload(result, meta.get("task_id"))
    ws.write_json(ws.score_path, {**score_payload, "ts": now()})
    emit({"ok": True, **score_payload})
    return 0



def autosolve(args: argparse.Namespace) -> int:
    ws = open_task_workspace(args.workspace)
    gateway = ToolGateway.from_workspace_context(ws)
    report = EcomDeterministicSolver(gateway, args.instruction).solve()
    emit({"ok": True, **report})
    return 0


def run_task(args: argparse.Namespace) -> int:
    adapter = setup_adapter(args.env)
    client = HarnessServiceClientSync(os.getenv("BENCHMARK_HOST") or BITGN_URL)
    trial_seed = json.loads(args.trial_seed) if args.trial_seed else None
    if args.leaderboard and trial_seed is None:
        raise SystemExit("leaderboard run-task requires --trial-seed")
    if args.leaderboard and trial_seed and not trial_seed.get("harness_url"):
        raw_trial = call_with_rate_retry(lambda: client.start_trial(StartTrialRequest(trial_id=str(trial_seed["trial_id"]))))
        actual_task_id = str(raw_trial.task_id)
        trial = adapter.start_trial(client=client, task_id=actual_task_id, trial_seed={"trial_id": str(raw_trial.trial_id), "harness_url": str(raw_trial.harness_url), "instruction": str(raw_trial.instruction)}, api_key=bitgn_api_key(), log=log)
    else:
        actual_task_id = args.task_id
        trial = adapter.start_trial(client=client, task_id=args.task_id, trial_seed=trial_seed, api_key=bitgn_api_key(), log=log)
    runtime_env = "pac1" if args.env.startswith("pac1") else args.env
    ws = create_task_workspace(
        base_dir=args.artifact_dir,
        benchmark_id=os.environ["BENCHMARK_ID"],
        task_id=actual_task_id,
        env=runtime_env,
        model="deterministic",
        local_run_id=args.run_id,
    )
    started = time.monotonic()
    ws.instruction_path.write_text(trial.instruction + "\n", encoding="utf-8")
    adapter.write_context(workspace=ws, task_id=actual_task_id, run_id=args.run_id, harness_url=trial.harness_url)
    gateway = adapter.create_gateway(harness_url=trial.harness_url, workspace=ws, task_id=actual_task_id)
    adapter.hydrate_workspace(workspace=ws, instruction=trial.instruction)
    ws.write_json(ws.root / "bridge_trial.json", {"trial_id": trial.trial_id, "task_id": actual_task_id, "started_at": now()})
    if args.env.startswith("pac1"):
        report = Pac1DeterministicSolver(gateway, trial.instruction, actual_task_id).solve()
    else:
        report = EcomDeterministicSolver(gateway, trial.instruction).solve()
    completion = report.get("completion", {})
    refs = completion.get("refs") or []
    payload = {"message": completion.get("message", ""), "outcome": completion.get("outcome", "OUTCOME_NONE_UNSUPPORTED"), "grounding_refs": refs}
    gateway.call(step=0, tool="report_completion", args=payload)
    ws.write_json(ws.submission_path, {"message": payload["message"], "answer": payload["message"], "outcome": payload["outcome"], "grounding_refs": refs})
    wall_seconds = time.monotonic() - started
    result = call_with_rate_retry(lambda: client.end_trial(EndTrialRequest(trial_id=str(trial.trial_id))))
    score_payload = end_trial_score_payload(result, actual_task_id)
    ws.write_json(ws.score_path, {**score_payload, "ts": now(), "wall_seconds": wall_seconds})
    emit({
        "ok": True,
        "task_id": actual_task_id,
        "trial_id": str(trial.trial_id),
        "run_id": str(trial_seed.get("run_id", "") if isinstance(trial_seed, dict) else ""),
        "passed": score_payload["passed"],
        "score_available": score_payload["score_available"],
        "score": score_payload["score"],
        "solver": report.get("solver", "deterministic"),
        "workspace": str(ws.root),
        "error": None,
        "score_detail": score_payload["score_detail"],
        "wall_seconds": wall_seconds,
    })
    return 0


def end_trial_score_payload(value: Any, task_id: Any) -> dict[str, Any]:
    available = bool(getattr(value, "score_available", False))
    score = float(value.score) if available else None
    return {
        "trial_id": str(value.trial_id),
        "task_id": str(task_id or ""),
        "score_available": available,
        "score": score,
        "passed": score == 1.0 if available else None,
        "score_detail": [str(item) for item in value.score_detail],
    }


def protobuf_to_jsonable(value: Any) -> Any:
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    try:
        from google.protobuf.json_format import MessageToDict

        return MessageToDict(value, preserving_proto_field_name=True)
    except Exception:
        return str(value)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare-leaderboard")
    p.add_argument("--env", default="ecom")
    p.add_argument("--tasks", required=True)
    p.add_argument("--run-name", default="")
    p.set_defaults(func=prepare_leaderboard)
    p = sub.add_parser("list-tasks")
    p.add_argument("--env", default="ecom")
    p.set_defaults(func=list_tasks)
    p = sub.add_parser("submit-leaderboard")
    p.add_argument("--run-id", required=True)
    p.set_defaults(func=submit_leaderboard)
    p = sub.add_parser("finalize-run")
    p.add_argument("--run-id", required=True)
    p.set_defaults(func=finalize_run)
    p = sub.add_parser("start")
    p.add_argument("--task-id", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--artifact-dir", required=True)
    p.add_argument("--leaderboard", action="store_true")
    p.set_defaults(func=start)
    p = sub.add_parser("tool")
    p.add_argument("--workspace", required=True)
    p.add_argument("--tool", required=True)
    p.add_argument("--args", default="{}")
    p.add_argument("--step", default="0")
    p.set_defaults(func=tool)
    p = sub.add_parser("finish")
    p.add_argument("--workspace", required=True)
    p.set_defaults(func=finish)
    p = sub.add_parser("autosolve")
    p.add_argument("--workspace", required=True)
    p.add_argument("--instruction", required=True)
    p.set_defaults(func=autosolve)
    p = sub.add_parser("run-task")
    p.add_argument("--env", default="ecom")
    p.add_argument("--task-id", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--artifact-dir", required=True)
    p.add_argument("--leaderboard", action="store_true")
    p.add_argument("--trial-seed", default="")
    p.set_defaults(func=run_task)
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
