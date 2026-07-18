"""CLI for local agent development."""

from __future__ import annotations

import argparse
import json
import sys

from civilai_agent.models.context import WorkbenchContext
from civilai_agent.runner import run_agent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="civilai-agent")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run the Civil Analyst agent")
    run_parser.add_argument("--request", required=True, help="User request text")
    run_parser.add_argument("--entity-id", default=None)
    run_parser.add_argument("--section", default=None, dest="section_id")
    run_parser.add_argument("--project-id", default="local-dev")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--json", action="store_true", help="Emit AgentResponse JSON")

    eval_parser = sub.add_parser("eval-trace", help="Evaluate an AgentCore trace export")
    eval_parser.add_argument("trace_file", help="Path to trace.jsonl")
    eval_parser.add_argument("--max-web-searches", type=int, default=5)
    eval_parser.add_argument("--max-tool-calls", type=int, default=30)

    serve_parser = sub.add_parser(
        "serve", help="Run the dev-only HTTP wrapper (requires the 'serve' extra)"
    )
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8010)
    serve_parser.add_argument("--reload", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "run":
        context = WorkbenchContext(
            project_id=args.project_id,
            entity_id=args.entity_id,
            active_section_id=args.section_id,
            request=args.request,
        )
        response = run_agent(context, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(response.model_dump(), indent=2, default=str))
        else:
            print(response.message)
        return 0

    if args.command == "eval-trace":
        from pathlib import Path

        from civilai_agent.eval.trace_loader import evaluate_trace_file

        result = evaluate_trace_file(
            Path(args.trace_file),
            max_web_searches=args.max_web_searches,
            max_tool_calls=args.max_tool_calls,
        )
        print(json.dumps(result.model_dump(), indent=2))
        return 0 if result.passed else 2

    if args.command == "serve":
        import uvicorn

        uvicorn.run(
            "civilai_agent.server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
