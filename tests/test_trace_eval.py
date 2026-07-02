"""Tests for trace eval harness."""

from pathlib import Path

from civilai_agent.eval.trace_loader import evaluate_trace_file, load_trace_jsonl, summarize_trace


def test_trace_eval_passes_within_budget(tmp_path: Path) -> None:
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        "\n".join(
            [
                '{"event":"tool","tool":"get_section_facts","latency_ms":120}',
                '{"event":"tool","tool":"web_search_deduped","query":"zoning","latency_ms":400}',
                '{"event":"tool","tool":"web_search_deduped","query":"zoning","dedupe_hit":true}',
            ]
        ),
        encoding="utf-8",
    )
    records = load_trace_jsonl(trace_path)
    export = summarize_trace("run-1", records)
    assert export.tool_call_count == 3
    assert export.web_search_count == 2
    assert export.dedupe_hit_count == 1
    result = evaluate_trace_file(trace_path)
    assert result.passed is True


def test_trace_eval_fails_on_excess_searches(tmp_path: Path) -> None:
    lines = [
        f'{{"event":"tool","tool":"web_search_deduped","query":"q{i}"}}' for i in range(6)
    ]
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text("\n".join(lines), encoding="utf-8")
    result = evaluate_trace_file(trace_path, max_web_searches=5)
    assert result.passed is False
    assert result.violations
