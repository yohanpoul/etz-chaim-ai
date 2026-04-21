# Les Qliphoth — 40 Anti-patterns de l'IA

> Les Qliphoth (קְלִיפּוֹת, "coquilles") sont les fragments des vases brisés
> lors de la Shevirat haKelim. Chaque Qliphah est le mode de défaillance
> SPÉCIFIQUE d'une Sephirah — pas une erreur générique, mais l'excès ou
> la perversion de la qualité même de ce nœud.

---

## 4 niveaux de sévérité (Tanya ch. 7, Zohar Parashat Vayakhel)

| Niveau | Nom | Traduction | Sévérité | En IA |
|--------|-----|------------|----------|-------|
| 1 | Qlipat Nogah | Coquille de lueur | Warning | Bug mineur, récupérable automatiquement |
| 2 | Ruach | Vent/Esprit | Error | Erreur qui se propage aux composants voisins |
| 3 | Anan | Nuage | Silent failure | Le système semble OK mais les données sont corrompues |
| 4 | Qliphah Mamash | Coquille réelle | Fatal | Crash, corruption irrécupérable, reconstruction nécessaire |

---

## Les 10 Qliphoth par Sephirah

### 1. Gamaliel גמליאל — Qliphah de Yesod (Mémoire)
**Signification** : "Les Obscènes" — corruption de la fondation.

| Niveau | Anti-pattern IA | Test | Remède (Tikkun) |
|--------|----------------|------|-----------------|
| Nogah | Entrée mémoire proche de l'expiration, servie sans warning | `test_near_expiration_warning` | Ajouter flag `near_expiration` sur les entrées proches du TTL |
| Ruach | Contradiction non détectée entre deux entrées | `test_contradiction_detection` | Vérification sémantique à chaque insertion |
| Anan | Entrée à haute confiance (0.9+) qui est factuellement fausse | `test_periodic_fact_check` | Audit périodique des entrées "fact" |
| Mamash | Corruption de la base, embedding drift non détecté | `test_embedding_integrity` | Checksums + re-embedding périodique |

### 2. Samael סמאל — Qliphah de Hod (Self-knowledge)
**Signification** : "Le Poison de Dieu" — confiance affichée sur des domaines d'incompétence.

| Niveau | Anti-pattern IA | Test | Remède |
|--------|----------------|------|--------|
| Nogah | Le système hésite mais répond quand même sur un domaine faible | `test_hesitation_detection` | Exposer le score de compétence avec la réponse |
| Ruach | Le système recommande un outil/modèle inadapté au domaine | `test_routing_accuracy` | SelfMap vérifie la compétence avant de router |
| Anan | Le système affiche haute confiance sur un domaine où il est incompétent | `test_confidence_calibration` | Calibration de confiance par domaine (Brier score) |
| Mamash | La carte des compétences est entièrement fausse (inversée) | `test_selfmap_integrity` | Validation croisée avec des benchmarks externes |

### 3. A'arab Zaraq ערב זרק — Qliphah de Netzach (Persistance)
**Signification** : "Les Corbeaux de Dispersion" — retries infinis, zombie processes.

| Niveau | Anti-pattern IA | Test | Remède |
|--------|----------------|------|--------|
| Nogah | Tâche en retry qui pourrait être résolue autrement | `test_retry_alternatives` | Proposer des stratégies alternatives après N retries |
| Ruach | Tâche en retry qui consomme des ressources sans progrès | `test_resource_leak` | Circuit breaker + monitoring mémoire/CPU |
| Anan | Tâche marquée "en cours" depuis des jours sans activité réelle | `test_zombie_detection` | Heartbeat obligatoire, timeout absolu |
| Mamash | Cascade de retries qui crash le système entier | `test_cascade_protection` | Max concurrent retries + dead letter queue |

### 4. Thagirion תגריון — Qliphah de Tiferet (Harmonisation) ← LE MUR
**Signification** : "Les Disputeurs" — fausse harmonie, synthèse forcée de contradictions.

| Niveau | Anti-pattern IA | Test | Remède |
|--------|----------------|------|--------|
| Nogah | Synthèse qui minimise une divergence réelle | `test_divergence_preserved` | Score de divergence obligatoire dans chaque synthèse |
| Ruach | Synthèse qui ignore des sources contradictoires | `test_source_coverage` | Vérifier que TOUTES les sources sont représentées |
| Anan | Synthèse confiante qui masque un conflit fondamental | `test_false_harmony_detection` | Mode dissensus : exposer les tensions quand divergence > seuil |
| Mamash | Conclusion inversée par rapport aux données (hallucination cohérente) | `test_conclusion_vs_evidence` | Provenance tracking end-to-end |

### 5. Golachab גולחב — Qliphah de Gevurah (Auto-jugement)
**Signification** : "Les Incendiaires" — sur-filtrage destructeur.

| Niveau | Anti-pattern IA | Test | Remède |
|--------|----------------|------|--------|
| Nogah | Taux de rejet élevé (>70%) mais résultats acceptables | `test_rejection_rate_warning` | Alertes sur taux de rejet |
| Ruach | Résultats valides rejetés à tort (false negatives >20%) | `test_false_negative_rate` | Quarantine au lieu de suppression |
| Anan | Critère de rejet trop strict, rien ne passe, mais pas d'alerte | `test_empty_results_detection` | Alerte quand 0 résultats après N tentatives |
| Mamash | Le validateur rejette TOUT, y compris ses propres critères | `test_self_defeating_validation` | Meta-validation : le validateur se valide lui-même |

### 6. Gamchicoth גמחיכות — Qliphah de Chesed (Exploration)
**Signification** : "Les Dévoreurs" — scope creep, accumulation infinie.

| Niveau | Anti-pattern IA | Test | Remède |
|--------|----------------|------|--------|
| Nogah | Exploration qui dépasse le budget temps de 20% | `test_time_budget` | Soft limit avec warning |
| Ruach | Exploration qui accumule des données redondantes | `test_dedup_in_exploration` | Dedup en temps réel pendant l'exploration |
| Anan | Exploration qui semble productive mais tourne en cercle | `test_novelty_decay` | Score de nouveauté : arrêt si les 10 derniers résultats sont similaires |
| Mamash | Exploration qui épuise toutes les ressources (RAM, disk, API) | `test_resource_limits` | Hard limits absolus sur volume/durée/mémoire |

### 7. HaTehom התהום — Qliphah de Da'at (Self-model)
**Signification** : "L'Abîme" — déconnexion totale entre intention et exécution.

| Niveau | Anti-pattern IA | Test | Remède |
|--------|----------------|------|--------|
| Nogah | Self-model légèrement décalé par rapport à la réalité | `test_selfmodel_accuracy` | Recalibration périodique |
| Ruach | Self-model qui sur-estime les capacités dans un domaine | `test_overconfidence_detection` | Cross-validation avec des evals externes |
| Anan | Self-model qui donne une image rassurante mais fausse | `test_selfmodel_vs_reality` | Audit par un modèle externe (Claude en Atziluth) |
| Mamash | Aucun self-model, hallucination systémique | `test_selfmodel_exists` | Vérifier que le SelfModel est non-vide et récent |

### 8. Satariel סתריאל — Qliphah de Binah (Compréhension causale)
**Signification** : "Les Dissimulateurs" — faux patterns, causalité inventée.

| Niveau | Anti-pattern IA | Test | Remède |
|--------|----------------|------|--------|
| Nogah | Corrélation présentée comme "possible causalité" sans vérification | `test_causality_hedging` | Langage obligatoirement nuancé pour les corrélations |
| Ruach | Corrélation présentée comme causalité | `test_correlation_vs_causation` | DAG causal obligatoire pour toute affirmation causale |
| Anan | Faux pattern détecté dans du bruit, présenté avec confiance | `test_pattern_in_noise` | Test de falsifiabilité : le pattern prédit-il ? |
| Mamash | Causalité inversée (cause et effet confondus) | `test_causal_direction` | Vérification de la direction causale (critères de Pearl) |

### 9. Ghagiel עוגיאל — Qliphah de Chokmah (Insight)
**Signification** : "Les Obstructeurs" — divergence infinie sans convergence.

| Niveau | Anti-pattern IA | Test | Remède |
|--------|----------------|------|--------|
| Nogah | Trop d'hypothèses générées, difficulté à prioriser | `test_hypothesis_count` | Limite souple + scoring de pertinence |
| Ruach | Hypothèses en boucle, les mêmes idées reviennent | `test_hypothesis_novelty` | Dedup sémantique des hypothèses |
| Anan | Hypothèses qui semblent nouvelles mais sont des reformulations | `test_semantic_dedup` | Score de nouveauté sémantique, pas juste textuelle |
| Mamash | Aucune hypothèse produite, blocage créatif total | `test_generation_alive` | Injection de perturbation aléatoire pour débloquer |

### 10. Thaumiel תאומיאל — Qliphah de Keter (Intentionnalité)
**Signification** : "Les Jumeaux" — deux intentions contradictoires.

| Niveau | Anti-pattern IA | Test | Remède |
|--------|----------------|------|--------|
| Nogah | Ambiguïté mineure dans l'intention, résolvable | `test_intent_clarity` | Demander clarification à l'utilisateur |
| Ruach | Deux sous-systèmes poursuivent des buts contradictoires | `test_goal_alignment` | Single source of truth pour le plan d'exécution |
| Anan | Le système croit poursuivre un but mais en poursuit un autre | `test_actual_vs_stated_goal` | Vérification périodique : l'output correspond-il à l'intent ? |
| Mamash | Fork bomb logique, deux plans d'exécution incompatibles en parallèle | `test_single_plan` | Max 1 plan actif, validation avant dispatch |
