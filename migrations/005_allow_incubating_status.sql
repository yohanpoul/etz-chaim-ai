-- Sprint 8b fix 4 — autoriser le statut 'incubating' dans candidate_insights.
--
-- Contexte : insightforge/core.py:197 pose candidate.status='incubating' pour
-- les candidats dont la novelty est borderline (0.35 <= score < 0.45) — idée
-- d'Ibur : laisser incuber plutôt que rejeter immédiatement. Mais la contrainte
-- CHECK de la table ne l'autorisait pas (valeurs : candidate | validated |
-- rejected | insight | pending) → l'INSERT plantait silencieusement (catch
-- dans save_candidate) ou le candidat n'était jamais persisté (_persist_
-- candidates n'itérait pas sur cette liste).
--
-- Décision : APPROCHE A — ajouter 'incubating' à la contrainte CHECK. La
-- sémantique distincte (borderline en attente de plus d'évidence) mérite un
-- statut propre.
--
-- Source : diagnostic Sprint 8 §5 dette 2.

ALTER TABLE candidate_insights
    DROP CONSTRAINT IF EXISTS candidate_insights_status_check;

ALTER TABLE candidate_insights
    ADD CONSTRAINT candidate_insights_status_check
    CHECK (status IN (
        'candidate',
        'validated',
        'rejected',
        'insight',
        'pending',
        'incubating'
    ));
