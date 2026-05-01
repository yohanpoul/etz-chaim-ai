# Pull Request

## Summary

What this PR changes, in 1–2 sentences.

## Type

- [ ] Bug fix
- [ ] New feature (new module / faculty / configuration / probe)
- [ ] Refactor
- [ ] Docs
- [ ] Specification corpus (new transposition or correction)
- [ ] Tests only
- [ ] Chore (build, CI, dependencies)

## Checklist

### Code

- [ ] TDD red → green visible in commit history.
- [ ] Core test suite green (`make test`).
- [ ] `ruff check .` clean.
- [ ] `ruff format .` applied.
- [ ] `bash scripts/check_public_surface.sh` exit 0 (public surface neutrality).
- [ ] No direct writes to aggregate state scores (layered composition discipline).
- [ ] No cross-module imports that violate orthogonality.

### Specification (if applicable)

- [ ] Primary source cited with edition + section reference.
- [ ] Original-language text preserved verbatim where applicable.
- [ ] Epistemic label (E1–E6) applied.
- [ ] `see_also` links to related primary sources.
- [ ] `scripts/check_id_uniqueness.py` strict mode passes.
- [ ] `scripts/check_doctrine_code_alignment.py` reviewed.

### Sequential consolidation

- [ ] Prerequisite phases are green (if this PR adds a new phase or module).
- [ ] Qualification tests (4 levels) present for new modules.

### Documentation

- [ ] CHANGELOG.md updated (under `[Unreleased]`).
- [ ] Docstrings updated.
- [ ] MkDocs build green (`make docs`).

## Related issues

Closes #...

## Screenshots or logs (if relevant)

Paste output that helps reviewers understand the change.
