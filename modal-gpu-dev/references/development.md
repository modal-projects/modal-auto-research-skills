# Development with Modal

Interactive GPU containers with SSH access for debugging, profiling, and iterating on code. Use when you need to explore a GPU environment hands-on before writing a training app.

## Launching a Sandbox

```bash
# Launch with specific GPU (runs in background)
SANDBOX_ID="dev-sandbox"
_SANDBOX_GPU=H100 python -m modal run modal-gpu-dev/tools/gpu_sandbox.py \
  --key-path ~/.ssh/id_ed25519.pub --gpu H100 --sandbox-id $SANDBOX_ID > /tmp/sandbox.log 2>&1 &
SANDBOX_PID=$!

# Wait for SSH info (written to volume — reliable, doesn't depend on log buffering)
while true; do
  modal volume get gpu-sandbox-workspace /ssh-info/$SANDBOX_ID.json /tmp/ssh-info.json 2>/dev/null && break
  sleep 3
done
HOST=$(python3 -c "import json; d=json.load(open('/tmp/ssh-info.json')); print(d['host'])")
PORT=$(python3 -c "import json; d=json.load(open('/tmp/ssh-info.json')); print(d['port'])")

# SSH is available immediately — sshd starts before volume sync completes
```

For multiple concurrent sandboxes, use `modal deploy` instead of `modal run` — see the `sub-agents` skill.

GPU options: `cpu`, `H100`, `H100:2`, `H100:4`, `H100:8`, `H200`, `H200:2`-`H200:8`, `B200`, `B200:2`-`B200:8`

## SSH Commands

```bash
# Run a command
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o LogLevel=ERROR -i ~/.ssh/id_ed25519 -p $PORT root@$HOST "nvidia-smi"

# Upload a file
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.ssh/id_ed25519 -P $PORT ./local_file.py root@$HOST:/tmp/

# Download a file
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.ssh/id_ed25519 -P $PORT root@$HOST:/tmp/results.json ./

# Rsync a directory
rsync -avz --exclude .git/ --exclude __pycache__/ --exclude .venv/ \
  -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/id_ed25519 -p $PORT" \
  ./my_code/ root@$HOST:/tmp/my_code/
```

## Environment

- **OS**: Ubuntu 22.04, CUDA 12.6, Python 3.12, root access
- **Pre-installed**: SGLang, PyTorch, Transformers, datasets, numpy, pandas, nvitop
- **Profiling tools**: nvidia-smi, nsys, ncu
- **Dev tools**: git, pip, tmux, vim, htop, jq
- **Persistent workspace**: `/root/workspace` (Modal Volume `gpu-sandbox-workspace`, synced every 30s)
- **Auto-terminates**: after 4 hours

## Use Cases

- **Debugging**: SSH in, reproduce an issue, inspect state interactively
- **Profiling**: Run `nsys profile python train.py` and download the trace
- **Prototyping**: Iterate on code before committing to a training app
- **Model serving**: Spin up a model and test inference interactively
- **Environment exploration**: Check GPU specs, test library compatibility

## Long-Running Commands

Always background long commands to avoid SSH timeouts:

```bash
ssh ... root@$HOST "nohup python train.py > /tmp/train.log 2>&1 & echo PID=\$!"
# Check later
ssh ... root@$HOST "tail -20 /tmp/train.log"
```

## Workspace Persistence

The workspace at `/root/workspace` is backed by the Modal Volume `gpu-sandbox-workspace` and synced every 30 seconds. Download data once, reuse across all future sandboxes:

```bash
# First run: download and cache
ssh ... root@$HOST "wget -O /root/workspace/data.tar.gz https://example.com/data.tar.gz"

# Future runs on any sandbox: data is already there
ssh ... root@$HOST "ls /root/workspace/data/"
```

```bash
# CLI commands for the volume
modal volume ls gpu-sandbox-workspace /workspace
modal volume get gpu-sandbox-workspace /workspace/results.json ./results.json
modal volume put gpu-sandbox-workspace ./data.tar.gz /workspace/data.tar.gz
```

## Development Workflow

1. Launch a sandbox with the GPU you need
2. Upload your code via scp/rsync
3. SSH in and iterate: run, debug, profile
4. Once the code works, write a proper Modal training app (see the `modal-gpu-experiment` skill)
5. Kill the sandbox

This is the Modal equivalent of SSHing into a cloud VM — except it starts in seconds and has your entire ML stack pre-installed.

## Cleanup

```bash
# Kill the sandbox (kills the modal run process)
kill $SANDBOX_PID
```
