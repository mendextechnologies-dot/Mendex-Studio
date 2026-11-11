"""Codex v1.5 application API demo; no native solver or shell execution."""
import argparse
import json
from pathlib import Path
import sys

from .integration_contracts import JobRequest
from .paths import default_data_root
from .service import StudioService, StudioError


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mendex integration catalog and generic synthetic jobs")
    parser.add_argument("--root", type=Path, default=None)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("catalog")
    commands.add_parser("workspaces")
    create = commands.add_parser("new-workspace")
    create.add_argument("name", nargs="?", default="Generic integration workspace")
    demo = commands.add_parser("demo", help="Run a foreground synthetic software fixture; no engineering model")
    demo.add_argument("--workspace", required=True)
    demo.add_argument("--steps", type=int, default=10)
    demo.add_argument("--delay", type=float, default=.02)
    demo.add_argument("--timeout", type=float, default=30)
    demo.add_argument("--fail", action="store_true")
    commands.add_parser("jobs")
    for name in ("job", "report"):
        command = commands.add_parser(name)
        command.add_argument("job_id")
    commands.add_parser("datasets")
    args = parser.parse_args(argv)
    engine = None
    try:
        engine = StudioService(args.root or default_data_root()).integrations
        if args.command == "catalog":
            value = [{"descriptor": item.model_dump(mode="json"), "health": engine.detect(item.tool_id).model_dump(mode="json")} for item in engine.list_tools()]
        elif args.command == "workspaces":
            value = engine.list_workspaces()
        elif args.command == "new-workspace":
            value = engine.create_workspace(args.name)
        elif args.command == "demo":
            request = JobRequest(workspace_id=args.workspace, tool_id="studio-demo", operation="synthetic-echo", parameters={"steps": args.steps, "delay_s": args.delay, "fail": args.fail}, timeout_s=args.timeout, provenance="Foreground CLI SYNTHETIC SOFTWARE FIXTURE; engineering NOT_EVALUATED")
            job = engine.submit(request)
            value = engine.wait(job.request.job_id, timeout=args.timeout + 5).model_dump(mode="json")
        elif args.command == "jobs":
            value = [job.model_dump(mode="json") for job in engine.list_jobs()]
        elif args.command == "job":
            value = engine.job(args.job_id).model_dump(mode="json")
        elif args.command == "report":
            value = {"report_path": str(engine.export_report(args.job_id))}
        else:
            value = engine.list_datasets()
        print(json.dumps(value, indent=2))
        return 0
    except (ValueError, StudioError, OSError) as exc:
        print(json.dumps({"error": getattr(exc, "code", "INVALID_INPUT"), "message": str(exc)}), file=sys.stderr)
        return 1
    finally:
        if engine:
            engine.shutdown()


if __name__ == "__main__":
    sys.exit(main())
