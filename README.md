# modal-auto-research-skills

Give your research agents elastic GPUs. These skills teach agents how to use [Modal](https://modal.com) to provision and release GPUs on demand, from spinning up dozens of cheap single-GPU runs for exploration, to scaling to parallel multi-node GPU clusters for training. No cluster management, no idle bills, no wasted compute.

We used these skills to run [OpenAI's Parameter Golf challenge](https://openai.com/index/parameter-golf/) overnight: 113 experiments across 238 GPU-hours, finishing 5x faster than a single workstation while using a fraction of the resources of a dedicated cluster. Read the full writeup on the [Modal blog](https://modal.com/blog).

## Skills

| Skill | Description |
|-------|-------------|
| `modal-basic-skills` | Foundational Modal platform knowledge — app structure, function types, CLI, deployment. Auto-triggers when code imports `modal`. |
| `modal-gpu-dev` | Interactive GPU sandboxes with SSH. Launch any GPU (T4 to B200), SSH in, debug and profile with pre-installed ML tools. |
| `modal-gpu-experiment` | Training apps with volumes, secrets, retries, and checkpoint auto-resume. Single-GPU to multi-node. |
| `sub-agents` | Parallel agent orchestration. Spawn multiple Claude Code agents, each with its own GPU, with structured reporting. |

## Installation

Copy the skill folders into your project's `.claude/skills/` directory:

```bash
git clone https://github.com/modal-projects/modal-auto-research-skills.git
cp -R modal-auto-research-skills/{modal-basic-skills,modal-gpu-dev,modal-gpu-experiment,sub-agents} \
  /path/to/your/project/.claude/skills/
```

## Usage

Once installed, the agent will automatically pick the right skill based on context. To guide it, add something like this to your project's `AGENT.md`:

```
Use Modal skills for all GPU work:
- modal-basic-skills: foundational Modal platform knowledge
- modal-gpu-dev: launch interactive GPU sandboxes for debugging and prototyping
- modal-gpu-experiment: write and run training apps for experiments
- sub-agents: orchestrate parallel agents across multiple GPUs
```
