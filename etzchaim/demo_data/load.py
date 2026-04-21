"""Load demo seed.sql into the running postgres container."""
from __future__ import annotations

import subprocess
from importlib import resources

from etzchaim.cli.compose import compose_dir


def load_seed() -> int:
    """Run the seed SQL against the compose postgres service.

    Returns the exit code of `docker compose exec -T postgres psql`.
    """
    with resources.as_file(resources.files("etzchaim.demo_data") / "seed.sql") as sql_path:
        cmd = [
            "docker", "compose",
            "exec", "-T", "postgres",
            "psql", "-U", "etz", "-d", "etz_chaim",
        ]
        with open(sql_path) as f:
            return subprocess.run(cmd, cwd=str(compose_dir()), stdin=f).returncode
