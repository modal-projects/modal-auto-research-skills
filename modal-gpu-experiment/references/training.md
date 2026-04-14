# Training with Modal

Run training jobs on Modal GPUs — from single-GPU fine-tuning to multi-node distributed training with RDMA.

## Writing a Training App

A Modal training app is a single Python file. Bake your code into the image, mount volumes for data and checkpoints, and run with `modal run`.

```python
import modal

app = modal.App("my-training")

# Persistent storage for data and checkpoints
data_volume = modal.Volume.from_name("training-data", create_if_missing=True)
ckpt_volume = modal.Volume.from_name("training-checkpoints", create_if_missing=True)

# Build the container image
image = (
    modal.Image.from_registry("nvidia/cuda:12.6.0-devel-ubuntu22.04", add_python="3.12")
    .pip_install("torch", "transformers", "datasets", "accelerate", "wandb")
    # Bake your training code into the image
    # IMPORTANT: use copy=True when add_local_file/add_local_dir is followed by run_commands
    .add_local_file("train.py", remote_path="/root/train.py", copy=True)
    .add_local_dir("src/", remote_path="/root/src", copy=True)
    .add_local_dir("configs/", remote_path="/root/configs", copy=True)
)

@app.function(
    image=image,
    gpu="H100",
    timeout=60 * 60 * 12,  # 12 hours
    volumes={"/data": data_volume, "/checkpoints": ckpt_volume},
    secrets=[modal.Secret.from_name("wandb-secret")],
    retries=modal.Retries(max_retries=3),
)
def train(config: str = "configs/default.yaml"):
    import subprocess
    subprocess.run(["python", "/root/train.py", "--config", config], check=True)

@app.local_entrypoint()
def main(config: str = "configs/default.yaml"):
    train.remote(config=config)
```

Save the above as a `.py` file (e.g., `my_train.py`) and run it:

```bash
modal run my_train.py
modal run my_train.py --config configs/large.yaml
```

Note: pass flags directly after the filename. The old `modal run app.py -- --flag` separator syntax no longer works.

### Key Patterns

- **`add_local_file` / `add_local_dir`**: Bake code into the image rather than shipping scripts as strings. **Use `copy=True`** if you chain `.run_commands()` after — without it, Modal errors because the file is mounted (not copied) and isn't available during the build step.
- **Volumes**: Mount persistent storage for data (`/data`) and checkpoints (`/checkpoints`). Data survives across runs.
- **Secrets**: Use `modal.Secret.from_name(...)` for W&B, HuggingFace tokens, etc. Create with `modal secret create`.
- **Retries**: `modal.Retries(max_retries=N)` for fault tolerance — combine with checkpoint auto-resume.
- **Timeout**: Set generous timeouts for long training runs.

### Auto-Resume from Checkpoints

Write your training script to detect existing checkpoints and resume:

```python
# In your training script
output_dir = "/checkpoints/my-experiment"
latest = find_latest_checkpoint(output_dir)
if latest:
    print(f"Resuming from {latest}")
    model.load_state_dict(torch.load(latest))
```

Combined with `retries`, this gives you fault-tolerant training — if a container is preempted, Modal retries and your script resumes from the last checkpoint.

## Multi-Node Distributed Training

For large models that don't fit on a single node, use `@modal.experimental.clustered` with RDMA for high-bandwidth inter-node communication.

```python
import modal
import modal.experimental

N_NODES = 2
GPUS_PER_NODE = 8

app = modal.App("distributed-training", image=image, volumes={...})

@app.function(
    gpu=f"H100:{GPUS_PER_NODE}",
    timeout=60 * 60 * 24,
    retries=modal.Retries(initial_delay=0.0, max_retries=10),
    experimental_options={"efa_enabled": True},  # Enable RDMA networking
)
@modal.experimental.clustered(size=N_NODES, rdma=True)
def train(config: str):
    from torchrun_util import torchrun

    cluster_info = modal.experimental.get_cluster_info()

    torchrun.run(
        node_rank=cluster_info.rank,
        master_addr=cluster_info.container_ips[0],
        master_port=1234,
        nnodes=str(N_NODES),
        nproc_per_node=str(GPUS_PER_NODE),
        training_script="/root/train.py",
        training_script_args=["--config", config],
    )
```

### How Clustered Training Works

- **Gang scheduling**: All `N_NODES` containers launch together or not at all.
- **RDMA**: `rdma=True` + `efa_enabled` gives up to 3,200 Gbps inter-node bandwidth via InfiniBand — essential for multi-node gradient sync.
- **Cluster info**: `modal.experimental.get_cluster_info()` returns:
  - `rank` — this container's index (0 = leader)
  - `container_ips` — all container IPs, sorted by rank
  - `cluster_id` — unique identifier for this cluster
- **Leader (rank 0)**: Coordinates the job. Only rank 0's return value is returned to the caller.

### NCCL Configuration

Set these environment variables in your training function for reliable multi-node NCCL:

```python
import os
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ["CUDA_DEVICE_MAX_CONNECTIONS"] = "1"
os.environ["NCCL_NVLS_ENABLE"] = "0"  # Disable NVLS — can hang on B200
os.environ["NCCL_DEBUG"] = "WARN"
```

### Fault Tolerance

- **Preemption**: If any container in the cluster is preempted, Modal terminates all containers and retries the entire input.
- **Retries + checkpoints**: Set `retries=modal.Retries(max_retries=10)` and write checkpoints to a volume. On retry, your script resumes from the last checkpoint.
- **Input failures**: If rank 0 fails, the input is marked failed. Other ranks failing independently doesn't propagate.

### Torchrun Integration

Use `torchrun` (or Accelerate) to manage distributed processes within each node. The `torchrun_util` pattern from Modal's examples wraps `torch.distributed.run` with the cluster info:

```python
# Each node runs torchrun with GPUS_PER_NODE processes
# torchrun handles local process spawning and NCCL init
# Modal handles inter-node networking and scheduling
```

## Data Loading

Use a separate Modal function to download/preprocess data to a volume:

```python
@app.function(
    timeout=60 * 60 * 4,
    volumes={"/data": data_volume},
)
def download_data(max_shards: int = None):
    from huggingface_hub import hf_hub_download
    # Download to /data/... — persists on the volume
    ...
    data_volume.commit()
```

```bash
# Download data (one-time) — the :: syntax calls a specific function
modal run my_train.py::download_data --max-shards 64

# Then train (data already on volume)
modal run my_train.py
```

## References

- Multi-node training docs: https://modal.com/docs/guide/multi-node-training
- Multi-node training examples: https://github.com/modal-labs/multinode-training-guide
- GPU options: see ./compute.md
