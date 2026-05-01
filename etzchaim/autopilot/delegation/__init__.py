"""Delegation — isolated workers and worker spawning."""

from __future__ import annotations

from etzchaim.autopilot.delegation.subagent import IsolatedWorker, WorkerResult
from etzchaim.autopilot.delegation.worker import WorkerSpawner

__all__ = ["IsolatedWorker", "WorkerResult", "WorkerSpawner"]
