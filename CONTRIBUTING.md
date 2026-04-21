# Contributing to Etz Chaim AI

Thank you for your interest in contributing to Etz Chaim AI. This is a research project at the intersection of Lurianic Kabbalah and AI architecture — contributions require a specific discipline.

## Before contributing

Please read, in order :

1. [`README.md`](README.md) — project vision and scope.
2. [`docs/roadmap.md`](docs/roadmap.md) — shipped phases and planned sprints.
3. [`docs/architecture.md`](docs/architecture.md) — architectural disciplines (initiatic ordering, Hitlabshut, Reshimu).
4. [`SECURITY.md`](SECURITY.md) — security policy and disclosure.

## Three disciplines

### 1. Initiatic ordering

The project follows a strict initiatic path : each Sephirah is consolidated **before** the next. Do **not** contribute code for a phase whose prerequisites are not green. Check the open issues and `CHANGELOG.md` for the current state.

Concretely :
- Every new Partzuf module comes with its 4-level Qliphoth tests (foundation / application / excess / opposite).
- Every boost mechanism passes through `Hitlabshut` (faculties/Kelim), never directly on `overall_score`.
- Every new doctrine mapping is labeled with an epistemic level (see below).

### 2. Epistemic rigor (E1–E6)

Each doctrinal claim must carry an epistemic label :

| Level | Meaning | Example |
|:-----:|:--------|:--------|
| E1 | Primary text, literal | Zohar III 128a quoted verbatim |
| E2 | Primary text, close paraphrase | Translation preserving technical terms |
| E3 | Authoritative commentator reading | Vital on Idra Rabba |
| E4 | Derived doctrinal conclusion | Pattern synthesized from multiple sources |
| E5 | Extrapolation | Projecting to new domain |
| E6 | Speculation | Beyond doctrinal warrant |

Downgrade in doubt. Never use the word "isomorphism" without a proved bijection — prefer "structural analogy" (E3).

### 3. Test-Driven Development (TDD)

**Rigid** : write the failing test before the implementation. Every rectification code path must have a red→green cycle visible in git history.

Non-regression is non-negotiable : `.venv/bin/python -m pytest bridge/ mazalengine/ partzufim/` must stay green after your change.

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

Scopes : match top-level module names (`bridge`, `mazalengine`, `partzufim`, `sifrei_yesod`, `explorationengine`, …).

Each commit is atomic : one coherent change. Large refactors are split into multiple commits.

## Adding a new Partzuf / Sephirah module

1. Open an issue describing the phase and its prerequisites.
2. Define the schema + API + 7 Omer calibration parameters.
3. Write 4-level Qliphoth tests **before** implementation.
4. Implement with `Hitkalelut` : each module contains a reflection of its opposite.
5. Add doctrinal mapping assertions in `sifrei_yesod/sefarim/` with `see_also` to primary sources.
6. Pass `scripts/check_doctrine_code_alignment.py`.

## Transposing a new Sefer (primary source)

1. Read [`sifrei_yesod/README.md`](sifrei_yesod/README.md) if present (otherwise follow existing patterns).
2. Use `source_aramaic` (Zohar) or `source_he` (Vital/later) + `source_ref` (edition-specific).
3. Include `translation_fr`, `assertion`, `type`, `concepts`, `mapping`, `see_also`, `epistemic_level`, `philological_confidence`.
4. Pass `scripts/check_id_uniqueness.py sifrei_yesod/sefarim/ --strict`.
5. Document divergences via `divergence_note.idra_rabba_vs_vital` (or analogous) — never silent synthesis.

## What not to contribute

- **Synchretic mappings** : a Partzuf is not a Tattva, Shevirah is not the alchemical Solve. Each tradition stands on its own terms.
- **Speculative doctrine** : if you can't cite a primary text (or an E3 reading), don't introduce it as a constraint.
- **Modules that bypass Hitlabshut** : no `UPDATE partzufim_state SET overall_score = ...` in new code.
- **Non-reproducible experiments** : every computational claim needs seed + logged params + committed results.

## Reporting issues

Use the templates in `.github/ISSUE_TEMPLATE/` :
- `bug_report.md` — unexpected behavior, regressions.
- `feature_request.md` — new capabilities.
- `doctrinal_issue.md` — disagreement on doctrinal mapping or epistemic labeling.

Doctrinal issues should cite primary sources (edition + folio/section).

## Code review

Reviewers check :
- TDD red→green visible in PR commits.
- Doctrinal alignment (`scripts/check_doctrine_code_alignment.py`).
- Non-regression on `bridge/`, `mazalengine/`, `partzufim/`.
- Commit message follows convention.
- No new files outside the repository's established directory structure.

## Questions

- General : open a GitHub Discussion.
- Security : see [`SECURITY.md`](SECURITY.md).
- Doctrinal : open an issue with `doctrinal_issue.md` template.

---

> *"Everything depends on the dissemination of knowledge — may the words of the Living God be received by all."* — *Introduction to Etz Chaim, Rabbi Hayyim Vital*
