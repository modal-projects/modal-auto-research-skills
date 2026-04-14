# Compute Options

## All Available GPUs

| GPU | VRAM | Max per container | Notes |
|-----|------|-------------------|-------|
| `T4` | 16 GB | 8 | Budget inference, light workloads |
| `L4` | 24 GB | 8 | Cost-effective inference |
| `A10` | 24 GB | 4 | General purpose |
| `L40S` | 48 GB | 8 | Mid-range, good for medium models |
| `RTX-PRO-6000` | — | — | Professional workstation GPU |
| `A100-40GB` | 40 GB | 8 | Training and inference |
| `A100-80GB` | 80 GB | 8 | High-memory training |
| `H100` | 80 GB | 8 | Hopper architecture, SXM variant. All H100s on Modal are SXM |
| `H200` | 141 GB | 8 | HBM3e memory, 4.8 TB/s bandwidth. 1.75x capacity and 1.4x faster than H100 |
| `B200` | 192 GB | 8 | Blackwell architecture, latest gen |
| `B200+` | 192+ GB | 8 | Runs on B200 or B300. Billed as B200 regardless. B300 requires CUDA 13.0+ |

Multi-GPU: append `:N` to the GPU type (e.g., `gpu="H100:8"`). All GPUs are on the same physical machine. Requesting more than 2 GPUs per container may result in longer wait times.

## Automatic Upgrades

- `gpu="H100"` may be automatically upgraded to H200 at no extra cost. Use `gpu="H100!"` to prevent this.
- `gpu="A100"` may be automatically upgraded to A100-80GB at no extra cost.
- `gpu="B200+"` allows Modal to run on B200 or B300, billed as B200.

## GPU Fallbacks

You can specify multiple GPU types as fallback options for cross-compatible functions. Modal respects the preference ordering during allocation.

## Choosing a GPU

- **Inference (< 70B params)**: `H100` or `H200`
- **Inference (70B+)**: `H100:2` or `H200` (141 GB fits most 70B models)
- **Training (small models < 1B)**: `H100`
- **Training (1B-7B)**: `H100:4` or `H200:2`
- **Training (7B+)**: `H100:8` or `H200:4`+
- **Maximum single-GPU memory**: `B200` (192 GB)
- **Data prep / non-GPU**: no `gpu` parameter (CPU only)

## Multi-Node Training

For workloads that need more than 8 GPUs, use multi-node with `@modal.experimental.clustered`. This gang-schedules multiple containers and connects them via RDMA (up to 3,200 Gbps). See ./training.md for details.

Example: 2 nodes x 8 H100s = 16 GPUs, 1,280 GB total VRAM.

## Specifying GPUs in Code

```python
# In a Modal app
@app.function(gpu="H100")
def train(): ...

@app.function(gpu="H100:8")
def distributed_train(): ...

@app.function(gpu="B200+")  # B200 or B300
def flexible_train(): ...

# Prevent automatic upgrade
@app.function(gpu="H100!")
def exact_h100(): ...
```

## CUDA

Modal pre-installs NVIDIA Driver 580.95.05 and CUDA Driver API 13.0. CUDA 12.x and 13.x are guaranteed compatible. For ML libraries like PyTorch, Transformers, vLLM — just `pip_install` them, they bundle their own CUDA runtime. For full CUDA toolkit, use `nvidia/cuda:*-devel-*` base images.

## References

- GPU docs: https://modal.com/docs/guide/gpu
- Multi-GPU training: https://modal.com/docs/guide/gpu#multi-gpu-training
- Multi-node training: https://modal.com/docs/guide/multi-node-training
- CUDA on Modal: https://modal.com/docs/guide/cuda
- GPU metrics: https://modal.com/docs/guide/gpu-metrics
- Pricing: https://modal.com/pricing
