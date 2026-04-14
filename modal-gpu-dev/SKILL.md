---
name: modal-gpu-dev
user-invocable: true
description: >
  Interactive GPU sandboxes on Modal with SSH access for debugging,
  profiling, and prototyping. Launch a container with any GPU (T4 to B200),
  SSH in, iterate on code with pre-installed ML tools. Use when you need
  hands-on GPU access for debugging, profiling with nsys/ncu, prototyping
  training scripts, or testing model serving.
---

# GPU Debugging

Interactive GPU containers on Modal with SSH access. Use for debugging, profiling, prototyping, or any work where you need hands-on access to a GPU environment. Containers come pre-installed with PyTorch, Transformers, SGLang, and common ML tools. Your workspace is persisted to a Modal Volume and synced every 30 seconds.

For general Modal platform usage (app structure, function types, CLI, deployment), see the `modal-basic-skills` skill.

## Quick Reference

### Launch a Sandbox

```bash
# Launch with specific GPU (runs in background)
_SANDBOX_GPU=H100 python -m modal run modal-gpu-dev/tools/gpu_sandbox.py \
  --key-path ~/.ssh/id_ed25519.pub --gpu H100 --sandbox-id my-sandbox > /tmp/sandbox.log 2>&1 &

# Wait for SSH info (written to volume — reliable, not buffered)
while true; do
  modal volume get gpu-sandbox-workspace /ssh-info/my-sandbox.json /tmp/ssh-info.json 2>/dev/null && break
  sleep 3
done
HOST=$(python3 -c "import json; d=json.load(open('/tmp/ssh-info.json')); print(d['host'])")
PORT=$(python3 -c "import json; d=json.load(open('/tmp/ssh-info.json')); print(d['port'])")

# SSH in (available immediately — sshd starts before volume sync)
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.ssh/id_ed25519 -p $PORT root@$HOST "nvidia-smi"
```

Sandboxes auto-terminate after 4 hours.

### SSH Commands

```bash
# Run a command
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -o LogLevel=ERROR -i ~/.ssh/id_ed25519 -p $PORT root@$HOST "nvidia-smi"

# Upload/download files
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.ssh/id_ed25519 -P $PORT ./local_file.py root@$HOST:/tmp/
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
  -i ~/.ssh/id_ed25519 -P $PORT root@$HOST:/tmp/results.json ./

# Rsync a directory
rsync -avz --exclude .git/ --exclude __pycache__/ --exclude .venv/ \
  -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/id_ed25519 -p $PORT" \
  ./my_code/ root@$HOST:/tmp/my_code/
```

### Workspace Persistence

The workspace at `/root/workspace` is backed by a Modal Volume (`gpu-sandbox-workspace`) and synced every 30 seconds. Data persists across sandbox restarts.

```bash
# List files on the volume
modal volume ls gpu-sandbox-workspace /workspace

# Download/upload via CLI
modal volume get gpu-sandbox-workspace /workspace/results.json ./results.json
modal volume put gpu-sandbox-workspace ./data.tar.gz /workspace/data.tar.gz
```

### Compute Options

Modal offers GPUs from T4 (16 GB) to B200 (192 GB), with up to 8 GPUs per container. H100 requests may be auto-upgraded to H200 at no extra cost.

See ./references/compute.md for the full GPU table, selection guide, and CUDA details.

### Development Workflow

1. Launch a sandbox with the GPU you need
2. Upload your code via scp/rsync
3. SSH in and iterate: run, debug, profile
4. Once the code works, write a proper Modal training app (see the `modal-gpu-experiment` skill)
5. Kill the sandbox

## References

- ./references/development.md — Full development workflow, environment details, use cases
- ./references/compute.md — GPU options and selection guide

## See Also

- For writing training apps: use the `modal-gpu-experiment` skill
- For running multiple sandboxes in parallel (multi-agent): use the `sub-agents` skill
