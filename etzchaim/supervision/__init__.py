"""Read-only macOS supervision helpers for bounded loop runs."""

from __future__ import annotations

from etzchaim.supervision.launchagent import (
    LABEL,
    PROGRAM_ARGUMENTS,
    default_launchagent_path,
    install_dry_run_payload,
    launchagent_payload,
    preflight_payload,
    refused_install_payload,
    render_launchagent_plist,
)

__all__ = [
    "LABEL",
    "PROGRAM_ARGUMENTS",
    "default_launchagent_path",
    "install_dry_run_payload",
    "launchagent_payload",
    "preflight_payload",
    "refused_install_payload",
    "render_launchagent_plist",
]
