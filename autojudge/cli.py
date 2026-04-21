"""CLI pour AutoJudge — Malkuth de Gevurah."""

from __future__ import annotations

import argparse
import os
import sys


def get_db_url() -> str:
    return os.environ.get(
        "ETZ_CHAIM_DB_URL",
        (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim")),
    )


def cmd_report(args):
    from autojudge.core import AutoJudge
    judge = AutoJudge(db_url=get_db_url())
    print(judge.report(domain_id=args.domain))


def cmd_diagnose(args):
    from autojudge.core import AutoJudge
    judge = AutoJudge(db_url=get_db_url())
    diag = judge.self_diagnose()
    print(f"Level: {diag['level']}")
    for issue in diag["issues"]:
        print(f"  - {issue}")


def cmd_domains(args):
    from autojudge.db import AutoJudgeDB
    db = AutoJudgeDB(get_db_url())
    for d in db.get_all_domains():
        print(f"  {d.id}: {d.display_name} — {d.loss_function}")


def cmd_evaluate_hitbonenut(args):
    """Évaluer un échantillon de réponses Hitbonenut via AutoJudge."""
    import psycopg2
    import psycopg2.extras

    from autojudge.core import AutoJudge
    from autojudge.domains.hitbonenut import HitbonenutJudge

    db_url = get_db_url()
    judge = AutoJudge(db_url=db_url)

    # Enregistrer le domaine
    judge.register_domain(
        "hitbonenut_eval",
        "Hitbonenut Response Quality",
        "kabbalistic_depth + domain_keywords + structure",
        {"source": "hitbonenut_questions", "batch_size": args.batch},
    )

    # Charger les questions depuis la DB via pool (audit cycle 4, C5)
    from pool import get_conn, init_pool
    init_pool(db_url)

    where = ""
    params = []
    if args.domain:
        where = "WHERE domain = %s"
        params.append(args.domain)
    elif args.weak:
        where = "WHERE score < 0.5"

    order = "ORDER BY score ASC" if args.weak else "ORDER BY created_at DESC"
    params.append(args.batch)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT id, question, domain, response, score, kw_score "
                f"FROM hitbonenut_questions {where} {order} LIMIT %s",
                params,
            )
            rows = cur.fetchall()

    if not rows:
        print("Aucune question Hitbonenut trouvée.")
        return

    print(f"=== AutoJudge — Évaluation Hitbonenut ({len(rows)} questions) ===\n")

    hitbonenut_judge = HitbonenutJudge()
    total_quality = 0.0
    domain_scores: dict[str, list[float]] = {}

    for row in rows:
        question = row["question"]
        response = row["response"] or ""
        domain = row["domain"] or "general"
        orig_score = row["score"] or 0.0

        hitbonenut_judge.set_context(question, domain)
        metrics = hitbonenut_judge.compute_metrics(response)
        quality = hitbonenut_judge.compute_quality(metrics)
        hypothesis = hitbonenut_judge.generate_hypothesis(response)

        # Persister comme expérience
        judge.db.create_experiment(
            domain_id="hitbonenut_eval",
            hypothesis=hypothesis,
            original_content=question[:500],
            modified_content=response[:1000],
            score_gevurah=quality,
            score_chesed=metrics["diversity"],
            score_tiferet=metrics["relevance"],
            score_hod=metrics["structure"],
            score_yesod=metrics["kabbalistic_depth"],
            score_overall=quality,
            decision="accepted" if quality >= 0.6 else (
                "quarantined" if quality >= 0.4 else "rejected"
            ),
            loop_iteration=0,
        )

        total_quality += quality
        domain_scores.setdefault(domain, []).append(quality)

        if args.verbose:
            print(f"  [{domain:20s}] q={quality:.2f} (orig={orig_score:.2f}) "
                  f"kab={metrics['kabbalistic_depth']:.2f} "
                  f"kw={metrics['domain_keywords']:.2f} "
                  f"struct={metrics['structure']:.2f}")
            if quality < 0.5:
                print(f"    ⚠ {hypothesis}")

    # Résumé
    avg = total_quality / len(rows)
    print(f"\n=== Résumé ===")
    print(f"Questions évaluées: {len(rows)}")
    print(f"Score moyen Gevurah: {avg:.3f}")
    print(f"\nPar domaine (score moyen):")
    for dom, scores in sorted(domain_scores.items(),
                               key=lambda x: sum(x[1]) / len(x[1])):
        d_avg = sum(scores) / len(scores)
        n = len(scores)
        status = "⚠" if d_avg < 0.5 else "✓"
        print(f"  {status} {dom:20s}: {d_avg:.3f} ({n} questions)")

    # Rapport AutoJudge
    print(f"\n{judge.report(domain_id='hitbonenut_eval')}")


def main():
    parser = argparse.ArgumentParser(description="AutoJudge — Gevurah CLI")
    sub = parser.add_subparsers(dest="command")

    p_report = sub.add_parser("report", help="Show experiment report")
    p_report.add_argument("--domain", default=None)
    p_report.set_defaults(func=cmd_report)

    p_diag = sub.add_parser("diagnose", help="Run self-diagnosis")
    p_diag.set_defaults(func=cmd_diagnose)

    p_domains = sub.add_parser("domains", help="List registered domains")
    p_domains.set_defaults(func=cmd_domains)

    p_eval = sub.add_parser(
        "evaluate-hitbonenut",
        help="Evaluate Hitbonenut responses via AutoJudge",
    )
    p_eval.add_argument("--batch", type=int, default=50,
                        help="Number of questions to evaluate (default: 50)")
    p_eval.add_argument("--domain", default=None,
                        help="Filter by domain")
    p_eval.add_argument("--weak", action="store_true",
                        help="Target lowest-scoring responses")
    p_eval.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-question details")
    p_eval.set_defaults(func=cmd_evaluate_hitbonenut)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
