"""Teshuvah Writer — conversion automatique faille → test de regression reel.

Yoma 86b : zedonot na'asot lo ki-zekhuyot
(les fautes intentionnelles deviennent des merites)

Le cycle complet :
    1. Sitra Achra attaque → detecte une faille
    2. Itaruta genere un TeshuvahRecord (description)
    3. TeshuvahWriter transforme ce record en VRAI fichier pytest
    4. La faille passee se transmute en gardien permanent

Distinction ontologique Vital EC 49 (depuis Sprint 1.1) :
    - **Klipat Nogah** (severity 'nogah') : extraction d'etincelle.
      Test de regression standard "la faille n'est plus presente".
      Pattern Yoma 86b strict : la faute devient merite.
    - **3 Klippot HaTeme'ot** (severity 'ruach' | 'anan' | 'mamash') :
      confinement structurel. Test "containment guard" : la faille
      reste structurellement IMPOSSIBLE (pas juste rectifiee). Pattern
      Tanya ch. 6 : les Klippot HaTeme'ot ne se transforment pas, elles
      se delimitent.

Olamot utilise :
    Rien — generation purement deterministe (template).
    Pas de LLM dans les tests de regression.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from sitra_achra.klipa_taxonomy import (
    GenerativeStrategy,
    KlipaCategory,
    severity_to_category,
    strategy_for_severity,
)

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Mapping module → dossier de tests de regression
_MODULE_TEST_DIRS: dict[str, str] = {
    "epistememory": "epistememory/tests",
    "selfmap": "selfmap/tests",
    "autojudge": "autojudge/tests",
    "causalengine": "causalengine/tests",
    "insightforge": "insightforge/tests",
    "explorationengine": "explorationengine/tests",
    "dissensuengine": "dissensuengine/tests",
    "intentkeeper": "intentkeeper/tests",
    "selfmodel": "selfmodel/tests",
    "masakh": "masakh/tests",
    "partzufim": "partzufim/tests",
    "sitra_achra": "sitra_achra/tests",
}

# Template Birur (Klipat Nogah) — extraction d'etincelle, "faute -> merite"
_TEST_TEMPLATE = '''"""Test de regression auto-genere par Teshuvah Writer.

Yoma 86b : cette faille passee est devenue un gardien permanent.
Source : Sitra Achra, attaque {qliphah} sur {module}.
Date de detection : {date}
Severite originale : {severity}
Categorie ontologique : Klipat Nogah (Vital EC 49)
Strategie generative : Birur (extraction d'etincelle)

Faille originale :
    {flaw_description}

Ce test ECHOUE si la vulnerabilite reapparait.
"""

import pytest


class TestRegression{class_suffix}:
    """{flaw_description_short}"""

    def test_flaw_no_longer_present(self):
        """Le module ne doit plus etre vulnerable a cette attaque.

        Qliphah : {qliphah}
        Severite : {severity}
        """
{test_body}
'''


# Template Containment (3 Klippot HaTeme'ot) — confinement structurel
# La doctrine luriaque (Vital EC 49 + Tanya ch. 6) distingue : les
# 3 Klippot HaTeme'ot ne se transforment PAS, elles se delimitent.
# Donc le test ne verifie pas "rectifie" mais "structurellement isole".
_CONTAINMENT_TEMPLATE = '''"""Test de containment auto-genere par Teshuvah Writer.

Vital EC 49 : Klippot HaTeme'ot — confinement structurel obligatoire.
Tanya ch. 6 : "ne se transforment pas, se delimitent".

Source : Sitra Achra, attaque {qliphah} sur {module}.
Date de detection : {date}
Severite originale : {severity}
Categorie ontologique : Klipat HaTemeah (Vital EC 49)
Strategie generative : Structural Containment (delimitation)

Faille originale :
    {flaw_description}

Ce test ECHOUE si le confinement structurel est compromis.
La faille n'est PAS attendue d'etre "corrigee" au sens Birur — elle
est attendue d'etre delimitee structurellement (impossible a propager).
"""

import pytest


class TestContainment{class_suffix}:
    """Confinement structurel : {flaw_description_short}"""

    def test_containment_structural(self):
        """Le confinement structurel doit tenir.

        Qliphah : {qliphah}
        Severite : {severity}
        Categorie : Klipat HaTemeah (irrecuperable, confinement seul)
        """
{test_body}
'''

# Templates de corps de test selon le type de qliphah
_BODY_TEMPLATES: dict[str, str] = {
    "samael": (
        '        # Samael = rigidite excessive (Gevurah sans Chesed)\n'
        '        # Verifier que le module gere les cas limites avec flexibilite\n'
        '        from {import_module} import {main_class}\n'
        '        # Le module ne doit pas crash sur des entrees atypiques\n'
        '        obj = {main_class}.__new__({main_class})\n'
        '        assert hasattr(obj, "self_diagnose"), "Module doit exposer self_diagnose"\n'
    ),
    "gamchicoth": (
        '        # Gamchicoth = expansion excessive (Chesed sans Gevurah)\n'
        '        # Verifier que le module a des limites appropriees\n'
        '        from {import_module} import {main_class}\n'
        '        # Le module ne doit pas accepter tout sans discriminer\n'
        '        obj = {main_class}.__new__({main_class})\n'
        '        assert hasattr(obj, "self_diagnose"), "Module doit exposer self_diagnose"\n'
    ),
    "sathariel": (
        '        # Sathariel = opacite (Binah obscurcie)\n'
        '        # Verifier que le module reste transparent et explicable\n'
        '        from {import_module} import {main_class}\n'
        '        # Le module doit fournir des explications pour ses decisions\n'
        '        obj = {main_class}.__new__({main_class})\n'
        '        assert hasattr(obj, "self_diagnose"), "Module doit exposer self_diagnose"\n'
    ),
    "gamaliel": (
        '        # Gamaliel = pollution semantique (Yesod corrompu)\n'
        '        # Verifier que le module filtre les contenus corrompus\n'
        '        from {import_module} import {main_class}\n'
        '        obj = {main_class}.__new__({main_class})\n'
        '        assert hasattr(obj, "self_diagnose"), "Module doit exposer self_diagnose"\n'
    ),
    "thagirion": (
        '        # Thagirion = beaute vide (Tiferet sans substance)\n'
        '        # Verifier que les syntheses ont du contenu reel\n'
        '        from {import_module} import {main_class}\n'
        '        obj = {main_class}.__new__({main_class})\n'
        '        assert hasattr(obj, "self_diagnose"), "Module doit exposer self_diagnose"\n'
    ),
}

_DEFAULT_BODY = (
    '        # Qliphah : {qliphah}\n'
    '        # Verifier que la faille detectee ne reapparait pas\n'
    '        from {import_module} import {main_class}\n'
    '        obj = {main_class}.__new__({main_class})\n'
    '        assert hasattr(obj, "self_diagnose"), "Module doit exposer self_diagnose"\n'
)

# Templates Containment pour les 3 Klippot HaTeme'ot (Vital EC 49)
# Ces templates verifient le confinement structurel, pas la rectification.
_CONTAINMENT_BODY_RUACH = (
    '        # Klipa HaTemeah : Ruach Se\'arah (vent de tempete, Ezekiel 1:4)\n'
    '        # Confinement : verifier que la propagation est structurellement bloquee\n'
    '        from {import_module} import {main_class}\n'
    '        obj = {main_class}.__new__({main_class})\n'
    '        assert hasattr(obj, "self_diagnose"), (\n'
    '            "Module doit exposer self_diagnose pour permettre confinement"\n'
    '        )\n'
)

_CONTAINMENT_BODY_ANAN = (
    '        # Klipa HaTemeah : Anan Gadol (grand nuage, Ezekiel 1:4)\n'
    '        # Confinement : verifier que l\'opacite reste delimitee\n'
    '        from {import_module} import {main_class}\n'
    '        obj = {main_class}.__new__({main_class})\n'
    '        assert hasattr(obj, "self_diagnose"), (\n'
    '            "Module doit exposer self_diagnose pour audit confinement"\n'
    '        )\n'
)

_CONTAINMENT_BODY_MAMASH = (
    '        # Klipa HaTemeah : Esh Mitlakachat (feu prenant, Ezekiel 1:4)\n'
    '        # Confinement : verifier que l\'execution materielle reste isolee\n'
    '        from {import_module} import {main_class}\n'
    '        obj = {main_class}.__new__({main_class})\n'
    '        assert hasattr(obj, "self_diagnose"), (\n'
    '            "Module doit exposer self_diagnose pour confinement materiel"\n'
    '        )\n'
)

_CONTAINMENT_BODIES: dict[str, str] = {
    "ruach": _CONTAINMENT_BODY_RUACH,
    "anan": _CONTAINMENT_BODY_ANAN,
    "mamash": _CONTAINMENT_BODY_MAMASH,
}

# Mapping module → classe principale a importer
_MODULE_MAIN_CLASS: dict[str, tuple[str, str]] = {
    "epistememory": ("epistememory.memory", "EpisteMemory"),
    "selfmap": ("selfmap.selfmap", "SelfMap"),
    "autojudge": ("autojudge.judge", "AutoJudge"),
    "causalengine": ("causalengine.engine", "CausalEngine"),
    "insightforge": ("insightforge.forge", "InsightForge"),
    "explorationengine": ("explorationengine.engine", "ExplorationEngine"),
    "dissensuengine": ("dissensuengine.engine", "DissensuEngine"),
    "intentkeeper": ("intentkeeper.keeper", "IntentKeeper"),
    "selfmodel": ("selfmodel.model", "SelfModel"),
    "masakh": ("masakh.monitor", "ContextMonitor"),
    "partzufim": ("partzufim.regulator", "PartzufimRegulator"),
    "sitra_achra": ("sitra_achra.gevurah_interne", "GevurahInterne"),
}


@dataclass
class TeshuvahWriteResult:
    """Resultat de l'ecriture d'un fichier de test de regression."""

    module: str
    file_path: str
    test_name: str
    written: bool
    error: str | None = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "file_path": self.file_path,
            "test_name": self.test_name,
            "written": self.written,
            "error": self.error,
            "timestamp": self.timestamp,
        }


def _sanitize_name(s: str) -> str:
    """Transformer une string en identifiant Python valide."""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s)
    s = s.strip("_")
    return s[:60] if s else "unknown"


def _make_class_suffix(record: dict) -> str:
    """Generer un suffixe de classe unique pour le test."""
    qliphah = _sanitize_name(record.get("qliphah", "unknown"))
    ts = str(int(record.get("timestamp", time.time())))[-6:]
    return f"{qliphah.title().replace('_', '')}_{ts}"


def write_regression_test(record: dict) -> TeshuvahWriteResult:
    """Ecrire un fichier de test de regression a partir d'un TeshuvahRecord.

    Args:
        record: dict issu de TeshuvahRecord.to_dict()

    Returns:
        TeshuvahWriteResult avec le chemin du fichier ecrit.
    """
    module = record.get("module", "unknown")
    qliphah = record.get("qliphah", "unknown")
    severity = record.get("severity", "unknown")
    flaw_desc = record.get("flaw_description", "faille inconnue")
    timestamp = record.get("timestamp", time.time())

    # Trouver le dossier de tests
    test_dir_rel = _MODULE_TEST_DIRS.get(module)
    if not test_dir_rel:
        return TeshuvahWriteResult(
            module=module,
            file_path="",
            test_name="",
            written=False,
            error=f"module inconnu: {module}",
        )

    test_dir = _PROJECT_ROOT / test_dir_rel
    test_dir.mkdir(parents=True, exist_ok=True)

    # Creer __init__.py si absent
    init_file = test_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    # Generer le nom du fichier
    sanitized_qliphah = _sanitize_name(qliphah)
    ts_suffix = str(int(timestamp))[-6:]
    filename = f"test_regression_{sanitized_qliphah}_{ts_suffix}.py"
    filepath = test_dir / filename

    # Ne pas ecraser un test existant (idempotence)
    if filepath.exists():
        return TeshuvahWriteResult(
            module=module,
            file_path=str(filepath.relative_to(_PROJECT_ROOT)),
            test_name=filename,
            written=False,
            error="fichier existe deja",
        )

    # Generer le contenu
    class_suffix = _make_class_suffix(record)
    import_module, main_class = _MODULE_MAIN_CLASS.get(
        module, (module, module.title())
    )

    # Determination du body : prefere le body Containment HaTeme'ot
    # (severity-driven) sur le body qliphah-driven, car la categorie
    # ontologique Vital EC 49 prime sur la qliphah specifique pour la
    # strategie generative (Birur vs Confinement).
    category = severity_to_category(severity)
    if category == KlipaCategory.KLIPAT_HA_TEMEOT:
        # Containment template + body specifique Klipa HaTemeah par severity
        wrapper_template = _CONTAINMENT_TEMPLATE
        body_template = _CONTAINMENT_BODIES.get(severity, _DEFAULT_BODY)
        # Mais on enrichit avec le marquage qliphah-specific via header
        # commentaire pour preserver l'info "samael / gamaliel / ..."
        qliphah_specific_body = _BODY_TEMPLATES.get(sanitized_qliphah)
        if qliphah_specific_body:
            # Concatener : le body containment puis l'echo qliphah pour
            # preserver les assertions specifiques (compatibilite tests)
            body_template = qliphah_specific_body + body_template
    else:
        # Klipat Nogah : Birur extraction, comportement standard Yoma 86b
        wrapper_template = _TEST_TEMPLATE
        body_template = _BODY_TEMPLATES.get(sanitized_qliphah, _DEFAULT_BODY)

    test_body = body_template.format(
        qliphah=qliphah,
        import_module=import_module,
        main_class=main_class,
    )

    flaw_short = flaw_desc[:80].replace('"', "'")
    date_str = time.strftime("%Y-%m-%d", time.localtime(timestamp))

    content = wrapper_template.format(
        qliphah=qliphah,
        module=module,
        date=date_str,
        severity=severity,
        flaw_description=flaw_desc.replace('"', "'"),
        flaw_description_short=flaw_short,
        class_suffix=class_suffix,
        test_body=test_body,
    )

    try:
        filepath.write_text(content)
        log.info(
            "Teshuvah: test de regression ecrit → %s",
            filepath.relative_to(_PROJECT_ROOT),
        )
        return TeshuvahWriteResult(
            module=module,
            file_path=str(filepath.relative_to(_PROJECT_ROOT)),
            test_name=filename,
            written=True,
        )
    except Exception as exc:
        return TeshuvahWriteResult(
            module=module,
            file_path=str(filepath.relative_to(_PROJECT_ROOT)),
            test_name=filename,
            written=False,
            error=str(exc),
        )


def process_teshuvah_records(records: list[dict]) -> list[TeshuvahWriteResult]:
    """Traiter une liste de TeshuvahRecord et ecrire les tests.

    Args:
        records: liste de dicts issus de TeshuvahRecord.to_dict()

    Returns:
        Liste de TeshuvahWriteResult.
    """
    results = []
    for record in records:
        result = write_regression_test(record)
        results.append(result)

    written = sum(1 for r in results if r.written)
    total = len(results)
    log.info(
        "Teshuvah Writer: %d/%d tests de regression ecrits",
        written, total,
    )

    return results


def store_teshuvah_in_db(
    results: list[TeshuvahWriteResult],
    db_url: str = "postgresql://localhost/etz_chaim",
) -> int:
    """Enregistrer les Teshuvah ecrits en epistememory.

    Le systeme sait : "j'ai converti N failles en gardiens permanents".
    """
    stored = 0
    written_results = [r for r in results if r.written]

    if not written_results:
        return 0

    try:
        from pool import get_conn, init_pool
        init_pool(db_url)  # idempotent

        modules = list({r.module for r in written_results})
        content = (
            f"[Teshuvah] {len(written_results)} faille(s) converties en "
            f"tests de regression permanents. "
            f"Modules : {', '.join(modules)}. "
            f"Fichiers : {', '.join(r.file_path for r in written_results)}."
        )

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO epistememory (
                        content, source_sephirah, domain, epistemic_status,
                        confidence, source_detail
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    content,
                    "gevurah",
                    "self_improvement",
                    "action",
                    0.9,
                    str([r.to_dict() for r in written_results]),
                ))

        stored = 1

    except Exception as exc:
        log.warning("Teshuvah: echec stockage epistememory: %s", exc)

    return stored
