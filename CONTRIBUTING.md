# Contributing to Etz Chaim AI

Thank you for your interest in contributing. Etz Chaim AI is a cognitive operating system for LLM agents — contributions require specific discipline.

## Before contributing

Please read, in order :

1. [`README.md`](README.md) — project vision and scope.
2. [`docs/roadmap.md`](docs/roadmap.md) — shipped phases and planned sprints.
3. [`docs/architecture.md`](docs/architecture.md) — architectural disciplines (sequential consolidation, layered composition, persistent trace).
4. [`SECURITY.md`](SECURITY.md) — security policy and disclosure.

For contributors curious about the structural framework that inspired the architecture, see [`docs/advanced.md`](docs/advanced.md). It is informational only — never required to contribute.

## Three disciplines

### 1. Sequential consolidation

The project follows a strict consolidation order : each cognitive faculty is consolidated **before** the next. Do **not** contribute code for a phase whose prerequisites are not green. Check the open issues and `CHANGELOG.md` for the current state.

Concretely :
- Every new configuration module comes with its 4-level qualification tests (foundation / application / excess / opposite).
- Every boost mechanism passes through the layered composition channel (faculties), never directly on the aggregate score.
- Every new specification mapping is labeled with an epistemic level (see below).

### 2. Epistemic rigor (E1–E6)

Each specification claim must carry an epistemic label :

| Level | Meaning | Example |
|:-----:|:--------|:--------|
| E1 | Primary text, literal | Source quoted verbatim |
| E2 | Primary text, close paraphrase | Translation preserving technical terms |
| E3 | Authoritative commentator reading | Authoritative reading of a primary source |
| E4 | Derived conclusion | Pattern synthesized from multiple sources |
| E5 | Extrapolation | Projecting to a new domain |
| E6 | Speculation | Beyond clear warrant |

Downgrade in doubt. Never use the word "isomorphism" without a proved bijection — prefer "structural analogy" (E3).

### 3. Test-Driven Development (TDD)

**Rigid** : write the failing test before the implementation. Every rectifier code path must have a red→green cycle visible in git history.

Non-regression is non-negotiable : `make test-core` must stay green after your change.

## Development workflow

```bash
# 1. Fork + clone
git clone git@github.com:<your-user>/etz-chaim-ai.git
cd etz-chaim-ai

# 2. Set up environment
make install   # venv + dependencies + pre-commit hooks

# 3. Branch
git checkout -b feat/your-feature

# 4. Write test (TDD red)
# 5. Implement (TDD green)
# 6. Verify
make test      # pytest + ruff + mypy
make docs      # MkDocs build sanity
bash scripts/check_public_surface.sh    # public surface neutrality

# 7. Commit atomically
git add -p
git commit -m "feat(module): short imperative description"

# 8. Push + PR
git push -u origin feat/your-feature
gh pr create
```

## Commit convention

We follow [Conventional Commits](https://www.conventionalcommits.org/) :

```
<type>(<scope>): <short description>

<body — why this change, not just what>

Co-Authored-By: ...
```

Types : `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `style`.

Scopes : match top-level module names (`bridge`, `probes`, `configurations`, `explore`, `autopilot`, …).

Each commit is atomic : one coherent change. Large refactors are split into multiple commits.

## Public surface neutrality

Default user-facing artifacts (README, docs/, examples/, web UI, CLI) must remain neutral — no surface mention of the structural framework's source tradition. See [`.claude/rules/public-surface-neutrality.md`](.claude/rules/public-surface-neutrality.md) for the full rule and `scripts/check_public_surface.sh` for the CI guard.

If your contribution touches an internal module that uses domain-specific naming, that is fine — the neutrality rule applies only to default user-facing surfaces.

## Adding a new configuration / faculty module

1. Open an issue describing the phase and its prerequisites.
2. Define the schema + API + 7 calibration parameters.
3. Write 4-level qualification tests **before** implementation.
4. Implement with fractal self-similarity : each module contains a reflection of its opposite.
5. Add specification mapping assertions in the internal corpus with `see_also` to primary sources.
6. Pass `scripts/check_doctrine_code_alignment.py`.
7. Pass `bash scripts/check_public_surface.sh` if your changes touch any public surface.

## Pull request gates

Every PR is gated by :

1. CI tests green (4 Python versions × 2 OSes)
2. `bash scripts/check_public_surface.sh` exit 0
3. At least one human review for non-trivial changes
4. `human-approved` label before merge for autopilot-generated PRs

## Questions

Open an issue with `[QUESTION]` tag, or reach the maintainer on GitHub.
