# ADR-001 — Vocabulaire des statuts d'insight

**Date** : 2026-04-19
**Statut** : Accepté
**Sprint** : 8b (diagnostic Sprint 8 §5 dette 4)

## Contexte

La table `candidate_insights` (Chokmah / InsightForge) porte une colonne
`status` avec une contrainte CHECK explicite. Historiquement, plusieurs
audits, requêtes SQL, dashboards, et métriques du daemon parlent d'un
statut `'accepted'` qui **n'existe pas** dans le schéma. Le statut de
succès réel est `'insight'`.

Le diagnostic Sprint 8 a exposé le problème :
- SQL d'audit cherchait `WHERE status = 'accepted'` → 0 lignes.
- `daemon_tasks/tzimtzum.py:249` utilise `count(*) FILTER (WHERE status = 'accepted')` pour la métrique `insights_accepted` alimentée au régulateur Tzimtzum → métrique toujours 0.
- Dashboards et docs utilisent "accepted" indifféremment pour signaler "validé".

## Décision

1. **Statut canonique** : le statut de succès dans `candidate_insights` est `'insight'`. Après Sprint 8b, la contrainte CHECK autorise :
   ```
   status IN ('candidate','validated','rejected','insight','pending','incubating')
   ```
   (ajout de `'incubating'` pour les borderline novelty — cf ADR à venir ou diagnostic Sprint 8 §5 dette 2).

2. **Sémantiques** :
   - `candidate` : fraîchement créé, pas encore évalué.
   - `validated` : triple validation Binah/Gevurah/Da'at passée, en attente de promotion.
   - `insight` : promu comme insight utilisable (`InsightSession.mark_as_insight`).
   - `rejected` : au moins un gate a rejeté.
   - `pending` : deferred (ex. max_insights atteint, `session.defer_candidate`).
   - `incubating` : novelty borderline (0.35 ≤ score < 0.45) — Ibur, attend plus d'évidence.

3. **`'accepted'` n'est PAS un statut**. Tout code ou doc qui utilise ce terme dans le contexte `candidate_insights` doit être corrigé.

4. **Vocabulaire métrique distinct** : il est acceptable d'avoir une métrique nommée `insights_accepted` dans un régulateur si elle agrège `status IN ('insight','validated')`. Le nommage de variable est une convention métier ; le statut SQL est une valeur de schéma.

5. **Double persistance des insights validés** : quand un candidat passe la triple validation, il est :
   - sauvegardé dans `candidate_insights` avec `status='insight'`, ET
   - ré-ancré dans `epistememory` via `yesod.remember(... tags=['insight','chokmah','validated'])` (core.py:497–506).
   Le tag `'validated'` dans `epistememory` n'est pas un statut, c'est un tag — il peut coexister avec ce vocabulaire.

## Conséquences

- Les audits doivent requêter `status IN ('insight','validated')` pour compter les succès.
- Le fichier `daemon_tasks/tzimtzum.py:249` est bugué mais hors scope Sprint 8b (impact direct sur le régulateur Tzimtzum → à corriger dans un sprint dédié avec tests de non-régression sur la décision binaire actif/dormant).
- Les dashboards web qui mentionnent "accepted" doivent être alignés.
- Les tests de tzimtzum (`tests/test_tzimtzum.py:606,619,632,674`) continuent d'utiliser l'argument `insights_accepted` — c'est le nom du *paramètre Python*, pas une valeur SQL. Pas de correction nécessaire.

## Occurrences à corriger (inventaire Sprint 8b)

Commande de scan :
```bash
grep -rn "accepted" --include="*.py" --include="*.md" | grep -Ei "insight|candidate" | grep -v __pycache__ | grep -v .venv
```

| Fichier:ligne | Nature | Priorité |
|---|---|---|
| `daemon_tasks/tzimtzum.py:249` | Bug SQL réel — requête ne matche jamais | **haute** (sprint dédié) |
| `ohr_yashar.py:109` | Assignation `insights_accepted=n_validated` — cohérent, pas bug | aucune |
| `partzufim/abba.py:196` | Commentaire "acceptés" dans docstring — OK | cosmétique |
| `insightforge/ratzo_v_shov.py:272-275` | Variable locale `accepted` — cohérent | aucune |
| `tzimtzum.py:515,536` | Paramètre Python `insights_accepted` — convention métier | aucune |
| `tests/test_tzimtzum.py:606,619,632,670,674` | Tests de paramètre Python — aucun rapport statut SQL | aucune |
| `masakh/tests/test_masakh.py:1083` | Idem | aucune |

## Référence

- Schéma : `insightforge/schema.sql`
- Migration statut incubating : `migrations/005_allow_incubating_status.sql`
