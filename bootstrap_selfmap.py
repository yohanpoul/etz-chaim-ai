#!/usr/bin/env python3
"""Bootstrap SelfMap scores from hitbonenut_questions data.

Résout le problème des 44 domaines à score 0.0 dans selfmap_competence.

Cause racine : eval_domain() écrasait les scores EMA accumulés par Hitbonenut.
Ce script restaure les scores à partir des données hitbonenut existantes.

Stratégie :
  1. Lire les avg(score) par domaine depuis hitbonenut_questions
  2. Calculer un score bootstrap : min(avg * coverage_factor, 0.5)
     où coverage_factor = min(n_questions / 200, 1.0)
  3. Ne mettre à jour QUE les domaines dont le score actuel < score bootstrap
  4. Nettoyer les domaines composés parasites (contenant '+')

Usage :
  python bootstrap_selfmap.py              # dry-run (affiche sans écrire)
  python bootstrap_selfmap.py --apply      # applique les changements
  python bootstrap_selfmap.py --apply --clean-compounds  # + nettoyage composés
"""

import argparse
import sys

import psycopg2
import psycopg2.extras


DB = "dbname=etz_chaim"
from olamot import get_model
MODEL_ID = get_model("yetzirah")
MAX_BOOTSTRAP_SCORE = 0.5
COVERAGE_DENOMINATOR = 200  # n >= 200 → coverage_factor = 1.0


def get_hitbonenut_stats(cur) -> list[dict]:
    """Lire les statistiques hitbonenut par domaine."""
    cur.execute("""
        SELECT domain,
               count(*) as n,
               avg(score)::float as avg_score,
               count(*) FILTER (WHERE score > 0) as n_positive
        FROM hitbonenut_questions
        GROUP BY domain
        ORDER BY count(*) DESC
    """)
    return [dict(r) for r in cur.fetchall()]


def get_current_scores(cur) -> dict[str, dict]:
    """Lire les scores selfmap actuels."""
    cur.execute("""
        SELECT domain, score, n_evals
        FROM selfmap_competence
        WHERE model_id = %s
    """, (MODEL_ID,))
    return {r["domain"]: dict(r) for r in cur.fetchall()}


def get_compound_domains(cur) -> list[str]:
    """Identifier les domaines composés parasites."""
    cur.execute("""
        SELECT domain FROM selfmap_competence
        WHERE domain LIKE '%%+%%'
        AND model_id = %s
    """, (MODEL_ID,))
    return [r["domain"] for r in cur.fetchall()]


def compute_bootstrap_score(avg_score: float, n_questions: int) -> float:
    """Calculer le score bootstrap.

    Formula : min(avg_score * coverage_factor, MAX_BOOTSTRAP_SCORE)
    coverage_factor = min(n_questions / COVERAGE_DENOMINATOR, 1.0)
    """
    coverage_factor = min(n_questions / COVERAGE_DENOMINATOR, 1.0)
    return min(avg_score * coverage_factor, MAX_BOOTSTRAP_SCORE)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap SelfMap scores")
    parser.add_argument("--apply", action="store_true", help="Appliquer les changements (sinon dry-run)")
    parser.add_argument("--clean-compounds", action="store_true", help="Supprimer les domaines composés")
    args = parser.parse_args()

    # Pool avec autocommit=False pour transaction explicite (audit C5)
    from pool import get_conn, init_pool
    init_pool(DB)
    _conn_ctx = get_conn(autocommit=False)
    conn = _conn_ctx.__enter__()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ── 1. Données hitbonenut ──
        hitbonenut_stats = get_hitbonenut_stats(cur)
        current_scores = get_current_scores(cur)

        print("=" * 70)
        print("BOOTSTRAP SELFMAP — ANALYSE")
        print("=" * 70)
        print(f"\nDomaines hitbonenut : {len(hitbonenut_stats)}")
        print(f"Domaines selfmap    : {len(current_scores)}")

        # ── 2. Calculer les bootstrap scores ──
        updates = []
        for stat in hitbonenut_stats:
            domain = stat["domain"]
            bootstrap = compute_bootstrap_score(stat["avg_score"], stat["n"])
            current = current_scores.get(domain, {}).get("score", None)

            if current is not None and current < bootstrap:
                updates.append({
                    "domain": domain,
                    "bootstrap_score": round(bootstrap, 4),
                    "current_score": current,
                    "hitbonenut_avg": round(stat["avg_score"], 3),
                    "hitbonenut_n": stat["n"],
                })

        print(f"\nDomaines à mettre à jour : {len(updates)}")
        print()
        print(f"{'Domaine':<25} {'Actuel':>8} {'→ Bootstrap':>12} {'Hitb avg':>10} {'Hitb n':>8}")
        print("-" * 70)
        for u in updates:
            print(f"{u['domain']:<25} {u['current_score']:>8.3f} → {u['bootstrap_score']:>8.4f}"
                  f"    {u['hitbonenut_avg']:>8.3f} {u['hitbonenut_n']:>8d}")

        # ── 3. Domaines composés ──
        compounds = get_compound_domains(cur)
        if compounds:
            print(f"\n{'=' * 70}")
            print(f"DOMAINES COMPOSÉS PARASITES : {len(compounds)}")
            print("-" * 70)
            for c in compounds:
                print(f"  {c}")

        # ── 4. Appliquer ──
        if not args.apply:
            print(f"\n{'=' * 70}")
            print("DRY-RUN — aucun changement. Relancer avec --apply pour écrire.")
            conn.rollback()
            return

        # Appliquer les bootstrap scores
        updated_count = 0
        for u in updates:
            cur.execute("""
                UPDATE selfmap_competence
                SET score = %s, updated_at = NOW()
                WHERE domain = %s AND model_id = %s AND score < %s
            """, (u["bootstrap_score"], u["domain"], MODEL_ID, u["bootstrap_score"]))
            updated_count += cur.rowcount

        print(f"\n✓ {updated_count} domaines mis à jour")

        # Nettoyer les composés
        if args.clean_compounds and compounds:
            cur.execute("""
                DELETE FROM selfmap_competence
                WHERE domain LIKE '%%+%%' AND model_id = %s
            """, (MODEL_ID,))
            print(f"✓ {cur.rowcount} domaines composés supprimés")

        conn.commit()

        # ── 5. Vérification ──
        print(f"\n{'=' * 70}")
        print("ÉTAT APRÈS BOOTSTRAP")
        print("-" * 70)
        cur.execute("""
            SELECT domain, score, n_evals
            FROM selfmap_competence
            WHERE model_id = %s
            ORDER BY score DESC, domain
        """, (MODEL_ID,))

        zero_count = 0
        for row in cur.fetchall():
            marker = " ←" if row["score"] == 0 else ""
            if row["score"] == 0:
                zero_count += 1
            print(f"  {row['domain']:<35} {row['score']:>8.4f}  (n={row['n_evals']}){marker}")

        print(f"\nDomaines encore à 0 : {zero_count}")

    except Exception as e:
        conn.rollback()
        print(f"ERREUR : {e}", file=sys.stderr)
        raise
    finally:
        cur.close()
        _conn_ctx.__exit__(None, None, None)


if __name__ == "__main__":
    main()
