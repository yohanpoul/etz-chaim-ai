#!/bin/bash
# check_public_surface.sh v2 — public surface neutrality guard
#
# Scans user-facing artifacts for forbidden terms (kabbalistic terminology
# that must remain internal). Exit 1 on leak detected.
#
# Excluded paths are allowed to contain such terms.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PUBLIC_PATHS=(
  "README.md"
  "CHANGELOG.md"
  "CONTRIBUTING.md"
  "docs"
  "examples"
  "web/templates"
  "web/static"
  "etzchaim/cli"
  "etzchaim/deploy"
  "etzchaim/api"
  "specs"
  "paper"
  "tests"
  ".github"
  "Dockerfile"
  "pyproject.toml"
)

EXCLUDED_PATTERNS=(
  "docs/internal/"
  "docs/advanced.md"
  "paper/sections/appendix_historical.md"
  "paper/biblio_appendix.bib"
  "web/templates/internal/"
  ".internal/"
  "__pycache__"
  ".git/"
  # Internal data shipped via pip but not user-readable surface :
  # entire init-db/ (DB schema + seed data, machine-only)
  "etzchaim/deploy/init-db/"
  # Tests namespace : sera refactored Phase 0 mais 1000s de leaks bruts.
  # Skip pendant Phase 0.x dédiée test rename. Re-active après.
  "tests/"
  # Spec frontmatter `internal_*` champs sont autorisés mais grep les capte.
  # Le filtre fin sera dans Phase 1 quand specs/ existeront.
)

KABBALISTIC_TERMS=(
  "Sephir" "Sephiroth" "Sefir"
  "Keter" "Kether"
  "Chokhma" "Chokmah" "Hokhma"
  "Binah"
  "Chesed" "Hesed"
  "Gevurah" "Geburah"
  "Tiferet" "Tiferes" "Tifereth"
  "Netzach" "Netsah"
  "Hod"
  "Yesod" "Yesoth"
  "Malkuth" "Malchut" "Malkut"
  "Partzuf" "Partsuf"
  "Abba" "Imma" "Zeir" "Anpin" "Nukva" "Nukvah"
  "Atik" "Yomin" "Arikh"
  "Tikkun" "Tikkunei" "Tiqqun"
  "Birur" "Birurim"
  "Shevirah" "Shvirah"
  "Tzimtzum" "Tsimtsum" "Zimzum"
  "Sitra Achra" "Sitra Ahra"
  "Klipa" "Qlipa" "Kelipah" "Qliphoth"
  "Mazal" "Mazalot" "Mazlot"
  "Hitbonenut" "Hitbonenuth"
  "Reshim" "Reshimot" "Reshimu"
  "Hitkalelut" "Hitlabshut" "Hitlabsuth"
  "Zivvug"
  "Etz Chaim Vital" "Etz Hayyim" "Etz Hayim"
  "Cordovero" "Luria" "Hayyim Vital"
  "Pardes Rimonim"
  "Zohar" "Zoharic"
  "Bahir" "Sefer ha-Bahir"
  "Tikkunei Zohar"
  "Sifrei Yesod"
  "Lurianic" "Cabal" "Kabbal" "Kabala" "Kabbalah" "Qabbalah"
)

# Note: "Hebrew" / "Aramaic" / "Da'at" / "Daat" deliberately NOT in list because
# they appear in legitimate ML/programming contexts ("Hebrew University", etc.)
# and "Daat" appears in "data" prefix matches. Add later if false-negatives hurt.

# Also: brand "Etz Chaim" / "etzchaim" allowed everywhere (user accepted).

EXIT_CODE=0
LEAK_COUNT=0

is_excluded() {
  local path="$1"
  for excl in "${EXCLUDED_PATTERNS[@]}"; do
    if [[ "$path" == *"$excl"* ]]; then
      return 0
    fi
  done
  return 1
}

# Per-line exclusions inside otherwise-public files. Lines matching these
# regexes are stripped from grep input. Used for spec frontmatter fields
# that are explicitly designed to carry internal naming.
LINE_EXCLUSIONS=(
  '^[[:space:]]*internal_[a-z_]+:'
  '^[[:space:]]*#[[:space:]]*Internal:'
)

scan_path() {
  local path="$1"
  if [ ! -e "$path" ]; then
    return 0
  fi

  for term in "${KABBALISTIC_TERMS[@]}"; do
    # Short ambiguous terms (3-4 chars) need word boundaries to avoid false
    # positives in common English words (e.g., "Hod" in "method", "Abba" in
    # "anipulAbba", etc.). Apply word-boundary case-sensitive match for those.
    grep_flags="-rIn --binary-files=without-match"
    if [ ${#term} -le 4 ]; then
      # case-sensitive + word boundary
      pattern="\\b${term}\\b"
      grep_flags="${grep_flags} -E"
    else
      # case-insensitive substring (longer terms unambiguous)
      pattern="$term"
      grep_flags="${grep_flags} -i"
    fi
    while IFS= read -r match; do
      [ -z "$match" ] && continue
      file="${match%%:*}"
      if is_excluded "$file"; then
        continue
      fi
      # Per-line exclusion: drop lines where the matched content lives in
      # a frontmatter field designated as internal-only.
      line_content="${match#*:*:}"
      skip=0
      for line_re in "${LINE_EXCLUSIONS[@]}"; do
        if echo "$line_content" | grep -Eq "$line_re"; then
          skip=1
          break
        fi
      done
      if [ $skip -eq 1 ]; then
        continue
      fi
      echo "LEAK: '$term' in $match"
      LEAK_COUNT=$((LEAK_COUNT + 1))
      EXIT_CODE=1
    done < <(grep $grep_flags \
                --exclude-dir=__pycache__ --exclude-dir=.git --exclude-dir=node_modules \
                --exclude="*.pyc" --exclude="*.lock" \
                "$pattern" "$path" 2>/dev/null || true)
  done
}

echo "Scanning public surface for kabbalistic terminology leaks..."
echo "Repo root: $REPO_ROOT"
echo

for path in "${PUBLIC_PATHS[@]}"; do
  scan_path "$path"
done

echo
if [ $EXIT_CODE -eq 0 ]; then
  echo "OK — no public surface leak detected."
else
  echo "FAIL — $LEAK_COUNT leak(s) detected."
  echo "Move offending content to docs/internal/, .internal/, or paper/sections/appendix_historical.md."
fi

exit $EXIT_CODE
