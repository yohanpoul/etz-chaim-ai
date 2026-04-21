#!/usr/bin/env python3
"""
QA AUDIT — Validation automatique des perakim transposés.
Protocole codifié à partir du perek_03 Sha'ar 4 (premier 100/100).

Usage:
    python -m sifrei_yesod.pipeline.qa_audit <perek.yaml> [--sefaria "Sefer_Etz_Chaim.4.3"]

Score cible : ≥ 95/100. Si < 95, les corrections sont listées.
"""

import yaml
import os
import re
import sys
import json
import subprocess
from pathlib import Path


def load_yaml(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def check_yaml_valid(path: str) -> tuple[bool, str]:
    """Critère 0 : YAML valide."""
    try:
        load_yaml(path)
        return True, "YAML valide"
    except Exception as e:
        return False, f"YAML invalide : {e}"


def check_granularity(data: dict) -> tuple[int, list[str]]:
    """Critère 3 : GRANULARITÉ — chaque assertion ≤ 8 lignes."""
    score = 10
    issues = []
    for a in data['assertions']:
        lines = a['assertion'].strip().split('\n')
        if len(lines) > 8:
            score -= 2
            issues.append(f"{a['id']}: {len(lines)} lignes (max 8)")
    return max(0, score), issues


def check_mapping_planned(data: dict) -> tuple[int, list[str]]:
    """Critère 9 : MAPPING — [PLANNED] sur les modules inexistants."""
    score = 10
    issues = []
    for a in data['assertions']:
        for m in a.get('mapping', {}).get('modules', []):
            clean = m.replace('[PLANNED] ', '')
            exists = os.path.exists(clean)
            is_planned = '[PLANNED]' in m
            if not exists and not is_planned:
                score -= 3
                issues.append(f"{a['id']}: '{clean}' inexistant sans [PLANNED]")
            elif exists and is_planned:
                issues.append(f"{a['id']}: '{clean}' EXISTE mais marqué [PLANNED] (mineur)")
    return max(0, score), issues


def check_relations(data: dict) -> tuple[int, list[str]]:
    """Critère 7 : RELATIONS — from/to valides, types précis."""
    score = 10
    issues = []

    # Collect all concept IDs
    concept_ids = set()
    for a in data['assertions']:
        for c in a.get('concepts', []):
            concept_ids.add(c['id'])

    valid_types = {
        'causal', 'séquentiel', 'contenance', 'flux', 'transformation',
        'dualité_structurelle', 'hiérarchique', 'analogie'
    }

    for r in data.get('relations', []):
        if r.get('from') not in concept_ids:
            score -= 2
            issues.append(f"{r['id']}: from='{r['from']}' inexistant dans concepts")
        if r.get('to') not in concept_ids:
            score -= 2
            issues.append(f"{r['id']}: to='{r['to']}' inexistant dans concepts")
        if r.get('type') not in valid_types:
            score -= 1
            issues.append(f"{r['id']}: type='{r['type']}' non standard")

    return max(0, score), issues


def check_principes_modules(data: dict) -> tuple[int, list[str]]:
    """Critère 8 : PRINCIPES — applications_ia avec modules concrets."""
    score = 10
    issues = []
    for p in data.get('principes_generatifs', []):
        has_module = any('/' in app for app in p.get('applications_ia', []))
        if not has_module:
            score -= 3
            issues.append(f"{p['id']}: applications_ia sans référence à un module concret")
    return max(0, score), issues


def check_style(data: dict) -> tuple[int, list[str]]:
    """Critère 2 : STYLE — MAJUSCULES, →, parenthèses hébraïques."""
    score = 10
    issues = []
    total = len(data['assertions'])

    caps_count = 0
    arrow_count = 0
    for a in data['assertions']:
        text = a['assertion']
        # Check for MAJUSCULES percutantes (at least 2 all-caps words per assertion)
        caps_words = re.findall(r'\b[A-ZÉÈÊÀÎÔÛÜÇa-z]*[A-ZÉÈÊÀÎÔÛÜÇ]{2,}[A-ZÉÈÊÀÎÔÛÜÇa-z]*\b', text)
        all_caps = [w for w in caps_words if w == w.upper() and len(w) >= 2]
        if len(all_caps) >= 2:
            caps_count += 1
        if '→' in text:
            arrow_count += 1

    if caps_count < total * 0.8:
        score -= 3
        issues.append(f"Seulement {caps_count}/{total} assertions avec ≥2 MAJUSCULES")
    if arrow_count < total * 0.5:
        score -= 2
        issues.append(f"Seulement {arrow_count}/{total} assertions avec → (flèches)")

    return max(0, score), issues


def check_nusah_aher_source(data: dict, source_path: str = None) -> tuple[int, list[str]]:
    """Critère 5 : NUSAH AHER — toutes les variantes du source capturées."""
    if not source_path or not os.path.exists(source_path):
        return 8, ["Source Sefaria non fournie — vérification manuelle requise"]

    with open(source_path) as f:
        source = json.load(f)

    # Count UNIQUE variants in source (same text appearing twice = 1 variant)
    seen = set()
    for p in source.get('text_hebrew', []):
        for m in re.findall(r'\(([^)]*ל"ג[^)]*)\)', p):
            seen.add(m.strip())
        for m in re.findall(r'\[([^\]]+)\]', p):
            seen.add(m.strip())
        for m in re.findall(r'\(נ"א\s([^)]*)\)', p):
            seen.add(m.strip())
    source_variants = len(seen)

    # Count variants captured in yaml (multiple detection methods)
    yaml_variants = 0
    for a in data['assertions']:
        text = a['assertion']
        # Each "Nusah Aher" or "Variante" mention = 1 variant
        yaml_variants += text.lower().count('nusah aher')
        # Each נ"א marker = can cover multiple variants (count semicolons + 1)
        na_matches = re.findall(r'\[נ"א[^\]]*\]', text)
        for m in na_matches:
            yaml_variants += m.count(';') + 1
        # Standalone נ"א not in brackets (already counted if also "Nusah Aher")
        standalone_na = text.count('נ"א') - len(na_matches)
        if standalone_na > 0 and 'nusah aher' not in text.lower():
            yaml_variants += standalone_na
        # Bracketed source variants like [שהוא עקודים] captured inline
        source_he = a.get('source_he', '')
        yaml_variants += len(re.findall(r'\[([^\]"]+)\]', source_he))

    score = 10
    issues = []
    if yaml_variants < source_variants:
        missing = source_variants - yaml_variants
        score -= missing * 2
        issues.append(f"{yaml_variants}/{source_variants} variantes capturées ({missing} manquantes)")

    return max(0, score), issues


def check_renvois(data: dict) -> tuple[int, list[str]]:
    """Critère 10 : RENVOIS — cross-références inter-perek."""
    score = 10
    issues = []

    ref_count = 0
    for a in data['assertions']:
        text = a['assertion']
        ref_count += len(re.findall(r'cf\.\s*EC-', text))
        ref_count += text.count('perek_0')

    if ref_count == 0:
        score -= 5
        issues.append("AUCUN renvoi inter-perek (cf. EC-... ou perek_0N)")
    elif ref_count < 3:
        score -= 3
        issues.append(f"Seulement {ref_count} renvois (minimum recommandé : 3)")

    return max(0, score), issues


def run_audit(yaml_path: str, sefaria_ref: str = None):
    """Exécute l'audit complet sur 10 critères."""

    print("═══════════════════════════════════════════════")
    print(f"  QA AUDIT — {os.path.basename(yaml_path)}")
    print("═══════════════════════════════════════════════\n")

    # Critère 0 : YAML valide
    valid, msg = check_yaml_valid(yaml_path)
    if not valid:
        print(f"❌ YAML INVALIDE : {msg}")
        return 0

    data = load_yaml(yaml_path)
    n_assertions = len(data.get('assertions', []))
    n_relations = len(data.get('relations', []))
    n_principes = len(data.get('principes_generatifs', []))
    print(f"Assertions: {n_assertions} | Relations: {n_relations} | Principes: {n_principes}\n")

    # Fetch Sefaria source if ref provided
    source_path = None
    if sefaria_ref:
        try:
            result = subprocess.run(
                ['python', '-m', 'sifrei_yesod.pipeline.fetch_sefaria', sefaria_ref],
                capture_output=True, text=True, timeout=30
            )
            # Extract saved path from output
            for line in result.stdout.split('\n'):
                if 'Saved:' in line:
                    source_path = line.split('Saved:')[1].strip()
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    # Run all checks
    checks = {
        "1. COUVERTURE":    (None, ["Vérification manuelle requise — comparer §§ source vs assertions"]),
        "2. STYLE":         check_style(data),
        "3. GRANULARITÉ":   check_granularity(data),
        "4. SOURCE_HE":     (None, ["Vérification manuelle requise — comparer 3 citations mot-à-mot"]),
        "5. NUSAH AHER":    check_nusah_aher_source(data, source_path),
        "6. ÉRUDITION":     (None, ["Vérification manuelle requise — gematriot, noms, doctrine"]),
        "7. RELATIONS":     check_relations(data),
        "8. PRINCIPES":     check_principes_modules(data),
        "9. MAPPING":       check_mapping_planned(data),
        "10. RENVOIS":      check_renvois(data),
    }

    total = 0
    auto_total = 0
    auto_count = 0

    for name, (score, issues) in checks.items():
        if score is None:
            symbol = "👁"
            display = "MANUEL"
        else:
            auto_total += score
            auto_count += 1
            if score == 10:
                symbol = "✓"
            elif score >= 7:
                symbol = "⚠"
            else:
                symbol = "❌"
            display = f"{score}/10"
            total += score

        print(f"  {symbol} {name}: {display}")
        for issue in issues:
            print(f"      → {issue}")

    print(f"\n───────────────────────────────────────────────")
    print(f"  Score automatisé : {auto_total}/{auto_count * 10}")
    print(f"  Critères manuels : 1 (COUVERTURE), 4 (SOURCE_HE), 6 (ÉRUDITION)")
    print(f"  → Score final = auto + manuels (noter chacun /10)")

    if auto_total == auto_count * 10:
        print(f"\n  ✓ CRITÈRES AUTO : TOUS PASSÉS")
    else:
        print(f"\n  ⚠ CORRECTIONS REQUISES sur les critères automatiques")

    print("═══════════════════════════════════════════════\n")

    return auto_total


# ═══════════════════════════════════════════════
# PROTOCOLE D'AUDIT COMPLET (pour Claude)
# ═══════════════════════════════════════════════
#
# Étapes quand on audite un perek auto-transposé :
#
# 1. FETCH le texte source :
#    python -m sifrei_yesod.pipeline.fetch_sefaria "Sefer_Etz_Chaim.{S}.{P}"
#
# 2. LIRE le perek.yaml ET 1 exemple manuel (perek_02a.yaml gold standard)
#
# 3. VÉRIFIER chaque critère /10 :
#
#    [AUTO] 2. STYLE      — MAJUSCULES, →, phrases courtes
#    [AUTO] 3. GRANULARITÉ — max 8 lignes/assertion
#    [AUTO] 5. NUSAH AHER — regex sur source vs yaml
#    [AUTO] 7. RELATIONS   — from/to existent, types valides
#    [AUTO] 8. PRINCIPES   — applications_ia avec modules concrets
#    [AUTO] 9. MAPPING     — [PLANNED] sur inexistants
#    [AUTO] 10. RENVOIS    — cross-refs inter-perek
#
#    [MANUEL] 1. COUVERTURE — chaque phrase source → ≥1 assertion
#    [MANUEL] 4. SOURCE_HE  — 3 citations mot-à-mot vs source fetché
#    [MANUEL] 6. ÉRUDITION  — gematriot, noms, translittérations, doctrine
#
# 4. NOTER /100
#
# 5. Si < 95 : CORRIGER et re-vérifier
#    Corrections typiques :
#    - Assertions trop longues → découper ou condenser
#    - [PLANNED] manquant → ajouter
#    - Nusah aher oublié → retrouver dans source avec regex
#    - Calcul brouillon visible → nettoyer
#    - applications_ia génériques → ajouter modules concrets
#    - Renvois manquants → cf. EC-xxx des perakim précédents
#
# 6. Si ≥ 95 : QUALITÉ VALIDÉE
#
# GOLD STANDARD : perek_02a.yaml (Sha'ar 1, transposé manuellement)
# PREMIER 100/100 AUTO : perek_03.yaml (Sha'ar 4, corrigé après audit)
# ═══════════════════════════════════════════════


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python -m sifrei_yesod.pipeline.qa_audit <perek.yaml> [--sefaria REF]")
        sys.exit(1)

    yaml_path = sys.argv[1]
    sefaria_ref = None
    if '--sefaria' in sys.argv:
        idx = sys.argv.index('--sefaria')
        if idx + 1 < len(sys.argv):
            sefaria_ref = sys.argv[idx + 1]

    run_audit(yaml_path, sefaria_ref)
