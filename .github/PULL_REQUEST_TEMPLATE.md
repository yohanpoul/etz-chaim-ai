# Pull Request

## Summary

What this PR changes, in 1–2 sentences.

## Type

- [ ] Bug fix
- [ ] New feature (new module / Partzuf / Mazal)
- [ ] Refactor
- [ ] Docs
- [ ] Doctrinal corpus (new transposition or correction)
- [ ] Tests only
- [ ] Chore (build, CI, dependencies)

## Checklist

### Code

- [ ] TDD red → green visible in commit history.
- [ ] `pytest bridge/tests mazalengine/tests partzufim/tests` green.
- [ ] `ruff check .` clean.
- [ ] `ruff format .` applied.
- [ ] No direct writes to `partzufim_state.overall_score` (Hitlabshut).
- [ ] No new imports of `partzufim.*` from adversarial / mazal / rectification modules (orthogonality).

### Doctrine (if applicable)

- [ ] Primary source cited with edition + folio / section reference.
- [ ] Original-language text preserved verbatim in `source_he` / `source_aramaic`.
- [ ] Epistemic label (E1–E6) applied.
- [ ] `see_also` links to related primary sources.
- [ ] `scripts/check_id_uniqueness.py sifrei_yesod/sefarim/ --strict` passes.
- [ ] `scripts/check_doctrine_code_alignment.py` reviewed.

### Initiatic ordering

- [ ] Prerequisite phases are green (if this PR adds a new phase or module).
- [ ] Qliphoth tests (4 levels) present for new modules.

### Documentation

- [ ] CHANGELOG.md updated (under `[Unreleased]`).
- [ ] Docstrings updated.
- [ ] MkDocs build green (`make docs`).

## Related issues

Closes #...

## Screenshots or logs (if relevant)

Paste output that helps reviewers understand the change.
