"""Report findings from a sub-agent back to the parent.

Called by sub-agents to write structured reports and signal completion.

Usage:
    # Report a finding (can be called multiple times during the agent's run)
    python sub-agents/tools/agent_summarize.py agent-1 report \
        --title "LR sweep results" \
        --body "Optimal LR is 0.01 with val_loss=0.42" \
        --data '{"best_lr": 0.01, "val_loss": 0.42}'

    # Signal completion with a final summary
    python sub-agents/tools/agent_summarize.py agent-1 done \
        --summary "Explored LR range 0.001-0.1, found 0.01 optimal" \
        --findings "LR=0.01 gives val_loss=0.42" "Batch size 256 is stable" \
        --data '{"best_config": {"lr": 0.01, "batch_size": 256}}'

    # Signal failure
    python sub-agents/tools/agent_summarize.py agent-1 done \
        --status failed \
        --summary "OOM on H100 with batch_size=512"
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_agent_dir(agent_id: str) -> Path:
    return Path(".agents") / agent_id


def write_report(agent_dir: Path, title: str, body: str, data: dict | None) -> str:
    """Write a structured report. Returns the report filename."""
    reports_dir = agent_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    # Count existing reports for ordering
    existing = len(list(reports_dir.glob("*.json")))
    filename = f"{existing:04d}-{timestamp}.json"

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "body": body,
    }
    if data:
        report["data"] = data

    report_path = reports_dir / filename
    report_path.write_text(json.dumps(report, indent=2))
    print(f"Report written: {report_path}")
    return filename


def write_done(agent_dir: Path, status: str, summary: str, findings: list[str], data: dict | None) -> None:
    """Signal completion with a final summary."""
    done = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "summary": summary,
    }
    if findings:
        done["findings"] = findings
    if data:
        done["data"] = data

    done_path = agent_dir / "done.json"
    done_path.write_text(json.dumps(done, indent=2))
    print(f"Completion signaled: {done_path}")


def main():
    parser = argparse.ArgumentParser(description="Sub-agent reporting")
    parser.add_argument("agent_id", help="Agent ID (e.g., agent-1)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Report subcommand
    report_parser = subparsers.add_parser("report", help="Write a finding report")
    report_parser.add_argument("--title", required=True, help="Short title for the report")
    report_parser.add_argument("--body", default="", help="Detailed description")
    report_parser.add_argument("--data", default=None, help="JSON string with structured data")

    # Done subcommand
    done_parser = subparsers.add_parser("done", help="Signal completion")
    done_parser.add_argument("--status", default="completed", choices=["completed", "failed"], help="Completion status")
    done_parser.add_argument("--summary", required=True, help="Final summary of what was accomplished")
    done_parser.add_argument("--findings", nargs="*", default=[], help="Key findings (one per arg)")
    done_parser.add_argument("--data", default=None, help="JSON string with structured data")

    args = parser.parse_args()

    agent_dir = get_agent_dir(args.agent_id)
    if not agent_dir.exists():
        agent_dir.mkdir(parents=True, exist_ok=True)

    data = None
    if args.data:
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError:
            print(f"Error: --data must be valid JSON", file=sys.stderr)
            sys.exit(1)

    if args.command == "report":
        write_report(agent_dir, args.title, args.body, data)
    elif args.command == "done":
        write_done(agent_dir, args.status, args.summary, args.findings, data)


if __name__ == "__main__":
    main()
