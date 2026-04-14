"""Modal GPU sandbox — single function, GPU set via env var.

The _SANDBOX_GPU env var must be set BEFORE this file is imported.

Usage (ephemeral — single agent):
    _SANDBOX_GPU=H100 python -m modal run modal-gpu-dev/tools/gpu_sandbox.py

Usage (deployed — multiple concurrent agents):
    modal deploy modal-gpu-dev/tools/gpu_sandbox.py
    # Then from Python:
    #   fn = modal.Function.from_name("gpu-sandbox", "sandbox")
    #   fn.spawn(ssh_public_key=pubkey)
"""

import json
import os
import pathlib
import subprocess
import threading
import time

import modal

APP_NAME = "gpu-sandbox"
CUDA_TAG = "12.6.0-devel-ubuntu22.04"
LOCAL_SSHD_CONFIG_PATH = pathlib.Path(__file__).resolve().parent / "sshd_config"
REMOTE_WORKSPACE_DIR = "/root/workspace"
VOLUME_ROOT = "/vol"
VOLUME_WORKSPACE_DIR = f"{VOLUME_ROOT}/workspace"
SSH_INFO_DIR = f"{VOLUME_ROOT}/ssh-info"
SYNC_INTERVAL_SECONDS = 30

# GPU spec — read at import time (before Modal registers the function)
GPU_SPEC = os.environ.get("_SANDBOX_GPU", "H100")
_GPU_PARAM = None if GPU_SPEC.lower() == "cpu" else GPU_SPEC

app = modal.App(APP_NAME)

workspace_volume = modal.Volume.from_name(
    "gpu-sandbox-workspace", create_if_missing=True
)

image = (
    modal.Image.from_registry(f"nvidia/cuda:{CUDA_TAG}", add_python="3.12")
    .apt_install(
        "openssh-server",
        "rsync",
        "git",
        "curl",
        "wget",
        "vim",
        "htop",
        "tmux",
        "jq",
    )
    .add_local_file(str(LOCAL_SSHD_CONFIG_PATH), "/etc/ssh/sshd_config", copy=True)
    .run_commands(
        "mkdir -p /root/workspace /var/run/sshd /root/.ssh",
        "chmod 700 /root/.ssh",
    )
    .pip_install(
        "sglang[all]",
        "torch",
        "transformers",
        "datasets",
        "numpy",
        "pandas",
        "nvitop",
    )
)


def _rsync(src: str, dst: str) -> None:
    subprocess.run(
        ["rsync", "-a", "--delete", "--exclude", ".git/",
         f"{src.rstrip('/')}/", f"{dst.rstrip('/')}/"],
        check=True,
    )


def _initial_sync() -> None:
    os.makedirs(VOLUME_WORKSPACE_DIR, exist_ok=True)
    os.makedirs(REMOTE_WORKSPACE_DIR, exist_ok=True)
    workspace_volume.reload()
    _rsync(VOLUME_WORKSPACE_DIR, REMOTE_WORKSPACE_DIR)


def _background_sync(stop: threading.Event) -> None:
    while not stop.is_set():
        _rsync(REMOTE_WORKSPACE_DIR, VOLUME_WORKSPACE_DIR)
        workspace_volume.commit()
        stop.wait(SYNC_INTERVAL_SECONDS)


def _write_authorized_key(pubkey: str) -> None:
    path = "/root/.ssh/authorized_keys"
    with open(path, "w") as f:
        f.write(f"{pubkey.strip()}\n")
    os.chmod(path, 0o600)


def _write_ssh_info_to_volume(sandbox_id: str, host: str, port: int) -> None:
    """Write SSH connection info to the volume so the local client can read it."""
    os.makedirs(SSH_INFO_DIR, exist_ok=True)
    info = {"host": host, "port": port, "sandbox_id": sandbox_id, "time": time.time()}
    info_path = os.path.join(SSH_INFO_DIR, f"{sandbox_id}.json")
    with open(info_path, "w") as f:
        json.dump(info, f)
    workspace_volume.commit()


def _setup_workspace(repo_url: str) -> str:
    """Clone repo into /tmp/<name> and return the path."""
    name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    target = f"/tmp/{name}"
    if os.path.exists(target) and os.path.isdir(os.path.join(target, ".git")):
        print(f"Repo already at {target}, pulling...")
        subprocess.run(["git", "-C", target, "pull"], check=False)
    else:
        print(f"Cloning {repo_url} into {target}...")
        subprocess.run(["git", "clone", repo_url, target], check=True)
    return target


@app.function(
    image=image,
    gpu=_GPU_PARAM,
    timeout=4 * 60 * 60,
    volumes={VOLUME_ROOT: workspace_volume},
)
def sandbox(ssh_public_key: str, sandbox_id: str = "default", repo_url: str = "", repo_name: str = "") -> None:
    _write_authorized_key(ssh_public_key)

    # Start sshd FIRST so SSH is available immediately (don't block on volume sync)
    sshd = subprocess.Popen(["/usr/sbin/sshd", "-D", "-e"])

    # Run initial volume sync in background — SSH works while this catches up
    init_thread = threading.Thread(target=_initial_sync, daemon=True)
    init_thread.start()

    stop = threading.Event()
    sync_thread = threading.Thread(target=_background_sync, args=(stop,), daemon=True)
    sync_thread.start()

    try:
        with modal.forward(22, unencrypted=True) as tunnel:
            host, port = tunnel.tcp_socket
            # Print for logs (best-effort)
            print(f"SANDBOX_SSH={host}:{port}")
            print(f"ssh root@{host} -p {port}")
            # Write to volume for reliable handshake with local client
            _write_ssh_info_to_volume(sandbox_id, host, port)
            sshd.wait()
    finally:
        stop.set()
        sync_thread.join(timeout=5)
        _rsync(REMOTE_WORKSPACE_DIR, VOLUME_WORKSPACE_DIR)
        workspace_volume.commit()
        # Clean up SSH info file
        info_path = os.path.join(SSH_INFO_DIR, f"{sandbox_id}.json")
        if os.path.exists(info_path):
            os.remove(info_path)
            workspace_volume.commit()
        if sshd.poll() is None:
            sshd.terminate()


@app.local_entrypoint()
def main(key_path: str = "", gpu: str = "H100", sandbox_id: str = "default", repo_url: str = "", repo_name: str = "") -> None:
    default_key = pathlib.Path.home() / ".ssh" / "id_ed25519.pub"
    path = pathlib.Path(key_path.strip() or str(default_key)).expanduser()
    if not path.exists():
        raise ValueError(f"SSH public key not found: {path}")
    pubkey = path.read_text().strip()
    sandbox.remote(ssh_public_key=pubkey, sandbox_id=sandbox_id, repo_url=repo_url, repo_name=repo_name)
