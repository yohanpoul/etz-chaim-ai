"""23e sentier — Lamed (ל) — Gevurah → Tiferet — FailureToInsight.

Lettre simple : sens = mouvement/apprentissage.
LE SENTIER CRITIQUE. La seule lettre qui dépasse la ligne.
Transformer le jugement (Gevurah) en compréhension (Tiferet).
Apprendre des échecs — le Birur qui extrait les Nitzotzot des Klipot.

Wrapper autour de FailureToInsight.analyze_failure() + extract_nitzotzot().

Correspondances SY (Gra) :
  Sens : mouvement/apprentissage (hilukh/limud) — la tour d'étude
  Zodiaque : Balance (Moznayim) — Mois : Tishrei — Direction : sud-ouest
  Organe : vésicule biliaire (marah) — l'amertume qui enseigne
  Lamed = le bâton de l'enseignant qui monte au-dessus de la ligne.
  Seule lettre qui transcende l'espace d'écriture — l'apprentissage
  transcende toutes les bornes. Tishrei = Rosh HaShanah, le jugement
  qui ouvre l'année — et Yom Kippour, le retour.
  La vésicule sécrète la bile : l'amertume de l'échec DIGÈRE la Qliphah.
  Yetzirah : learning_rate=0.9, extraction_power=0.9, adaptability=0.8,
  bitterness_tolerance=0.9, transcendence=0.8
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Lamed(Sentier):
    name = "FailureToInsight"
    letter = "ל"
    letter_name = "lamed"
    number = 23
    source = "gevurah"
    target = "tiferet"
    letter_type = "simple"
    sense = "mouvement/apprentissage"
    description = "Transformer l'échec en insight — le Birur, extraction des Nitzotzot"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Lamed extrait les motifs de rejet pour nourrir Tiferet.

        Condition : ctx contient des rejets Gevurah (autojudge_rejections
        ou gevurah_feedback avec items rejetés).
        Effet : extraction des patterns de rejet → ctx_additions['rejection_patterns'].
        Tiferet peut s'en servir pour sa synthèse dialectique.

        Le Lamed monte au-dessus de la ligne — il transcende le jugement
        pour en extraire l'apprentissage. La vésicule biliaire digère l'amertume.
        """
        # Chercher les rejets dans le ctx
        rejections = ctx.get("autojudge_rejections", [])
        gevurah_feedback = ctx.get("gevurah_feedback", {})

        # Aussi : si le chemin Teth a filtré des items
        teth_filtered = ctx.get("teth_filtered_count", 0)

        if not rejections and not gevurah_feedback and teth_filtered == 0:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        patterns = []

        # Extraire les motifs de chaque rejet
        for rej in rejections:
            reason = rej.get("reason", "") if isinstance(rej, dict) else str(rej)
            if reason:
                patterns.append(reason[:200])

        # Rejets du feedback Gevurah
        if isinstance(gevurah_feedback, dict):
            for key, val in gevurah_feedback.items():
                if isinstance(val, dict) and val.get("passed") is False:
                    patterns.append(f"{key}: score={val.get('score', '?')}")

        # Si Teth a filtré des items, c'est un signal
        if teth_filtered > 0:
            patterns.append(f"Teth a filtré {teth_filtered} exploration(s) faible(s)")

        if patterns:
            return {
                "ctx_additions": {
                    "rejection_patterns": patterns,
                    "lamed_active": True,
                },
                "module_modifiers": {},
                "warnings": [],
                "applied": True,
            }
        return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

    def run(self, tree: dict, **kwargs) -> SentierResult:
        description = kwargs.get("description", "")
        source_type = kwargs.get("source_type", "external")
        source_id = kwargs.get("source_id")
        context = kwargs.get("context")
        domain = kwargs.get("domain")
        extract = kwargs.get("extract", True)

        if not description:
            result = SentierResult(
                sentier=self.name, letter=self.letter,
                source=self.source, target=self.target,
                success=False, message="Pas de description d'échec à analyser",
            )
            return self.enrich_result(result)

        (gevurah,) = self._require(tree, "gevurah")

        # ── Modificateurs du Lamed — la tour qui transcende ─────
        mods = self.yetzirah_modifiers()
        learning_rate = mods.get("learning_rate", 0.5)
        extraction_power = mods.get("extraction_power", 0.5)
        bitterness_tolerance = mods.get("bitterness_tolerance", 0.5)
        transcendence = mods.get("transcendence", 0.5)

        # Accéder au module FailureToInsight via Gevurah
        fti = getattr(gevurah, "fti", None) or getattr(gevurah, "failure_to_insight", None)
        if fti is None:
            # Chercher dans l'arbre directement
            fti = tree.get("failuretoinsight") or tree.get("fti")
        if fti is None:
            result = SentierResult(
                sentier=self.name, letter=self.letter,
                source=self.source, target=self.target,
                success=False, message="Module FailureToInsight non accessible",
            )
            return self.enrich_result(result)

        # Étape 1 : Analyser l'échec — classifier la Qliphah
        # La vésicule biliaire digère l'amertume : bitterness_tolerance=0.9
        # → même les échecs sévères sont acceptés pour analyse
        analysis = fti.analyze_failure(
            description=description,
            source_type=source_type,
            source_id=source_id,
            context=context,
            domain=domain,
            qliphah_override=kwargs.get("qliphah"),
            severity_override=kwargs.get("severity"),
        )

        data = {
            "analysis_id": str(analysis.id),
            "qliphah": analysis.qliphah if hasattr(analysis, "qliphah") else "unknown",
            "severity": analysis.severity if hasattr(analysis, "severity") else "unknown",
            "root_cause": analysis.root_cause if hasattr(analysis, "root_cause") else None,
        }

        # Étape 2 : Extraire les Nitzotzot — les étincelles de sagesse dans l'échec
        # extraction_power=0.9 → le Lamed monte au-dessus de la ligne,
        # il extrait même les étincelles enfouies profondément dans la Qliphah
        if extract:
            nitzotzot = fti.extract_nitzotzot(
                analysis_id=analysis.id,
                insights_data=kwargs.get("insights_data"),
            )

            # Filtrage par extraction_power : seuil de confiance abaissé
            # Plus l'extraction est puissante, plus on accepte des nitzotzot faibles
            # extraction_power=0.9 → min_conf = 0.1 * (1 - 0.9) = 0.01
            min_conf = 0.1 * (1 - extraction_power)

            extracted = []
            for n in nitzotzot:
                conf = n.confidence if hasattr(n, "confidence") else 0.0
                entry = {
                    "content": n.content if hasattr(n, "content") else str(n),
                    "insight_type": n.insight_type if hasattr(n, "insight_type") else "unknown",
                    "confidence": conf,
                }
                if conf >= min_conf:
                    # learning_rate=0.9 → boost de confiance pour les insights retenus
                    # Le Lamed apprend vite : chaque étincelle extraite est amplifiée
                    entry["boosted_confidence"] = min(1.0, conf * (1 + learning_rate * 0.3))
                    extracted.append(entry)

            data["nitzotzot"] = extracted
            data["n_nitzotzot"] = len(extracted)
            data["n_raw"] = len(nitzotzot)
            data["lamed_extraction_power"] = extraction_power
            data["lamed_min_confidence"] = min_conf

            # Transcendence : si l'échec est sévère MAIS que des nitzotzot sont trouvés,
            # le Lamed transcende — il dépasse la ligne, il transforme le jugement
            severity = data["severity"]
            if data["n_nitzotzot"] > 0 and severity in ("critical", "high"):
                data["transcendence_active"] = True
                data["transcendence_level"] = transcendence
                msg = (
                    f"Lamed(ל) TRANSCENDE : {data['qliphah']}({severity}) → "
                    f"{data['n_nitzotzot']} Nitzotz(ot) extraits "
                    f"(puissance={extraction_power:.1f}, transcendance={transcendence:.1f})"
                )
            else:
                data["transcendence_active"] = False
                msg = (
                    f"Birur(ל) : {data['qliphah']}({severity}) → "
                    f"{data['n_nitzotzot']}/{data['n_raw']} Nitzotz(ot) retenus "
                    f"(seuil={min_conf:.2f})"
                )
        else:
            data["nitzotzot"] = []
            data["n_nitzotzot"] = 0
            # bitterness_tolerance=0.9 → même sans extraction, on note
            # que la bile a absorbé l'amertume pour usage futur
            data["bile_absorbed"] = bitterness_tolerance
            msg = (
                f"Qliphah={data['qliphah']}, sévérité={data['severity']} "
                f"— bile absorbée ({bitterness_tolerance:.1f}), extraction différée"
            )

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data, message=msg,
        )
        return self.enrich_result(result)
