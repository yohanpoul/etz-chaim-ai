# syntax=docker/dockerfile:1.7
# Etz Chaim AI — multi-stage build for app + daemon.
#
# Stages :
#   base   : runtime deps + user etz + source install
#   app    : Flask web dashboard on :8080
#   daemon : orchestrator (daemon.py) with signal handling
#
# Non-root (uid 1000), tini as PID 1 for clean SIGTERM propagation.
# ETZCHAIM_IN_CONTAINER=1 triggers Flask 0.0.0.0 bind.

ARG PYTHON_VERSION=3.13

# ==================== base ====================
FROM python:${PYTHON_VERSION}-slim AS base

# System deps : postgres-client (psql for db migrate), curl (healthcheck), tini (PID 1)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        curl \
        tini \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (uid 1000 matches most host developer accounts on Linux)
RUN useradd -u 1000 -m -s /bin/bash etz

WORKDIR /app

# Copy dep manifests first for layer caching
COPY pyproject.toml requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
        'anthropic>=0.40' \
        'typer>=0.12' \
        'questionary>=2.0' \
        'rich>=13' \
        'structlog>=24' \
        'PyYAML>=6.0'

# Copy project source
COPY --chown=etz:etz . .

# Editable install to register entry points (etzchaim CLI)
RUN pip install --no-cache-dir -e .

# Ensure state dir exists inside image (volume mount point, owned by etz)
RUN mkdir -p /home/etz/.etz-chaim && chown -R etz:etz /home/etz/.etz-chaim

USER etz

ENV PYTHONUNBUFFERED=1 \
    ETZCHAIM_IN_CONTAINER=1 \
    ETZCHAIM_STATE_DIR=/home/etz/.etz-chaim \
    PATH=/home/etz/.local/bin:$PATH

# ==================== app ====================
FROM base AS app

EXPOSE 8080

ENTRYPOINT ["tini", "--"]

# Launch the Flask dashboard via mitzvot CLI entry (which calls web.create_app + app.run)
# mitzvot web --port 8080 wraps the run (host resolved via ETZCHAIM_IN_CONTAINER → 0.0.0.0)
CMD ["python", "-c", "import os; from web import create_app; app = create_app(); app.run(host='0.0.0.0', port=int(os.environ.get('WEB_PORT', '8080')))"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:8080/api/health || exit 1

# ==================== daemon ====================
FROM base AS daemon

ENTRYPOINT ["tini", "--"]

# daemon.py has its own signal handler; tini ensures SIGTERM propagation.
CMD ["python", "daemon.py"]

HEALTHCHECK --interval=60s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import json, time; s = json.load(open('/home/etz/.etz-chaim/daemon_state.json')); ts = max((v for k, v in s.items() if isinstance(v, (int, float)) and ('last' in k.lower() or 'heartbeat' in k.lower())), default=0); exit(0 if time.time() - ts < 300 else 1)" || exit 1
