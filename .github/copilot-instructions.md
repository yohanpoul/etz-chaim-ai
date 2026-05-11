# Etz Chaim AI — GitHub Copilot instructions

The canonical agent instructions for this project live in [AGENTS.md](../AGENTS.md).

This file exists because GitHub Copilot looks for `.github/copilot-instructions.md`
specifically and doesn't follow symlinks reliably. Read AGENTS.md for the
authoritative instructions.

Key points (for Copilot's instruction budget):
- Never write directly to aggregate scores — use named channels
- Spec mutations require Plan mode + verify-spec subagent
- All 1388 tests must pass in <3s before any merge
- E1-E6 citations required on new spec assertions
- Anthropic-specific features are bonuses, not requirements

See [AGENTS.md](../AGENTS.md) for the full picture.
