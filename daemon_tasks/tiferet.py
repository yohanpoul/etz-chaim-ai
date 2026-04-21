"""daemon_tasks/tiferet.py — Tiferet tasks: contradictions, synthesize.

Extracted from daemon.py for modularity.
"""
from __future__ import annotations

import logging

log = logging.getLogger("etz-daemon")


def task_contradictions(tree: dict) -> dict:
    """Tiferet — Détecter les contradictions PAR DOMAINE (pas globalement).

    Évite l'explosion O(n²) en ne comparant que les conclusions du même domaine.
    Après détection, le TikkunScheduler vérifie si une synthèse réactive est nécessaire.
    """
    report = {"task": "contradictions", "tensions": 0, "health": "unknown", "domains": 0}
    tiferet = tree.get("tiferet")
    if not tiferet:
        report["error"] = "DissensuEngine non disponible"
        return report

    try:
        import psycopg2.extras
        from dissensuengine.tikkun_scheduler import TikkunScheduler

        # Récupérer les domaines distincts
        with tiferet.db._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT DISTINCT domain FROM dissensuengine_conclusions
                   WHERE domain IS NOT NULL ORDER BY domain"""
            )
            domains = [row["domain"] for row in cur.fetchall()]

        worst_health = "consistent"
        health_priority = {"consistent": 0, "tensions_detected": 1, "highly_divergent": 2}

        for domain in domains:
            consistency = tiferet.analyze_consistency(domain=domain)
            if health_priority.get(consistency.health, 0) > health_priority.get(worst_health, 0):
                worst_health = consistency.health

        # Count réel depuis la DB (tensions ouvertes uniquement)
        with tiferet.db._cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM dissensuengine_tensions WHERE resolution_status = 'open'"
            )
            report["tensions"] = cur.fetchone()[0]

        report["health"] = worst_health
        report["domains"] = len(domains)

        open_qs = tiferet.db.get_open_questions()
        report["open_questions"] = len(open_qs)

        diag = tiferet.self_diagnose(quick=True)
        report["diagnosis"] = diag.get("level", "unknown")

        # TikkunScheduler — synthèse réactive si tensions dépassent le seuil
        scheduler = TikkunScheduler(tiferet.db)
        reactive_syntheses = 0
        for domain in domains:
            if scheduler.should_synthesize_now(domain):
                try:
                    syn = tiferet.synthesize_or_dissent(domain=domain)
                    reactive_syntheses += 1
                    log.info(
                        "TikkunScheduler: synthèse réactive pour %s → %s",
                        domain, syn.mode,
                    )
                except Exception as e:
                    log.warning("TikkunScheduler reactive error for %s: %s", domain, e)
        report["reactive_syntheses"] = reactive_syntheses

        log.info(
            "Tiferet: %d tensions across %d domains, health=%s, reactive=%d",
            report["tensions"], len(domains), worst_health, reactive_syntheses,
        )
    except Exception as e:
        report["error"] = str(e)
        log.error("Contradictions error: %s", e)

    return report


def task_tiferet_synthesize(tree: dict) -> dict:
    """Tiferet — Récolter conclusions et tenter synthèses.

    Hitkalelut entre Chesed (accueillir toutes les sources)
    et Gevurah (rejeter les incohérences).

    Étapes :
    1. Récolter conclusions depuis EpisteMemory, FailureToInsight, InsightForge
    2. Analyser cohérence par domaine
    3. Tenter synthèse ou dissensus par domaine (seulement ceux avec données fraîches)
    """
    import psycopg2.extras

    report = {
        "task": "tiferet_synthesize",
        "harvested": 0,
        "syntheses": 0,
        "dissensus": 0,
        "domains_processed": 0,
    }

    tiferet = tree.get("tiferet")
    if not tiferet:
        report["error"] = "DissensuEngine non disponible"
        return report

    try:
        # --- Étape 1 : Récolter conclusions (dédup par source_label) ---

        existing_labels = {
            c.source_label for c in tiferet.db.get_all_conclusions()
        }
        harvested = 0
        domains_with_new = set()

        # Mapping sephirah → source_type (contrainte CHECK de la table)
        SEPHIRAH_TO_TYPE = {
            "chesed": "model",
            "chokmah": "model",
            "hod": "system",
            "gevurah": "system",
            "netzach": "system",
            "malkuth": "human",
            "external": "human",
        }

        # A. EpisteMemory — max 10 entrées/domaine, les plus confiantes
        with tiferet.db._cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute("""
                SELECT id, content, source_sephirah, domain, confidence
                FROM epistememory
                WHERE epistemic_status != 'deprecated'
                  AND domain IS NOT NULL
                  AND length(content) > 50
                  AND source_sephirah != 'tiferet'
                ORDER BY domain, confidence DESC
            """)

            by_domain: dict[str, list] = {}
            for row in cur.fetchall():
                d = row["domain"]
                if d not in by_domain:
                    by_domain[d] = []
                if len(by_domain[d]) < 10:
                    by_domain[d].append(row)

            for domain, entries in by_domain.items():
                if len(entries) < 2:
                    continue
                for entry in entries:
                    label = f"em:{entry['id']}"
                    if label in existing_labels:
                        continue
                    src_type = SEPHIRAH_TO_TYPE.get(
                        entry["source_sephirah"], "system"
                    )
                    tiferet.submit_conclusion(
                        content=entry["content"][:500],
                        source_label=label,
                        source_type=src_type,
                        domain=domain,
                        confidence=entry["confidence"],
                        metadata={"epistememory_id": str(entry["id"])},
                    )
                    existing_labels.add(label)
                    domains_with_new.add(domain)
                    harvested += 1

        # B. FailureToInsight insights
        with tiferet.db._cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute("""
                SELECT id, content, insight_type, confidence, domain
                FROM failuretoinsight_insights
            """)
            for row in cur.fetchall():
                label = f"fti:{row['id']}"
                if label in existing_labels:
                    continue
                tiferet.submit_conclusion(
                    content=row["content"][:500],
                    source_label=label,
                    source_type="system",
                    domain=row.get("domain") or "failure_analysis",
                    confidence=row["confidence"],
                    metadata={
                        "fti_id": str(row["id"]),
                        "insight_type": row["insight_type"],
                    },
                )
                existing_labels.add(label)
                domains_with_new.add(row.get("domain") or "failure_analysis")
                harvested += 1

        # C. Candidate insights validés (InsightForge)
        with tiferet.db._cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute("""
                SELECT id, description, source_module, domain, confidence
                FROM candidate_insights
                WHERE status IN ('validated', 'insight')
            """)
            for row in cur.fetchall():
                label = f"ci:{row['id']}"
                if label in existing_labels:
                    continue
                tiferet.submit_conclusion(
                    content=row["description"][:500],
                    source_label=label,
                    source_type="model",
                    domain=row.get("domain") or "insights",
                    confidence=row["confidence"],
                    metadata={
                        "candidate_id": str(row["id"]),
                        "source_module": row["source_module"],
                    },
                )
                existing_labels.add(label)
                domains_with_new.add(row.get("domain") or "insights")
                harvested += 1

        report["harvested"] = harvested

        # --- Étape 2+3 : Synthèse par domaine, priorisée par TikkunScheduler ---

        from dissensuengine.tikkun_scheduler import TikkunScheduler

        scheduler = TikkunScheduler(tiferet.db)
        tohu_state = scheduler.assess_tohu_state()
        priority_domains = scheduler.schedule_tikkun(
            {d: s for d, s in tohu_state.items() if s.needs_tikkun}
        )

        # Domaines prioritaires d'abord, puis les domaines avec nouvelles données
        ordered_domains = list(dict.fromkeys(priority_domains + sorted(domains_with_new)))

        syntheses_count = 0
        dissensus_count = 0
        domain_errors = []

        for domain in ordered_domains:
            domain_concs = tiferet.db.get_all_conclusions(domain=domain)
            if len(domain_concs) < 2:
                continue

            try:
                syn = tiferet.synthesize_or_dissent(domain=domain)
                if syn.mode == "synthesis":
                    syntheses_count += 1
                else:
                    dissensus_count += 1
            except Exception as e:
                domain_errors.append(f"{domain}: {e}")
                log.warning("Tiferet synthesis error for domain %s: %s", domain, e)

        report["syntheses"] = syntheses_count
        report["dissensus"] = dissensus_count
        report["domains_processed"] = len(domains_with_new)
        report["total_conclusions"] = len(
            tiferet.db.get_all_conclusions()
        )
        if domain_errors:
            report["domain_errors"] = domain_errors[:10]

        log.info(
            "Tiferet synthesize: harvested=%d, syntheses=%d, dissensus=%d, domains=%d",
            harvested, syntheses_count, dissensus_count, len(domains_with_new),
        )

    except Exception as e:
        report["error"] = str(e)
        log.error("Tiferet synthesize error: %s", e)

    return report
