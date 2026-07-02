"""Eval harness — consume AgentCore / platform trace exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TraceRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    event: str = ""
    tool: str | None = None
    query: str | None = None
    dedupe_hit: bool = False
    latency_ms: int | None = None
    tokens: dict[str, int] | None = None


class RunTraceExport(BaseModel):
    """Normalized trace export from platform S3 agent-runs/{runId}/trace.jsonl."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    records: tuple[TraceRecord, ...] = ()
    tool_call_count: int = 0
    web_search_count: int = 0
    dedupe_hit_count: int = 0
    total_latency_ms: int | None = None


class TraceEvalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    passed: bool
    violations: tuple[str, ...] = Field(default_factory=tuple)


def load_trace_jsonl(path: Path) -> tuple[TraceRecord, ...]:
    records: list[TraceRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        payload: dict[str, Any] = json.loads(line)
        records.append(TraceRecord.model_validate(payload))
    return tuple(records)


def summarize_trace(run_id: str, records: tuple[TraceRecord, ...]) -> RunTraceExport:
    tool_calls = [r for r in records if r.tool]
    web_searches = [r for r in tool_calls if r.tool == "web_search_deduped"]
    dedupe_hits = [r for r in web_searches if r.dedupe_hit]
    latencies = [r.latency_ms for r in records if r.latency_ms is not None]
    total_latency = sum(latencies) if latencies else None
    return RunTraceExport(
        run_id=run_id,
        records=records,
        tool_call_count=len(tool_calls),
        web_search_count=len(web_searches),
        dedupe_hit_count=len(dedupe_hits),
        total_latency_ms=total_latency,
    )


def evaluate_trace(
    export: RunTraceExport,
    *,
    max_web_searches: int = 5,
    max_tool_calls: int = 30,
) -> TraceEvalResult:
    violations: list[str] = []
    if export.web_search_count > max_web_searches:
        violations.append(
            f"web_search_count {export.web_search_count} exceeds max {max_web_searches}"
        )
    if export.tool_call_count > max_tool_calls:
        violations.append(
            f"tool_call_count {export.tool_call_count} exceeds max {max_tool_calls}"
        )
    return TraceEvalResult(
        run_id=export.run_id,
        passed=not violations,
        violations=tuple(violations),
    )


def evaluate_trace_file(
    path: Path,
    *,
    max_web_searches: int = 5,
    max_tool_calls: int = 30,
) -> TraceEvalResult:
    run_id = path.parent.name if path.name == "trace.jsonl" else path.stem
    records = load_trace_jsonl(path)
    export = summarize_trace(run_id, records)
    return evaluate_trace(export, max_web_searches=max_web_searches, max_tool_calls=max_tool_calls)
