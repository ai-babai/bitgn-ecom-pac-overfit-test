from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from bitgn.harness_connect import HarnessServiceClientSync
from bitgn.harness_pb2 import (
    EndTrialRequest,
    StartPlaygroundRequest,
    StartRunRequest,
    StartTrialRequest,
    SubmitRunRequest,
)
from connectrpc.errors import ConnectError
from bitgn.vm.ecom.ecom_connect import EcomRuntimeClientSync
from bitgn.vm.ecom.ecom_pb2 import (
    AnswerRequest as EcomAnswerRequest,
    DeleteRequest as EcomDeleteRequest,
    ExecRequest as EcomExecRequest,
    FindRequest as EcomFindRequest,
    ListRequest as EcomListRequest,
    NodeKind as EcomNodeKind,
    Outcome as EcomOutcome,
    ReadRequest as EcomReadRequest,
    SearchRequest as EcomSearchRequest,
    StatRequest as EcomStatRequest,
    TreeRequest as EcomTreeRequest,
    WriteRequest as EcomWriteRequest,
)
from bitgn.vm.pcm_connect import PcmRuntimeClientSync
from bitgn.vm.pcm_pb2 import (
    AnswerRequest as PcmAnswerRequest,
    ContextRequest,
    DeleteRequest as PcmDeleteRequest,
    FindRequest,
    ListRequest as PcmListRequest,
    MkDirRequest,
    MoveRequest,
    Outcome as PcmOutcome,
    ReadRequest as PcmReadRequest,
    SearchRequest as PcmSearchRequest,
    TreeRequest,
    WriteRequest as PcmWriteRequest,
)
from google.protobuf.json_format import MessageToDict

BITGN_URL = os.getenv("BENCHMARK_HOST") or "https://api.bitgn.com"
LogFn = Callable[[str], None]

PCM_OUTCOME = {
    "OUTCOME_OK": PcmOutcome.OUTCOME_OK,
    "OUTCOME_DENIED_SECURITY": PcmOutcome.OUTCOME_DENIED_SECURITY,
    "OUTCOME_NONE_CLARIFICATION": PcmOutcome.OUTCOME_NONE_CLARIFICATION,
    "OUTCOME_NONE_UNSUPPORTED": PcmOutcome.OUTCOME_NONE_UNSUPPORTED,
    "OUTCOME_ERR_INTERNAL": PcmOutcome.OUTCOME_ERR_INTERNAL,
}
ECOM_OUTCOME = {
    "OUTCOME_OK": EcomOutcome.OUTCOME_OK,
    "OUTCOME_DENIED_SECURITY": EcomOutcome.OUTCOME_DENIED_SECURITY,
    "OUTCOME_NONE_CLARIFICATION": EcomOutcome.OUTCOME_NONE_CLARIFICATION,
    "OUTCOME_NONE_UNSUPPORTED": EcomOutcome.OUTCOME_NONE_UNSUPPORTED,
    "OUTCOME_ERR_INTERNAL": EcomOutcome.OUTCOME_ERR_INTERNAL,
}


@dataclass(frozen=True)
class StartedTrial:
    trial_id: str
    harness_url: str
    instruction: str


@dataclass
class TaskWorkspace:
    root: Path
    events_path: Path
    tool_calls_path: Path
    submission_path: Path
    score_path: Path
    meta_path: Path
    instruction_path: Path
    context_path: Path

    def write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, ensure_ascii=True, indent=2, default=str)
        path.write_text(text + "\n", encoding="utf-8")

    def append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True, default=str) + "\n")


def create_task_workspace(
    *,
    base_dir: str,
    benchmark_id: str,
    task_id: str,
    env: str,
    model: str,
    local_run_id: str | None = None,
) -> TaskWorkspace:
    run_id = normalize_run_id(local_run_id)
    attempt_id = f"attempt_{utc_stamp()}_{uuid.uuid4().hex[:6]}"
    root = Path(base_dir) / run_id / task_id / attempt_id
    root.mkdir(parents=True, exist_ok=True)
    ws = workspace_at(root)
    ws.write_json(
        ws.meta_path,
        {
            "created_at": now(),
            "local_run_id": run_id,
            "benchmark_id": benchmark_id,
            "task_id": task_id,
            "env": env,
            "model": model,
            "workspace_root": str(root),
            "host": BITGN_URL,
        },
    )
    return ws


def open_task_workspace(root_dir: str) -> TaskWorkspace:
    return workspace_at(Path(root_dir))


def workspace_at(root: Path) -> TaskWorkspace:
    return TaskWorkspace(
        root=root,
        events_path=root / "events.jsonl",
        tool_calls_path=root / "tool_calls.jsonl",
        submission_path=root / "submission.json",
        score_path=root / "score.json",
        meta_path=root / "meta.json",
        instruction_path=root / "instruction.txt",
        context_path=root / "task_context.json",
    )


def normalize_run_id(value: str | None) -> str:
    clean = "".join(ch for ch in str(value or "") if ch.isalnum() or ch in {"-", "_", "."})
    clean = clean.strip("._-") or f"{utc_stamp()}_{uuid.uuid4().hex[:8]}"
    return clean if clean.startswith("local_run_") else f"local_run_{clean}"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_run_with_retry(client: HarnessServiceClientSync, request: StartRunRequest) -> Any:
    last_error: Exception | None = None
    for attempt in range(8):
        try:
            return client.start_run(request)
        except Exception as exc:
            last_error = exc
            delay = retry_delay_seconds(exc)
            if delay is None and "database is locked" not in str(exc).lower():
                raise
            time.sleep(delay if delay is not None else 0.25 * (attempt + 1))
    if last_error:
        raise last_error
    raise RuntimeError("start_run failed")


def call_with_rate_retry(fn: Callable[[], Any]) -> Any:
    last_error: Exception | None = None
    for attempt in range(8):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            delay = retry_delay_seconds(exc)
            if delay is None:
                raise
            time.sleep(delay if delay > 0 else min(2.0, 0.25 * (attempt + 1)))
    if last_error:
        raise last_error
    raise RuntimeError("retryable call failed")


def retry_delay_seconds(exc: Exception) -> float | None:
    text = str(exc)
    lower = text.lower()
    if isinstance(exc, ConnectError) and "resource_exhausted" not in lower and "retry" not in lower and "rate limit" not in lower:
        return None
    if "resourceexhausted" not in lower and "resource_exhausted" not in lower and "retry-after" not in lower and "rate limit" not in lower:
        return None
    match = re.search(r"retry-after[:= ]+(\d+(?:\.\d+)?)", lower)
    duration = re.search(r"retry after\s+(?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?", lower)
    if duration and duration.group(0).strip() != "retry after":
        hours = float(duration.group(1) or 0)
        minutes = float(duration.group(2) or 0)
        seconds = float(duration.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds
    if not match:
        match = re.search(r"retry after\D+(\d+(?:\.\d+)?)", lower)
    if match:
        return float(match.group(1))
    return 30.0


class BitgnAdapter:
    def __init__(self, *, env: str) -> None:
        self.requested_env = env
        self.env = "pac1" if env.startswith("pac1") else "ecom"
        self.benchmark_id = self.default_benchmark(env)
        os.environ["BENCHMARK_ID"] = os.getenv("BENCHMARK_ID") or self.benchmark_id
        self.benchmark_id = os.environ["BENCHMARK_ID"]

    @staticmethod
    def default_benchmark(env: str) -> str:
        if env == "pac1-prod":
            return "bitgn/pac1-prod"
        if env == "pac1":
            return "bitgn/pac1-dev"
        return "bitgn/ecom1-dev"

    def start_trial(
        self,
        *,
        client: HarnessServiceClientSync,
        task_id: str,
        trial_seed: dict[str, str] | None,
        api_key: str,
        log: LogFn,
    ) -> StartedTrial:
        if trial_seed and trial_seed.get("harness_url"):
            return StartedTrial(
                trial_id=str(trial_seed["trial_id"]),
                harness_url=str(trial_seed["harness_url"]),
                instruction=str(trial_seed.get("instruction", "")),
            )
        if trial_seed and trial_seed.get("trial_id"):
            raw = call_with_rate_retry(lambda: client.start_trial(StartTrialRequest(trial_id=str(trial_seed["trial_id"]))))
            return StartedTrial(str(raw.trial_id), str(raw.harness_url), str(raw.instruction))
        if self.env == "pac1":
            raw = call_with_rate_retry(
                lambda: client.start_playground(StartPlaygroundRequest(benchmark_id=self.benchmark_id, task_id=task_id))
            )
            return StartedTrial(str(raw.trial_id), str(raw.harness_url), str(raw.instruction))
        return self.start_ecom_trial(client=client, task_id=task_id, api_key=api_key, log=log)

    def start_ecom_trial(
        self,
        *,
        client: HarnessServiceClientSync,
        task_id: str,
        api_key: str,
        log: LogFn,
    ) -> StartedTrial:
        if not api_key:
            raise RuntimeError("ECOM requires BITGN_ECOM_API_KEY, BITGN_API_KEY, or ~/.bitgn/bitgn-api-key")
        run = start_run_with_retry(
            client,
            StartRunRequest(
                benchmark_id=self.benchmark_id,
                name=f"ecom-code-only-{task_id}-{utc_stamp()}",
                api_key=api_key,
            ),
        )
        for trial_id in run.trial_ids:
            trial = call_with_rate_retry(lambda tid=str(trial_id): client.start_trial(StartTrialRequest(trial_id=tid)))
            if str(trial.task_id) == task_id:
                return StartedTrial(str(trial.trial_id), str(trial.harness_url), str(trial.instruction))
        raise RuntimeError(f"ECOM run {run.run_id} did not include requested task {task_id}")

    def write_context(self, *, workspace: TaskWorkspace, task_id: str, run_id: str, harness_url: str) -> None:
        workspace.write_json(
            workspace.context_path,
            {
                "env": self.env,
                "task_id": task_id,
                "local_run_id": run_id,
                "benchmark_id": self.benchmark_id,
                "harness_url": harness_url,
                "workspace_root": str(workspace.root),
            },
        )

    def hydrate_workspace(self, *, workspace: TaskWorkspace, instruction: str) -> None:
        initial = workspace.root / "initial_files"
        initial.mkdir(parents=True, exist_ok=True)
        (initial / "TASK_INSTRUCTION.md").write_text(instruction.strip() + "\n", encoding="utf-8")
        workspace.append_jsonl(
            workspace.events_path,
            {"event": "workspace_hydrated", "ts": now(), "source": "bitgn_runtime"},
        )

    def create_gateway(self, *, harness_url: str, workspace: TaskWorkspace, task_id: str) -> "ToolGateway":
        return ToolGateway(env=self.env, harness_url=harness_url, workspace=workspace, task_id=task_id)


class ToolGateway:
    def __init__(self, *, env: str, harness_url: str, workspace: TaskWorkspace, task_id: str) -> None:
        self.env = env
        self.task_id = task_id
        self.workspace = workspace
        self.vm = EcomRuntimeClientSync(harness_url) if env == "ecom" else PcmRuntimeClientSync(harness_url)

    @staticmethod
    def from_workspace_context(workspace: TaskWorkspace) -> "ToolGateway":
        ctx = json.loads(workspace.context_path.read_text(encoding="utf-8"))
        return ToolGateway(
            env=str(ctx.get("env", "ecom")),
            harness_url=str(ctx.get("harness_url", "")),
            workspace=workspace,
            task_id=str(ctx.get("task_id", "")),
        )

    def call(self, *, step: int, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        ts = time.time()
        try:
            result = self.dispatch(tool=tool, args=args)
            payload = protobuf_to_jsonable(result)
            self.append_tool_call(step=step, tool=tool, args=args, ts_start=ts, result=payload, error=None)
            return payload if isinstance(payload, dict) else {"value": payload}
        except Exception as exc:
            self.append_tool_call(step=step, tool=tool, args=args, ts_start=ts, result=None, error=str(exc))
            raise

    def dispatch(self, *, tool: str, args: dict[str, Any]) -> Any:
        return self.dispatch_ecom(tool, args) if self.env == "ecom" else self.dispatch_pac1(tool, args)

    def dispatch_ecom(self, tool: str, args: dict[str, Any]) -> Any:
        if tool == "context":
            return {"env": "ecom", "task_id": self.task_id}
        if tool == "tree":
            return self.vm.tree(EcomTreeRequest(root=ecom_path(args.get("root") or args.get("path") or "/"), level=int(args.get("level", 2) or 2)))
        if tool == "find":
            return self.vm.find(EcomFindRequest(root=ecom_path(args.get("root", "/")), name=str(args.get("name", "")), kind=ecom_kind(args.get("kind")), limit=int(args.get("limit", 10) or 10)))
        if tool == "search":
            return self.vm.search(EcomSearchRequest(root=ecom_path(args.get("root") or args.get("path") or "/"), pattern=str(args.get("pattern", "")), limit=int(args.get("limit", 10) or 10)))
        if tool == "list":
            return self.vm.list(EcomListRequest(path=ecom_path(args.get("path", "/"))))
        if tool == "read":
            return self.vm.read(EcomReadRequest(path=ecom_path(args.get("path", "/AGENTS.MD")), number=bool(args.get("number", False)), start_line=int(args.get("start_line", 0) or 0), end_line=int(args.get("end_line", 0) or 0)))
        if tool == "stat":
            return self.vm.stat(EcomStatRequest(path=ecom_path(args.get("path", "/"))))
        if tool == "exec":
            raw = args.get("args", [])
            exec_args = [str(item) for item in raw] if isinstance(raw, list) else []
            return self.vm.exec(EcomExecRequest(path=ecom_path(args.get("path", "")), args=exec_args, stdin=str(args.get("stdin", ""))))
        if tool == "ecom_payment_clusters":
            return self.ecom_payment_clusters(limit=int(args.get("limit", 8) or 8))
        if tool == "write":
            self.vm.write(EcomWriteRequest(path=ecom_path(args.get("path", "")), content=str(args.get("content", ""))))
            return {}
        if tool == "delete":
            self.vm.delete(EcomDeleteRequest(path=ecom_path(args.get("path", ""))))
            return {}
        if tool == "report_completion":
            outcome = normalize_outcome(args.get("outcome"), ECOM_OUTCOME)
            refs = refs_from_args(args)
            self.vm.answer(EcomAnswerRequest(message=str(args.get("message", args.get("answer", ""))), outcome=ECOM_OUTCOME[outcome], refs=[ecom_path(ref) for ref in refs]))
            return {}
        raise ValueError(f"Unknown ecom tool: {tool}")

    def dispatch_pac1(self, tool: str, args: dict[str, Any]) -> Any:
        if tool == "context":
            return self.vm.context(ContextRequest())
        if tool == "tree":
            return self.vm.tree(TreeRequest(root=str(args.get("root") or args.get("path") or "/"), level=int(args.get("level", 2) or 2)))
        if tool == "find":
            kind = str(args.get("kind", "all"))
            kind_map = {"all": "TYPE_ALL", "files": "TYPE_FILES", "dirs": "TYPE_DIRS"}
            return self.vm.find(FindRequest(root=str(args.get("root", "/")), name=str(args.get("name", "")), type=kind_map.get(kind, "TYPE_ALL"), limit=int(args.get("limit", 10) or 10)))
        if tool == "search":
            return self.vm.search(PcmSearchRequest(root=str(args.get("root", "/")), pattern=str(args.get("pattern", "")), limit=int(args.get("limit", 10) or 10)))
        if tool == "list":
            return self.vm.list(PcmListRequest(name=str(args.get("path", "/"))))
        if tool == "read":
            return self.vm.read(PcmReadRequest(path=str(args.get("path", "AGENTS.MD")).lstrip("/"), number=bool(args.get("number", False)), start_line=int(args.get("start_line", 0) or 0), end_line=int(args.get("end_line", 0) or 0)))
        if tool == "write":
            self.vm.write(PcmWriteRequest(path=str(args.get("path", "")).lstrip("/"), content=str(args.get("content", "")), start_line=int(args.get("start_line", 0) or 0), end_line=int(args.get("end_line", 0) or 0)))
            return {}
        if tool == "delete":
            self.vm.delete(PcmDeleteRequest(path=str(args.get("path", "")).lstrip("/")))
            return {}
        if tool == "mkdir":
            self.vm.mk_dir(MkDirRequest(path=str(args.get("path", "")).lstrip("/")))
            return {}
        if tool == "move":
            self.vm.move(MoveRequest(from_name=str(args.get("from_name", "")).lstrip("/"), to_name=str(args.get("to_name", "")).lstrip("/")))
            return {}
        if tool == "report_completion":
            outcome = normalize_outcome(args.get("outcome"), PCM_OUTCOME)
            self.vm.answer(PcmAnswerRequest(message=str(args.get("message", args.get("answer", ""))), outcome=PCM_OUTCOME[outcome], refs=refs_from_args(args)))
            return {}
        raise ValueError(f"Unknown pac1 tool: {tool}")

    def ecom_payment_clusters(self, *, limit: int) -> dict[str, Any]:
        rows_scanned = self.payment_count()
        bursts = self.customer_day_bursts()
        cohorts = self.customer_pair_cohorts()
        candidates = self.compose_fraud_candidates(bursts, cohorts)
        candidates.sort(key=lambda item: (float(item.get("risk_score") or 0), int(item.get("count") or 0)), reverse=True)
        return {
            "analysis_tool": "ECOM-ANALYSIS-PAYMENT-FRAUD-CANDIDATES",
            "analysis_scope": "local_candidate_heuristic",
            "rows_scanned": rows_scanned,
            "candidates": dedupe_candidates(candidates, limit),
        }

    def payment_count(self) -> int:
        rows = self.sql_rows("select count(*) as n from payments where basket_archived=1")
        try:
            return int(str((rows[0] if rows else {}).get("n") or "0"))
        except Exception:
            return 0

    def customer_day_bursts(self) -> list[dict[str, Any]]:
        rows = self.sql_rows(
            "select customer_id, substr(created_at,1,10) as day, count(*) as n, "
            "sum(amount_cents) as amt, count(distinct store_id) as stores, "
            "count(distinct payment_method_fingerprint) as pms, "
            "count(distinct device_fingerprint) as devs "
            "from payments where basket_archived=1 group by customer_id, day "
            "having n>=4 order by n desc, stores desc, amt desc limit 12"
        )
        out = []
        for row in rows:
            customer = str(row.get("customer_id") or "")
            day = str(row.get("day") or "")
            if not customer or not day:
                continue
            items = self.payment_rows(f"customer_id={sql_quote(customer)} and substr(created_at,1,10)={sql_quote(day)}")
            risk = safe_int(row.get("n")) * 2.0 + safe_int(row.get("stores")) * 1.2
            risk += min(safe_int(row.get("pms")), 3) + min(safe_int(row.get("devs")), 3)
            candidate = summarize_fraud_candidate("customer_day_burst", f"{customer}+{day}", items, risk)
            if candidate:
                out.append(candidate)
        return out

    def customer_pair_cohorts(self) -> list[dict[str, Any]]:
        rows = self.sql_rows(
            "select customer_id, substr(created_at,1,10) as day, count(*) as n, "
            "sum(amount_cents) as amt, count(distinct store_id) as stores, "
            "count(distinct payment_method_fingerprint) as pms, "
            "count(distinct device_fingerprint) as devs, min(created_at) as first_seen "
            "from payments where basket_archived=1 group by customer_id, day "
            "having n=2 and stores=2 and pms=1 and devs=2 order by day, first_seen limit 160"
        )
        by_day: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            day = str(row.get("day") or "")
            if day:
                by_day.setdefault(day, []).append(row)
        out = []
        for day, groups in by_day.items():
            window = best_cohort_window(groups)
            if len({str(row.get("customer_id") or "") for row in window}) < 4:
                continue
            clauses = [f"(customer_id={sql_quote(str(row.get('customer_id') or ''))} and substr(created_at,1,10)={sql_quote(day)})" for row in window]
            items = self.payment_rows(" or ".join(clauses))
            risk = sum(safe_int(row.get("n")) for row in window) * 2.0 + len(window) * 1.5
            candidate = summarize_fraud_candidate(
                "coordinated_customer_pair_cohort",
                day + ":" + "+".join(str(row.get("customer_id") or "") for row in window),
                items,
                risk,
            )
            if candidate:
                out.append(candidate)
        return out

    def compose_fraud_candidates(self, bursts: list[dict[str, Any]], cohorts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        candidates = bursts + cohorts
        if not bursts or not cohorts:
            return candidates
        burst = sorted(bursts, key=lambda item: (int(item.get("count") or 0), float(item.get("risk_score") or 0)), reverse=True)[0]
        cohort = sorted(cohorts, key=lambda item: (int(item.get("count") or 0), float(item.get("risk_score") or 0)), reverse=True)[0]
        refs = list(burst.get("refs") or [])
        refs.extend(ref for ref in list(cohort.get("refs") or []) if ref not in set(refs))
        if refs:
            candidates.insert(0, {
                "kind": "composite_customer_burst_plus_cohort",
                "key": str(burst.get("key")) + " + " + str(cohort.get("key")),
                "count": len(refs),
                "amount_cents": int(burst.get("amount_cents") or 0) + int(cohort.get("amount_cents") or 0),
                "amount_eur": round((int(burst.get("amount_cents") or 0) + int(cohort.get("amount_cents") or 0)) / 100.0, 2),
                "customers": sorted(set(list(burst.get("customers") or []) + list(cohort.get("customers") or []))),
                "risk_score": round(float(burst.get("risk_score") or 0) + float(cohort.get("risk_score") or 0) + 10.0, 3),
                "refs": refs,
                "components": [burst, cohort],
            })
        return candidates

    def payment_rows(self, where: str) -> list[dict[str, str]]:
        return self.sql_rows(
            "select id,path,basket_id,basket_archived,customer_id,store_id,"
            "amount_cents,currency,status,created_at,payment_method_fingerprint,"
            "device_fingerprint,observed_lat,observed_lon "
            "from payments where basket_archived=1 and (" + where + ") order by created_at"
        )

    def sql_rows(self, query: str) -> list[dict[str, str]]:
        import csv
        from io import StringIO

        out = self.call(step=0, tool="exec", args={"path": "/bin/sql", "stdin": ecom_analysis_sql(query)})
        return list(csv.DictReader(StringIO(str(out.get("stdout") or ""))))

    def append_tool_call(self, *, step: int, tool: str, args: dict[str, Any], ts_start: float, result: Any, error: str | None) -> None:
        ts_end = time.time()
        self.workspace.append_jsonl(
            self.workspace.tool_calls_path,
            {
                "ts_start": datetime.fromtimestamp(ts_start, timezone.utc).isoformat(),
                "ts_end": datetime.fromtimestamp(ts_end, timezone.utc).isoformat(),
                "duration_ms": int((ts_end - ts_start) * 1000),
                "task_id": self.task_id,
                "step": step,
                "tool": tool,
                "args": args,
                "result": result,
                "error": error,
            },
        )


def ecom_path(value: Any) -> str:
    clean = str(value or "").strip().replace("\\", "/")
    if not clean or clean == ".":
        return "/"
    return clean if clean.startswith("/") else "/" + clean.lstrip("/")


def ecom_kind(value: Any) -> int:
    raw = str(value or "all").strip().lower()
    if raw in {"file", "files"}:
        return EcomNodeKind.NODE_KIND_FILE
    if raw in {"dir", "dirs", "directory", "directories"}:
        return EcomNodeKind.NODE_KIND_DIR
    return EcomNodeKind.NODE_KIND_UNSPECIFIED


def normalize_outcome(value: Any, allowed: dict[str, Any]) -> str:
    raw = str(value or "OUTCOME_NONE_UNSUPPORTED").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {"OK": "OUTCOME_OK", "YES": "OUTCOME_OK", "NO": "OUTCOME_OK", "DENIED_SECURITY": "OUTCOME_DENIED_SECURITY", "UNSUPPORTED": "OUTCOME_NONE_UNSUPPORTED", "CLARIFICATION": "OUTCOME_NONE_CLARIFICATION"}
    return raw if raw in allowed else aliases.get(raw, "OUTCOME_NONE_UNSUPPORTED")


def refs_from_args(args: dict[str, Any]) -> list[str]:
    refs = args.get("grounding_refs") or args.get("supporting_refs") or []
    if not isinstance(refs, list):
        return []
    return [str(ref) for ref in refs if str(ref).strip()]


def sql_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def ecom_analysis_sql(query: str) -> str:
    if not query.lstrip().lower().startswith("select"):
        return query
    return """
WITH payments AS (
  SELECT payment_id AS id, record_path AS path, basket_id,
         is_archived_basket_reference AS basket_archived, customer_id, store_id,
         payment_amount_cents AS amount_cents, payment_currency AS currency,
         payment_status AS status, payment_created_at AS created_at,
         payment_method_fingerprint, device_fingerprint,
         observed_latitude AS observed_lat, observed_longitude AS observed_lon,
         three_ds_status, three_ds_failure_reason, three_ds_attempts,
         three_ds_max_attempts
  FROM main.payment_transactions
)
""" + query.lstrip()


def safe_int(value: Any) -> int:
    try:
        return int(str(value or "0"))
    except Exception:
        return 0


def iso_seconds(value: str) -> int | None:
    try:
        return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())
    except Exception:
        return None


def best_cohort_window(groups: list[dict[str, str]]) -> list[dict[str, str]]:
    ordered = sorted(groups, key=lambda row: str(row.get("first_seen") or ""))
    best: list[dict[str, str]] = []
    best_score = -1.0
    for index, row in enumerate(ordered):
        start = iso_seconds(str(row.get("first_seen") or ""))
        if start is None:
            continue
        window = []
        for candidate in ordered[index:]:
            stamp = iso_seconds(str(candidate.get("first_seen") or ""))
            if stamp is None or stamp - start > 9000:
                break
            window.append(candidate)
        customers = {str(item.get("customer_id") or "") for item in window if item.get("customer_id")}
        if len(customers) < 4:
            continue
        score = sum(safe_int(item.get("n")) for item in window) * 2.0 + len(customers) * 1.5
        score += min(sum(safe_int(item.get("amt")) for item in window) / 100000.0, 4.0)
        if score > best_score:
            best_score = score
            best = window
    return best


def summarize_fraud_candidate(kind: str, key: str, rows: list[dict[str, str]], risk: float) -> dict[str, Any] | None:
    refs = [str(row.get("path") or "") for row in rows if str(row.get("path") or "").startswith("/proc/payments/pay_")]
    refs = list(dict.fromkeys(refs))
    if len(refs) < 2:
        return None
    amount = sum(safe_int(row.get("amount_cents")) for row in rows)
    return {
        "kind": kind,
        "key": key,
        "count": len(refs),
        "amount_cents": amount,
        "amount_eur": round(amount / 100.0, 2),
        "customers": sorted({str(row.get("customer_id") or "") for row in rows if row.get("customer_id")}),
        "stores_count": len({str(row.get("store_id") or "") for row in rows if row.get("store_id")}),
        "payment_methods_count": len({str(row.get("payment_method_fingerprint") or "") for row in rows if row.get("payment_method_fingerprint")}),
        "devices_count": len({str(row.get("device_fingerprint") or "") for row in rows if row.get("device_fingerprint")}),
        "risk_score": round(float(risk), 3),
        "refs": refs,
    }


def dedupe_candidates(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    out = []
    seen: set[tuple[str, ...]] = set()
    for candidate in candidates:
        refs = tuple(candidate.get("refs") or [])
        if refs in seen:
            continue
        seen.add(refs)
        out.append(candidate)
        if len(out) >= max(1, min(limit, 20)):
            break
    return out


def protobuf_to_jsonable(value: Any) -> Any:
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    try:
        return MessageToDict(value, preserving_proto_field_name=True)
    except Exception:
        return str(value)


def client() -> HarnessServiceClientSync:
    return HarnessServiceClientSync(BITGN_URL)


def submit_run(run_id: str) -> None:
    client().submit_run(SubmitRunRequest(run_id=run_id, force=True))


def end_trial(trial_id: str) -> Any:
    return client().end_trial(EndTrialRequest(trial_id=trial_id))
