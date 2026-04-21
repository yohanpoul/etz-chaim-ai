"""daemon_tasks/binah.py — Binah tasks: confounders, causal graphs, evidence elevator, binah→yesod.

Extracted from daemon.py for modularity.
"""
from __future__ import annotations

import logging
import os

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))
log = logging.getLogger("etz-daemon")


def task_binah_confounders(tree: dict) -> dict:
    """Binah — enrichissement contextuel des claims causaux.

    Pour chaque claim sans confounders contextuels (LLM) :
    1. Demande au LLM des confounders spécifiques à la paire cause/effet
    2. Sauvegarde les nouveaux confounders
    3. Réévalue le evidence_level si possible

    Utilise Assiah (modèle rapide) — c'est du triage haute fréquence.
    """
    report = {
        "task": "binah_confounders",
        "claims_processed": 0,
        "total_new_confounders": 0,
        "evidence_elevated": 0,
        "errors": 0,
    }

    binah = tree.get("binah")
    if not binah:
        report["error"] = "Module binah non disponible"
        return report

    try:
        # Récupérer config Ollama
        from olamot import get_ollama_host, get_model

        get_ollama_host()
        get_model("assiah")  # Modèle rapide pour le triage

        result = binah.run_confounder_enrichment(
            batch_size=40,
            timeout=90,
        )
        report.update(result)

        log.info(
            "Binah confounders: %d claims, %d new confounders, %d elevated, %d errors",
            result["claims_processed"],
            result["total_new_confounders"],
            result["evidence_elevated"],
            result["errors"],
        )

    except Exception as e:
        report["error"] = str(e)
        log.error("Binah confounders error: %s", e)

    return report


def task_binah_causal_graphs(tree: dict) -> dict:
    """Binah — construction du graphe causal global.

    Hashgachah Pratit : chaque cause a un effet, chaque effet une cause.
    Construit le graphe complet, détecte les communautés, trouve les
    causes racines et les chaînes causales (Hishtalshelut).
    """
    report = {
        "task": "binah_causal_graphs",
        "nodes": 0,
        "edges": 0,
        "communities": 0,
        "root_causes": 0,
        "chains": 0,
    }

    binah = tree.get("binah")
    if not binah:
        report["error"] = "Module binah non disponible"
        return report

    try:
        from causalengine.tree_builder import CausalTreeBuilder

        builder = CausalTreeBuilder(binah.db)
        graph = builder.build_graph(min_confidence=0.3)

        report["nodes"] = len(graph.nodes)
        report["edges"] = len(graph.edges)

        if graph.nodes:
            summary = builder.summary()
            report["communities"] = summary.connected_components
            report["root_causes"] = len(summary.top_root_causes)
            report["chains"] = len(summary.longest_chains)
            report["top_roots"] = [
                {"name": name, "out_degree": deg}
                for name, deg in summary.top_root_causes
            ]
            report["top_terminals"] = [
                {"name": name, "in_degree": deg}
                for name, deg in summary.top_terminal_effects
            ]

        log.info(
            "Binah causal graphs: %d nodes, %d edges, %d communities, %d chains",
            report["nodes"], report["edges"],
            report["communities"], report["chains"],
        )

    except Exception as e:
        report["error"] = str(e)
        log.error("Binah causal graphs error: %s", e)

    return report


def task_binah_evidence_elevator(tree: dict) -> dict:
    """Binah — cristallisation des claims causaux.

    Élève les claims au-dessus de correlation_only en croisant
    les données de Hitbonenut, InsightForge, CausalTreeBuilder,
    et DissensuEngine. Cascading : observed → probable → demonstrated.
    """
    report = {
        "task": "binah_evidence_elevator",
        "elevated_to_observed": 0,
        "elevated_to_probable": 0,
        "elevated_to_demonstrated": 0,
        "errors": 0,
    }

    binah = tree.get("binah")
    if not binah:
        report["error"] = "Module binah non disponible"
        return report

    try:
        from causalengine.evidence_elevator import EvidenceElevator

        elevator = EvidenceElevator(
            db=binah.db,
            scorer=binah.evidence_scorer,
            language=binah.language,
        )
        result = elevator.elevate_claims(batch_size=100)
        report.update({
            "elevated_to_observed": result["elevated_to_observed"],
            "elevated_to_probable": result["elevated_to_probable"],
            "elevated_to_demonstrated": result["elevated_to_demonstrated"],
            "errors": result["errors"],
            "before": result.get("before", {}),
            "after": result.get("after", {}),
        })

        total_elevated = (
            result["elevated_to_observed"]
            + result["elevated_to_probable"]
            + result["elevated_to_demonstrated"]
        )
        log.info(
            "Binah elevator: %d elevated (%d observed, %d probable, %d demonstrated)",
            total_elevated,
            result["elevated_to_observed"],
            result["elevated_to_probable"],
            result["elevated_to_demonstrated"],
        )

    except Exception as e:
        report["error"] = str(e)
        log.error("Binah evidence elevator error: %s", e)

    return report


def task_binah_to_yesod(tree: dict) -> dict:
    """Binah → Yesod — Réinjecter les claims causaux dans EpisteMemory.

    בִּינָה → יְסוֹד — La compréhension doit descendre dans la fondation.
    Les causal claims élevés (observed, probable, demonstrated) sont du savoir
    solide qui doit enrichir la mémoire épistémique pour informer les futures
    requêtes. Sans cette boucle, Binah produit du savoir que Yesod ignore.
    """
    report = {
        "task": "binah_to_yesod",
        "claims_read": 0,
        "persisted": 0,
    }
    binah = tree.get("binah")
    yesod = tree.get("yesod")
    if not binah or not yesod:
        report["error"] = "Binah ou Yesod non disponible"
        return report

    try:
        import psycopg2.extras
        from pool import get_conn

        # Lire les claims élevés non encore intégrés dans Yesod.
        # NB schema: causal_claims n'a pas de colonne `domain` (elle vit sur
        # causal_graphs) ni `confounders` (c'est `known_confounders`). Les
        # valeurs evidence_level sont également longues ('probable_causation'
        # pas 'probable'). Un drift historique causait
        # `column "domain" does not exist` (Sprint megaclean T2 / Dette 7).
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT cc.id, cc.cause, cc.effect, cc.evidence_level,
                           cg.domain,
                           cc.known_confounders, cc.direction_verified
                    FROM causal_claims cc
                    LEFT JOIN causal_graphs cg ON cc.graph_id = cg.id
                    WHERE cc.evidence_level IN (
                              'observed_association',
                              'probable_causation',
                              'demonstrated_causation'
                          )
                      AND cc.id NOT IN (
                          SELECT CAST(source_detail->>'causal_claim_id' AS uuid)
                          FROM epistememory
                          WHERE source_detail->>'causal_claim_id' IS NOT NULL
                      )
                    ORDER BY cc.created_at DESC
                    LIMIT 500
                """)
                claims = cur.fetchall()

        report["claims_read"] = len(claims)

        for claim in claims:
            try:
                content = (
                    f"[Causal {claim['evidence_level']}] "
                    f"{claim['cause']} → {claim['effect']}"
                )
                if claim.get("known_confounders"):
                    content += f" (confounders: {', '.join(claim['known_confounders'][:3])})"

                confidence_map = {
                    "observed_association": 0.6,
                    "probable_causation": 0.75,
                    "demonstrated_causation": 0.9,
                }

                yesod.remember(
                    content=content,
                    source_sephirah="binah",
                    confidence=confidence_map.get(claim["evidence_level"], 0.5),
                    domain=claim.get("domain") or "causal",
                    tags=["causal_claim", claim["evidence_level"]],
                    source_detail={"causal_claim_id": str(claim["id"])},
                )
                report["persisted"] += 1
            except Exception as e:
                log.warning("Binah→Yesod persist %s: %s", claim["id"], e)

        log.info(
            "Binah→Yesod: %d claims lus, %d persistés dans EpisteMemory",
            report["claims_read"], report["persisted"],
        )

    except Exception as e:
        report["error"] = str(e)
        log.error("Binah→Yesod error: %s", e)

    return report
