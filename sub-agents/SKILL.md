---
name: sub-agents
user-invocable: true
description: >
  Parallel Claude Code agent orchestration. Spawn multiple autonomous
  agents, each with its own GPU or compute, to divide work in parallel.
  Each agent works independently and reports findings via structured reports;
  the parent monitors progress and steers agents. Use when you need to run
  multiple debugging sessions, experiments, or research tasks in parallel
  across separate GPUs.
---

# Sub-Agents

Spawn parallel Claude Code processes, each with its own compute, to divide work across multiple GPUs. Each agent works autonomously and reports findings back to the parent via structured reports. This is a general orchestration pattern — use it for parallel debugging, parallel experiments, or any work that benefits from multiple agents.

**IMPORTANT:** Deploy the sandbox/experiment app ONCE, then spawn agents against it. Do NOT use `modal run` per agent — concurrent `modal run` processes conflict and kill each other.

## Quick Reference

### Deploy Once, Call Many

```bash
# Deploy ONCE (shared by all agents)
modal deploy modal-gpu-dev/tools/gpu_sandbox.py

# Each agent gets a sandbox via the deployed function
python -c "
import modal, pathlib
fn = modal.Function.from_name('gpu-sandbox', 'sandbox')
pubkey = pathlib.Path('~/.ssh/id_ed25519.pub').expanduser().read_text().strip()
fn.spawn(ssh_public_key=pubkey, sandbox_id='agent-1')
"
```

### Option A: SSH Sandbox Agents (interactive debugging)

Each agent gets its own GPU sandbox via the `modal-gpu-dev` skill's sandbox tool, SSHes in, and works interactively.

```bash
AGENT_ID="agent-1"
mkdir -p .agents/$AGENT_ID

# Launch sandbox via deployed function
python -c "
import modal, pathlib
fn = modal.Function.from_name('gpu-sandbox', 'sandbox')
pubkey = pathlib.Path('~/.ssh/id_ed25519.pub').expanduser().read_text().strip()
fn.spawn(ssh_public_key=pubkey, sandbox_id='$AGENT_ID')
" &
echo $! > .agents/$AGENT_ID/sandbox.pid

# Wait for SSH info
while true; do
  modal volume get gpu-sandbox-workspace /ssh-info/$AGENT_ID.json /tmp/$AGENT_ID-ssh.json 2>/dev/null && break
  sleep 3
done
HOST=$(python3 -c "import json; d=json.load(open('/tmp/$AGENT_ID-ssh.json')); print(d['host'])")
PORT=$(python3 -c "import json; d=json.load(open('/tmp/$AGENT_ID-ssh.json')); print(d['port'])")

# Launch the agent
claude -p "YOUR TASK DESCRIPTION.

SSH into $HOST port $PORT with:
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/id_ed25519 -p $PORT root@$HOST

IMPORTANT: Report findings periodically using:
python sub-agents/tools/agent_summarize.py $AGENT_ID report --title 'TITLE' --body 'DETAILS'

When done, signal completion:
python sub-agents/tools/agent_summarize.py $AGENT_ID done --summary 'WHAT YOU DID' --findings 'FINDING 1' 'FINDING 2'" \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --model sonnet \
  > .agents/$AGENT_ID/output.jsonl 2>.agents/$AGENT_ID/stderr.log &
echo $! > .agents/$AGENT_ID/agent.pid
```

### Option B: Batch Experiment Agents (no SSH)

For workloads where each agent submits experiments and reads results — deploy your experiment function once and call it directly:

```bash
# Deploy your experiment runner ONCE
modal deploy my_experiment.py

# Each agent calls the deployed function — no sandbox needed
claude -p "Run experiments by calling:
  import modal
  fn = modal.Function.from_name('my-experiment-app', 'run_experiment')
  result = fn.remote(config=...)

Report findings with sub-agents/tools/agent_summarize.py." \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --model sonnet \
  > .agents/$AGENT_ID/output.jsonl 2>.agents/$AGENT_ID/stderr.log &
```

### Reporting (Sub-Agent Side)

```bash
# Report a finding (call multiple times during the run)
python sub-agents/tools/agent_summarize.py agent-1 report \
  --title "LR sweep results" \
  --body "Optimal LR is 0.01 with val_loss=0.42" \
  --data '{"best_lr": 0.01, "val_loss": 0.42}'

# Signal completion
python sub-agents/tools/agent_summarize.py agent-1 done \
  --summary "Explored LR range 0.001-0.1, found 0.01 optimal" \
  --findings "LR=0.01 gives best val_loss=0.42" "Batch size 256 is stable"
```

### Monitoring (Parent Side)

```bash
# Quick status check
python sub-agents/tools/agent_report.py agent-1

# Read structured reports
python sub-agents/tools/agent_report.py agent-1 --reports

# Read full trajectory
python sub-agents/tools/agent_report.py agent-1 --trajectory

# Read final summary
python sub-agents/tools/agent_report.py agent-1 --summary
```

## Tools

- ./tools/agent_report.py — Read agent status, reports, and trajectory
- ./tools/agent_summarize.py — Write reports and signal completion

## References

- ./references/sub-agents.md — Full orchestration guide (file structure, parallel patterns, follow-ups, cleanup)

## See Also

- For the GPU sandbox primitive: use the `modal-gpu-dev` skill
- For training/experiment apps to deploy: use the `modal-gpu-experiment` skill
