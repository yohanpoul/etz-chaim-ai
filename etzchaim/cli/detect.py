"""OS + Docker runtime + GPU profile detection for wizard auto-defaults."""
from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path


def detect_os() -> str:
    """Return 'macos', 'linux', 'windows', or 'unknown'."""
    s = platform.system()
    if s == "Darwin":
        return "macos"
    if s == "Linux":
        return "linux"
    if s == "Windows":
        return "windows"
    return "unknown"


def detect_docker_runtime() -> str | None:
    """Detect which Docker runtime is installed.

    Returns one of : 'orbstack', 'docker-desktop', 'colima', 'rancher', 'podman', 'docker', None.

    Resolves symlinks (e.g. /opt/homebrew/bin/docker → /Applications/OrbStack.app/...)
    *and* checks /Applications/ on macOS so we still recognize OrbStack /
    Docker Desktop when the docker binary is a Homebrew shim or absent.
    """
    docker = shutil.which("docker")
    candidates = []
    if docker:
        candidates.append(docker.lower())
        try:
            candidates.append(str(Path(docker).resolve()).lower())
        except OSError:
            pass
    # macOS Applications fallback : a runtime is "installed" if its app bundle
    # exists, even when the docker CLI is missing or shimmed.
    if platform.system() == "Darwin":
        if Path("/Applications/OrbStack.app").exists():
            candidates.append("/applications/orbstack.app")
        if Path("/Applications/Docker.app").exists():
            candidates.append("/applications/docker.app")
        if Path("/Applications/Rancher Desktop.app").exists():
            candidates.append("/applications/rancher desktop.app")

    blob = " ".join(candidates)
    if "orbstack" in blob:
        return "orbstack"
    if "docker.app" in blob or "docker desktop" in blob:
        return "docker-desktop"
    if "colima" in blob:
        return "colima"
    if "rancher" in blob:
        return "rancher"
    if not docker:
        if shutil.which("podman"):
            return "podman"
        return None
    return "docker"


def detect_compose_profile() -> str:
    """Auto-select docker-compose profile based on OS + hardware."""
    os_ = detect_os()
    if os_ == "macos":
        return "hybrid-host-ollama"
    if os_ == "linux":
        if shutil.which("nvidia-smi"):
            return "full-nvidia"
        if Path("/dev/kfd").exists():
            return "full-rocm"
        return "full-cpu"
    if os_ == "windows":
        proc_version = Path("/proc/version")
        if proc_version.exists() and "microsoft" in proc_version.read_text().lower():
            return "wsl2-cuda" if shutil.which("nvidia-smi") else "full-cpu"
        return "full-cpu"
    return "full-cpu"


def docker_is_running() -> bool:
    """Check `docker info` returns 0 (Docker daemon alive)."""
    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
