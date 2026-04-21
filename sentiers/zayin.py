"""18e sentier — Zayin (ז) — Binah ↔ Tiferet — AnalysisResults.

Lettre simple : sens = odorat (re'iach).
Les résultats d'analyse causale de Binah sont transmis à Tiferet pour
intégration dans la synthèse. Le flair qui détecte l'invisible —
l'anomalie subtile, le signal faible.

Zayin = l'arme (zayin), l'instrument tranchant de la discrimination.

Correspondances SY (Gra) :
  Sens : odorat (re'iach) — le flair subtil
  Zodiaque : Gémeaux (Te'omim) — Mois : Sivan — Direction : est-haut
  Organe : pied droit (regel yemin)
  Yetzirah : anomaly_detection=0.9, subtlety_sensitivity=0.9,
  discrimination=0.8, distance_sensing=0.7
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Zayin(Sentier):
    name = "AnalysisResults"
    letter = "ז"
    letter_name = "zayin"
    number = 18
    source = "binah"
    target = "tiferet"
    letter_type = "simple"
    sense = "odorat"
    description = "Transmettre l'analyse causale — le flair qui détecte les anomalies"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Zayin flaire les anomalies — signale les incohérences causales.

        Condition : daemon_enrichment avec binah_causal ET tiferet_syntheses.
        Effet : si les deux divergent, warning de friction Binah↔Tiferet.
        Le flair du Zayin détecte l'invisible — l'anomalie subtile.
        """
        enrichment = ctx.get("daemon_enrichment", {})
        causal = enrichment.get("binah_causal", [])
        syntheses = enrichment.get("tiferet_syntheses", [])

        if not causal and not syntheses:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        warnings = []
        additions = {"zayin_analysis_available": True}

        # Anomalie : des claims causaux existent mais aucune synthèse ne les intègre
        if causal and not syntheses:
            warnings.append(
                "Zayin(ז) : claims causaux non synthétisés — "
                "l'analyse Binah n'a pas encore été intégrée par Tiferet"
            )
            additions["zayin_unsynthesized_claims"] = True

        return {
            "ctx_additions": additions,
            "module_modifiers": {},
            "warnings": warnings,
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        domain = kwargs.get("domain")
        analysis_ids = kwargs.get("analysis_ids")
        detect_anomalies = kwargs.get("detect_anomalies", True)

        (binah, tiferet) = self._require(tree, "binah", "tiferet")

        # ── Modificateurs du flair ───────────────────────────
        mods = self.yetzirah_modifiers()
        anomaly_detection = mods.get("anomaly_detection", 0.9)
        subtlety_sensitivity = mods.get("subtlety_sensitivity", 0.9)
        discrimination = mods.get("discrimination", 0.8)

        data = {"domain": domain}

        # Étape 1 : Récupérer les résultats d'analyse de Binah
        if hasattr(binah, "get_analysis_results"):
            results = binah.get_analysis_results(
                domain=domain,
                analysis_ids=analysis_ids,
            )
        elif hasattr(binah, "get_results"):
            results = binah.get_results(domain=domain)
        elif hasattr(binah, "analyze"):
            results = binah.analyze(domain=domain)
        else:
            results = None

        if results is not None:
            if isinstance(results, (list, tuple)):
                data["n_results"] = len(results)
                data["results_summary"] = [str(r)[:100] for r in results[:10]]
            else:
                data["n_results"] = 1
                data["results_summary"] = str(results)[:300]
        else:
            data["n_results"] = 0
            data["results_summary"] = []

        # Étape 2 : Détection d'anomalies — le flair de Zayin
        # anomaly_detection=0.9 → sensibilité maximale aux signaux faibles
        anomalies = []
        if detect_anomalies and results is not None:
            if hasattr(binah, "detect_anomalies"):
                raw_anomalies = binah.detect_anomalies(
                    results=results,
                    sensitivity=subtlety_sensitivity,
                )
                anomalies = list(raw_anomalies) if raw_anomalies else []
            # Le flair discrimine — discrimination=0.8
            # Filtrer les faux positifs par seuil de discrimination
            if anomalies:
                filtered_anomalies = []
                for a in anomalies:
                    confidence = a.confidence if hasattr(a, "confidence") else 0.5
                    if confidence >= (1 - discrimination) * 0.5:
                        filtered_anomalies.append({
                            "description": str(a)[:150],
                            "confidence": round(confidence, 2),
                        })
                anomalies = filtered_anomalies

        data["n_anomalies"] = len(anomalies)
        data["anomalies"] = anomalies[:5]

        # Étape 3 : Transmettre à Tiferet pour synthèse
        transmitted = False
        if results is not None:
            if hasattr(tiferet, "receive_analysis"):
                tiferet.receive_analysis(
                    results=results,
                    domain=domain,
                    source="binah",
                    anomalies=anomalies if anomalies else None,
                )
                transmitted = True
            elif hasattr(tiferet, "receive"):
                tiferet.receive(data=results, source="binah", domain=domain)
                transmitted = True

        data["transmitted"] = transmitted
        data["zayin_discrimination"] = discrimination

        parts = [f"Flair(ז) — {data['n_results']} résultat(s) de Binah"]
        if anomalies:
            parts.append(f"{len(anomalies)} anomalie(s) détectée(s)")
        parts.append(f"transmis={'oui' if transmitted else 'non'}")

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            data=data, message=" — ".join(parts),
        )
        return self.enrich_result(result)
