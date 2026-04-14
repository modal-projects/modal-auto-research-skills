"""Read sub-agent status, reports, and trajectory.

Called by the parent agent to check on a sub-agent's progress.

Usage:
    # Quick status check — is it running? any reports?
    python sub-agents/tools/agent_report.py agent-1

    # Read all structured reports from the agent
    python sub-agents/tools/agent_report.py agent-1 --reports

    # Dump full trajectory (everything the agent said/did)
    python sub-agents/tools/agent_report.py agent-1 --trajectory

    # Read just the final summary (written when agent completes)
    python sub-agents/tools/agent_report.py agent-1 --summary
"""

import argparse
import json
import os
import sys
from pathlib import Path


def get_agent_dir(agent_id: str) -> Path:
    return Path(".agents") / agent_id


def is_running(agent_dir: Path) -> bool:
    """Check if the agent process is still alive."""
    pid_file = agent_dir / "agent.pid"
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError):
        return False


def is_done(agent_dir: Path) -> bool:
    """Check if the agent has signaled completion."""
    return (agent_dir / "done.json").exists()


def read_reports(agent_dir: Path) -> list[dict]:
    """Read all structured reports, sorted by timestamp."""
    reports_dir = agent_dir / "reports"
    if not reports_dir.exists():
        return []
    reports = []
    for f in sorted(reports_dir.glob("*.json")):
        try:
            reports.append(json.loads(f.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return reports


def read_summary(agent_dir: Path) -> dict | None:
    """Read the final completion summary."""
    done_file = agent_dir / "done.json"
    if not done_file.exists():
        return None
    try:
        return json.loads(done_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def read_trajectory(agent_dir: Path, last_n: int = 50) -> list[str]:
    """Extract assistant text messages from the stream-json trajectory."""
    output_file = agent_dir / "output.jsonl"
    if not output_file.exists():
        return []

    lines = output_file.read_text().strip().split("\n")
    messages = []
    for line in lines[-last_n * 5 :]:  # read extra lines since not all are assistant text
        try:
            obj = json.loads(line)
            if obj.get("type") == "assistant":
                for block in obj.get("message", {}).get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        messages.append(block["text"])
        except (json.JSONDecodeError, KeyError):
            continue
    return messages[-last_n:]


def print_status(agent_id: str, agent_dir: Path) -> None:
    """Print a quick status overview."""
    running = is_running(agent_dir)
    done = is_done(agent_dir)
    reports = read_reports(agent_dir)

    if done:
        status = "COMPLETED"
    elif running:
        status = "RUNNING"
    else:
        status = "STOPPED (no done marker — may have crashed)"

    print(f"Agent: {agent_id}")
    print(f"Status: {status}")
    print(f"Reports: {len(reports)}")

    if reports:
        latest = reports[-1]
        print(f"Latest report: [{latest.get('timestamp', '?')}] {latest.get('title', '?')}")

    if done:
        summary = read_summary(agent_dir)
        if summary:
            print(f"\nFinal summary: {summary.get('summary', '?')}")


def main():
    parser = argparse.ArgumentParser(description="Read sub-agent status and reports")
    parser.add_argument("agent_id", help="Agent ID (e.g., agent-1)")
    parser.add_argument("--reports", action="store_true", help="Print all structured reports")
    parser.add_argument("--trajectory", action="store_true", help="Print full trajectory")
    parser.add_argument("--summary", action="store_true", help="Print final completion summary")
    parser.add_argument("--last", type=int, default=50, help="Number of trajectory messages (default: 50)")
    args = parser.parse_args()

    agent_dir = get_agent_dir(args.agent_id)
    if not agent_dir.exists():
        print(f"Error: agent directory not found: {agent_dir}", file=sys.stderr)
        sys.exit(1)

    if args.reports:
        reports = read_reports(agent_dir)
        if not reports:
            print("No reports yet.")
        for r in reports:
            print(f"\n--- [{r.get('timestamp', '?')}] {r.get('title', 'Untitled')} ---")
            print(r.get("body", ""))
            if r.get("data"):
                print(f"Data: {json.dumps(r['data'], indent=2)}")

    elif args.trajectory:
        messages = read_trajectory(agent_dir, last_n=args.last)
        if not messages:
            print("No trajectory yet.")
        for msg in messages:
            print(msg)
            print("---")

    elif args.summary:
        summary = read_summary(agent_dir)
        if not summary:
            print("Agent has not completed yet (no done.json).")
        else:
            print(f"Status: {summary.get('status', '?')}")
            print(f"Summary: {summary.get('summary', '?')}")
            if summary.get("findings"):
                print("\nFindings:")
                for f in summary["findings"]:
                    print(f"  - {f}")
            if summary.get("data"):
                print(f"\nData: {json.dumps(summary['data'], indent=2)}")

    else:
        print_status(args.agent_id, agent_dir)


if __name__ == "__main__":
    main()
