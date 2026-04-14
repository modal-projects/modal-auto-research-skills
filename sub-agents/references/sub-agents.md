# Sub-Agents

Spawn parallel Claude Code processes, each with its own compute, to divide work across multiple GPUs. Each agent works autonomously and reports findings back to the parent via structured reports.

## Architecture

```
Parent Agent
  ├── modal deploy modal-gpu-dev/tools/gpu_sandbox.py    (ONE-TIME — shared by all agents)
  ├── spawns agent-1 (H100, task: architecture search)
  ├── spawns agent-2 (H100, task: LR optimization)
  └── spawns agent-3 (H100, task: training dynamics)

Each sub-agent:
  1. Gets its own GPU sandbox (via deployed function, not modal run)
  2. Works autonomously
  3. Reports findings via agent_summarize.py
  4. Signals completion with done marker

Parent agent:
  1. Polls agent_report.py to check progress
  2. Reads structured reports and summaries
  3. Can send follow-up messages to steer agents
```

## IMPORTANT: Deploy Once, Call Many

**Do NOT use `modal run` per agent.** Multiple `modal run` processes for the same app cause `APP_STATE_STOPPED` errors — when one finishes, it tears down the ephemeral app and kills all others.

Instead, deploy once and have each agent call the deployed function:

```bash
# Deploy the sandbox app ONCE (idempotent, safe to re-run)
modal deploy modal-gpu-dev/tools/gpu_sandbox.py
```

Then from each agent's Python code (or a thin launcher script):

```python
import modal

fn = modal.Function.from_name("gpu-sandbox", "sandbox")
fn.spawn(ssh_public_key=pubkey, sandbox_id="agent-1")
```

For batch experiment workloads (no SSH needed), the same pattern applies — deploy once, call `.remote()` or `.spawn()` concurrently:

```python
# Deploy your experiment app once
# modal deploy my_experiment.py

fn = modal.Function.from_name("my-experiment-app", "run_experiment")
result = fn.remote(train_py_content=code, config=config)
```

## File Structure

Each agent gets a directory under `.agents/`:

```
.agents/
└── agent-1/
    ├── agent.pid          # Agent process ID
    ├── sandbox.pid        # Sandbox process ID (if using SSH sandbox)
    ├── output.jsonl       # Full trajectory (stream-json from Claude CLI)
    ├── stderr.log         # Agent stderr
    ├── reports/           # Structured reports (written by sub-agent)
    │   ├── 0000-20260330-141500.json
    │   ├── 0001-20260330-143000.json
    │   └── ...
    └── done.json          # Completion marker with final summary
```

## Spawning an Agent

### Option A: SSH sandbox per agent (interactive development/debugging)

```bash
# 0. Deploy sandbox app ONCE (skip if already deployed)
modal deploy modal-gpu-dev/tools/gpu_sandbox.py

# 1. Create agent directory
AGENT_ID="agent-1"
mkdir -p .agents/$AGENT_ID

# 2. Launch a sandbox for the agent via the DEPLOYED function
python -c "
import modal, pathlib
fn = modal.Function.from_name('gpu-sandbox', 'sandbox')
pubkey = pathlib.Path('~/.ssh/id_ed25519.pub').expanduser().read_text().strip()
fn.spawn(ssh_public_key=pubkey, sandbox_id='$AGENT_ID')
" &
echo $! > .agents/$AGENT_ID/sandbox.pid

# 3. Wait for sandbox SSH info (written to volume by the sandbox)
echo "Waiting for sandbox SSH info..."
while true; do
  modal volume get gpu-sandbox-workspace /ssh-info/$AGENT_ID.json /tmp/$AGENT_ID-ssh.json 2>/dev/null && break
  sleep 3
done

# 4. Parse SSH info
HOST=$(python3 -c "import json; d=json.load(open('/tmp/$AGENT_ID-ssh.json')); print(d['host'])")
PORT=$(python3 -c "import json; d=json.load(open('/tmp/$AGENT_ID-ssh.json')); print(d['port'])")

# 5. Launch the Claude agent process
claude -p "YOUR TASK DESCRIPTION.

SSH into $HOST port $PORT with:
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/id_ed25519 -p $PORT root@$HOST

IMPORTANT: Report your findings periodically using:
python sub-agents/tools/agent_summarize.py $AGENT_ID report --title 'TITLE' --body 'DETAILS' --data '{\"key\": \"value\"}'

When you are done, signal completion:
python sub-agents/tools/agent_summarize.py $AGENT_ID done --summary 'WHAT YOU DID' --findings 'FINDING 1' 'FINDING 2'" \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --model sonnet \
  > .agents/$AGENT_ID/output.jsonl 2>.agents/$AGENT_ID/stderr.log &
echo $! > .agents/$AGENT_ID/agent.pid
```

### Option B: Batch experiments (no SSH, recommended for parallel search)

For workloads where each agent submits experiments and reads results (no interactive SSH needed), deploy your experiment function once and call it directly:

```bash
# Deploy your experiment runner ONCE
modal deploy my_experiment.py

# Each agent calls the deployed function from Python — no sandbox needed
claude -p "Run hyperparameter experiments by calling:
  import modal
  fn = modal.Function.from_name('my-experiment-app', 'run_experiment')
  result = fn.remote(config=...)

Report findings with sub-agents/tools/agent_summarize.py." \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --model sonnet \
  > .agents/$AGENT_ID/output.jsonl 2>.agents/$AGENT_ID/stderr.log &
```

This is simpler and more robust than SSH sandboxes for batch workloads.

## Reporting Findings (Sub-Agent Side)

Sub-agents call `agent_summarize.py` to send structured reports back to the parent.

### Report a finding (call multiple times during the run)

```bash
python sub-agents/tools/agent_summarize.py agent-1 report \
  --title "LR sweep results" \
  --body "Tested LR range 0.001-0.1. Optimal LR is 0.01 with val_loss=0.42." \
  --data '{"best_lr": 0.01, "val_loss": 0.42, "all_results": [{"lr": 0.001, "val_loss": 0.58}, {"lr": 0.01, "val_loss": 0.42}, {"lr": 0.1, "val_loss": 0.91}]}'
```

### Signal completion

```bash
# Success
python sub-agents/tools/agent_summarize.py agent-1 done \
  --summary "Explored LR range 0.001-0.1, found 0.01 optimal with val_loss=0.42" \
  --findings "LR=0.01 gives best val_loss=0.42" "Batch size 256 is stable" "LR>0.05 diverges" \
  --data '{"best_config": {"lr": 0.01, "batch_size": 256, "val_loss": 0.42}}'

# Failure
python sub-agents/tools/agent_summarize.py agent-1 done \
  --status failed \
  --summary "OOM on H100 with batch_size=512, need H100:2 or reduce batch size"
```

### Report format

Reports are stored as JSON in `.agents/<id>/reports/`:

```json
{
  "timestamp": "2026-03-30T14:15:00+00:00",
  "title": "LR sweep results",
  "body": "Tested LR range 0.001-0.1. Optimal LR is 0.01 with val_loss=0.42.",
  "data": {"best_lr": 0.01, "val_loss": 0.42}
}
```

The done marker (`.agents/<id>/done.json`):

```json
{
  "timestamp": "2026-03-30T15:30:00+00:00",
  "status": "completed",
  "summary": "Explored LR range 0.001-0.1, found 0.01 optimal",
  "findings": ["LR=0.01 gives best val_loss=0.42", "Batch size 256 is stable"],
  "data": {"best_config": {"lr": 0.01, "batch_size": 256}}
}
```

## Reading Agent Status (Parent Side)

The parent calls `agent_report.py` to check on sub-agents.

### Quick status check

```bash
python sub-agents/tools/agent_report.py agent-1
# Output:
# Agent: agent-1
# Status: RUNNING
# Reports: 3
# Latest report: [2026-03-30T14:15:00+00:00] LR sweep results
```

### Read all structured reports

```bash
python sub-agents/tools/agent_report.py agent-1 --reports
```

### Read full trajectory (everything the agent said/did)

```bash
python sub-agents/tools/agent_report.py agent-1 --trajectory
python sub-agents/tools/agent_report.py agent-1 --trajectory --last 100  # last 100 messages
```

### Read final summary (after agent completes)

```bash
python sub-agents/tools/agent_report.py agent-1 --summary
# Output:
# Status: completed
# Summary: Explored LR range 0.001-0.1, found 0.01 optimal
# Findings:
#   - LR=0.01 gives best val_loss=0.42
#   - Batch size 256 is stable
```

## Completion Detection

The parent can detect whether an agent is done in two ways:

1. **Done marker**: Check if `.agents/<id>/done.json` exists (agent explicitly signaled completion)
2. **Process check**: Check if the agent PID is still alive (process exited)

```bash
# Check via agent_report.py (combines both checks)
python sub-agents/tools/agent_report.py agent-1
# Status will be one of: RUNNING, COMPLETED, STOPPED (crashed without done marker)
```

A well-behaved agent always writes `done.json` before exiting. If the agent process dies without a done marker, the status shows `STOPPED` — the parent should investigate via `--trajectory`.

## Sending Follow-Up Messages

```bash
# Resume a finished agent's session with new instructions
claude -p "Now try with learning rate 0.01 and report results" \
  --resume SESSION_ID \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --model sonnet \
  >> .agents/$AGENT_ID/output.jsonl 2>>.agents/$AGENT_ID/stderr.log
```

## Sharing Data Between Agents

All sandboxes launched via the `modal-gpu-dev` skill share the same volume (`gpu-sandbox-workspace`). Agents can coordinate by writing results for others to read:

```bash
# Agent 1 writes results
ssh ... root@$HOST1 "echo '{\"best_lr\": 0.01}' > /root/workspace/agent1-results.json"

# Agent 2 reads them (after volume sync, ~30s)
ssh ... root@$HOST2 "cat /root/workspace/agent1-results.json"
```

## Parallel Research Pattern

```bash
# 0. Deploy sandbox app ONCE
modal deploy modal-gpu-dev/tools/gpu_sandbox.py

# Spawn 3 agents on 3 GPUs with different tasks
for i in 1 2 3; do
  mkdir -p .agents/agent-$i

  # Launch sandbox via deployed function (NOT modal run)
  python -c "
import modal, pathlib
fn = modal.Function.from_name('gpu-sandbox', 'sandbox')
pubkey = pathlib.Path('~/.ssh/id_ed25519.pub').expanduser().read_text().strip()
fn.spawn(ssh_public_key=pubkey, sandbox_id='agent-$i')
" &
  echo $! > .agents/agent-$i/sandbox.pid
done

# Wait for all sandboxes, then parse SSH info and launch agents
for i in 1 2 3; do
  while true; do
    modal volume get gpu-sandbox-workspace /ssh-info/agent-$i.json /tmp/agent-$i-ssh.json 2>/dev/null && break
    sleep 3
  done
  # Parse and launch claude -p for each (same as single-agent pattern above)
done

# Poll for completion
while true; do
  ALL_DONE=true
  for i in 1 2 3; do
    python sub-agents/tools/agent_report.py agent-$i
    if [ ! -f .agents/agent-$i/done.json ]; then
      ALL_DONE=false
    fi
  done
  if [ "$ALL_DONE" = true ]; then break; fi
  sleep 60
done

# Read all summaries
for i in 1 2 3; do
  echo "=== Agent $i ==="
  python sub-agents/tools/agent_report.py agent-$i --summary
done
```

## Cleanup

```bash
# Kill a specific agent and its sandbox
kill $(cat .agents/$AGENT_ID/agent.pid) 2>/dev/null
kill $(cat .agents/$AGENT_ID/sandbox.pid) 2>/dev/null

# Clean up all agents
for dir in .agents/*/; do
  AGENT_ID=$(basename "$dir")
  kill $(cat .agents/$AGENT_ID/agent.pid) 2>/dev/null
  kill $(cat .agents/$AGENT_ID/sandbox.pid) 2>/dev/null
done

# Stop the deployed sandbox app (only when completely done)
modal app stop gpu-sandbox
```
