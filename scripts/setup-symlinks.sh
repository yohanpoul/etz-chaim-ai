#!/usr/bin/env bash
# scripts/setup-symlinks.sh — wire CLAUDE.md / .codex / .cursor to AGENTS.md
#
# Etz Chaim AI uses AGENTS.md as the single source of truth for agent
# instructions. This script sets up the symlinks / references so every
# coding agent (Claude Code, Codex CLI, Cursor, Windsurf, Antigravity, etc.)
# reads the same canonical instructions.
#
# Run once after cloning. Idempotent — safe to re-run.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "═══════════════════════════════════════════════════════════════"
echo "  Etz Chaim AI — Setting up agent config symlinks"
echo "═══════════════════════════════════════════════════════════════"
echo ""

if [[ ! -f AGENTS.md ]]; then
  echo "ERROR: AGENTS.md not found at repo root. Are you in the right directory?"
  exit 1
fi

# Helper — symlink with backup
make_symlink() {
  local target="$1"
  local link="$2"

  if [[ -L "$link" ]]; then
    # Already a symlink — check if it points where we want
    if [[ "$(readlink "$link")" == "$target" ]]; then
      echo "  ✓ $link already symlinks to $target"
      return 0
    else
      echo "  ⟳ $link points elsewhere, updating"
      rm "$link"
    fi
  elif [[ -f "$link" ]]; then
    # Real file — back it up
    local backup="${link}.backup.$(date +%Y%m%d-%H%M%S)"
    echo "  ⚠ $link exists as a real file, backing up to $backup"
    mv "$link" "$backup"
  fi

  ln -s "$target" "$link"
  echo "  ✓ Created symlink: $link → $target"
}

# 1. CLAUDE.md → AGENTS.md (Claude Code reads symlinks fine)
echo "─── 1. Claude Code (CLAUDE.md → AGENTS.md) ───"
make_symlink AGENTS.md CLAUDE.md
echo ""

# 2. .codex/AGENTS.md → ../AGENTS.md (Codex CLI reads it)
echo "─── 2. OpenAI Codex CLI (.codex/AGENTS.md) ───"
mkdir -p .codex
make_symlink ../AGENTS.md .codex/AGENTS.md
echo ""

# 3. .cursor/rules/etz-base.mdc → references AGENTS.md
echo "─── 3. Cursor (.cursor/rules/etz-base.mdc) ───"
mkdir -p .cursor/rules
cat > .cursor/rules/etz-base.mdc <<'EOF'
---
description: Etz Chaim AI base rules — see AGENTS.md for canonical instructions
alwaysApply: true
---

# Etz Chaim AI — Cursor rules

The canonical agent instructions for this project live in
[AGENTS.md](../../AGENTS.md). Read that file first.

Cursor reads both AGENTS.md and CLAUDE.md natively as of v0.45+, so this
rule file mainly serves as a discovery breadcrumb.

For the full source-unique config, see [AGENTS.md](../../AGENTS.md).
EOF
echo "  ✓ Created Cursor rule reference at .cursor/rules/etz-base.mdc"
echo ""

# 4. .windsurfrules → reference AGENTS.md (Windsurf legacy format)
echo "─── 4. Windsurf (.windsurfrules) ───"
if [[ ! -f .windsurfrules ]]; then
  cat > .windsurfrules <<'EOF'
# Etz Chaim AI — Windsurf rules
# Canonical instructions: see AGENTS.md in repo root.
# This file is a pointer; AGENTS.md is the source of truth.

See AGENTS.md for behavioral rules, available tools, and architecture notes.
EOF
  echo "  ✓ Created Windsurf rule pointer at .windsurfrules"
else
  echo "  ✓ .windsurfrules already exists, leaving alone"
fi
echo ""

# 5. GEMINI.md → reference AGENTS.md (Gemini CLI reads GEMINI.md, doesn't follow symlinks predictably)
echo "─── 5. Gemini CLI (GEMINI.md) ───"
if [[ ! -f GEMINI.md ]]; then
  cat > GEMINI.md <<'EOF'
# Etz Chaim AI — Gemini CLI memory

The canonical agent instructions for this project live in AGENTS.md.

Please load and follow AGENTS.md as your primary instruction source.
This file exists because Gemini CLI looks for GEMINI.md specifically.

See [AGENTS.md](AGENTS.md) for:
- Critical invariants
- Architecture overview
- Available tools (Skills, MCP, subagents, slash commands)
- Behavior rules (Boris-aligned)
- Provider compatibility notes
EOF
  echo "  ✓ Created Gemini CLI pointer at GEMINI.md"
else
  echo "  ✓ GEMINI.md already exists, leaving alone"
fi
echo ""

# 6. .github/copilot-instructions.md → reference AGENTS.md
echo "─── 6. GitHub Copilot (.github/copilot-instructions.md) ───"
mkdir -p .github
if [[ ! -f .github/copilot-instructions.md ]]; then
  cat > .github/copilot-instructions.md <<'EOF'
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
EOF
  echo "  ✓ Created Copilot pointer at .github/copilot-instructions.md"
else
  echo "  ✓ .github/copilot-instructions.md already exists, leaving alone"
fi
echo ""

# 7. Verify
echo "═══════════════════════════════════════════════════════════════"
echo "  Verification"
echo "═══════════════════════════════════════════════════════════════"
echo ""
for f in CLAUDE.md .codex/AGENTS.md .cursor/rules/etz-base.mdc .windsurfrules GEMINI.md .github/copilot-instructions.md; do
  if [[ -L "$f" ]]; then
    echo "  ✓ $f → $(readlink "$f")"
  elif [[ -f "$f" ]]; then
    echo "  ✓ $f (pointer file)"
  else
    echo "  ✗ $f MISSING — please re-run"
  fi
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Done. Every coding agent will now read from AGENTS.md."
echo "  Edit AGENTS.md only — never edit the symlink targets directly."
echo "═══════════════════════════════════════════════════════════════"
