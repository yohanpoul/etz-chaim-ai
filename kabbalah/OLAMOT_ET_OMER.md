# Les 4 Mondes (Olamot) et les 49 Calibrations (Omer)

---

## Les 4 Mondes — Niveaux de manifestation

Chaque programme existe à 4 niveaux. TOUJOURS commencer par Atziluth avant Yetzirah.

### Atziluth אֲצִילוּת (Émanation)
**Lettre du Tétragramme** : Yod (י)
**Rôle** : Le CONCEPT PUR du programme. Le "pourquoi". La spécification formelle.
**En pratique** : Le document de design, le paper théorique, la raison d'être.
**Modèle IA** : Claude Opus 4.7 (frontier, raisonnement stratégique) ou réflexion humaine.
**Règle** : Ce qui est défini en Atziluth ne change JAMAIS pendant le développement d'une phase.

### Briah בְּרִיאָה (Création)
**Lettre du Tétragramme** : Hé (ה)
**Rôle** : Le DESIGN. L'architecture, les interfaces, les schémas, les contrats.
**En pratique** : Les schémas de DB, les interfaces Python, les diagrammes d'architecture.
**Modèle IA** : Qwen 32B local (raisonnement structuré, structured output).
**Règle** : Le design peut être révisé mais chaque révision doit être justifiée par rapport à Atziluth.

### Yetzirah יְצִירָה (Formation)
**Lettre du Tétragramme** : Vav (ו)
**Rôle** : Le CODE. L'implémentation, les tests, le pipeline.
**En pratique** : Le code Python, les tests, les migrations SQL.
**Modèle IA** : Phi-4 14B local (tâches courantes, code generation).
**Règle** : Le code doit respecter le design de Briah. Si le code demande un changement de design, remonter à Briah.

### Assiah עֲשִׂיָּה (Action)
**Lettre du Tétragramme** : Hé final (ה)
**Rôle** : Le DÉPLOIEMENT. Le runtime, les données réelles, le monitoring.
**En pratique** : Le déploiement sur Mac mini, la connexion à PostgreSQL, Grafana.
**Modèle IA** : Qwen 7B + tool calls (exécution rapide, actions concrètes).
**Règle** : Si le déploiement révèle un problème, remonter au niveau approprié (Yetzirah pour un bug, Briah pour un problème de design, Atziluth si le concept même est remis en question).

### Le mouvement descendant et ascendant

```
Atziluth (concept)
    ↓ descente : le concept se concrétise
Briah (design)
    ↓ descente : le design se code
Yetzirah (code)
    ↓ descente : le code se déploie
Assiah (runtime)
    ↑ remontée : les problèmes en production remontent
    ↑ vers le niveau où ils doivent être résolus
```

---

## Les 49 Calibrations du Omer

### Principe

Les 7 Midot (Chesed→Malkuth) × 7 = 49 combinaisons.
Chaque combinaison est un PARAMÈTRE DE CALIBRATION spécifique.

Dans la tradition : les 49 jours entre Pessah et Shavuot, chaque jour on raffine une combinaison.
Dans l'IA : pour chaque programme, 7 axes de tuning dérivés systématiquement.

### Grille complète

Format : `X-dans-Y` = comment la qualité X se manifeste dans le contexte Y.

#### Pour EpisteMemory (Yesod) :

| Jour | Combinaison | Paramètre | Type | Default |
|------|-------------|-----------|------|---------|
| 1 | Chesed-dans-Yesod | `store_threshold` | float 0-1 | 0.1 (stocker généreusement) |
| 2 | Gevurah-dans-Yesod | `gc_aggressiveness` | float 0-1 | 0.5 |
| 3 | Tiferet-dans-Yesod | `contradiction_detection_threshold` | float 0-1 | 0.7 |
| 4 | Netzach-dans-Yesod | `critical_entry_ttl_multiplier` | float | 3.0 |
| 5 | Hod-dans-Yesod | `introspection_interval_sec` | int | 3600 |
| 6 | Yesod-dans-Yesod | `embedding_model` | string | "qwen2.5:7b" |
| 7 | Malkuth-dans-Yesod | `api_response_format` | string | "json" |

#### Pour SelfMap (Hod) :

| Jour | Combinaison | Paramètre | Type | Default |
|------|-------------|-----------|------|---------|
| 8 | Chesed-dans-Hod | `eval_domains_breadth` | int | 20 (nb de domaines testés) |
| 9 | Gevurah-dans-Hod | `competence_threshold` | float 0-1 | 0.6 (en dessous = "je ne sais pas") |
| 10 | Tiferet-dans-Hod | `calibration_method` | string | "brier_score" |
| 11 | Netzach-dans-Hod | `eval_frequency_hours` | int | 24 |
| 12 | Hod-dans-Hod | `meta_eval_enabled` | bool | true (évaluer l'évaluation) |
| 13 | Yesod-dans-Hod | `competence_map_storage` | string | "postgresql" |
| 14 | Malkuth-dans-Hod | `expose_confidence_to_user` | bool | true |

#### Pour IntentKeeper (Netzach) :

| Jour | Combinaison | Paramètre | Type | Default |
|------|-------------|-----------|------|---------|
| 15 | Chesed-dans-Netzach | `max_concurrent_intentions` | int | 5 |
| 16 | Gevurah-dans-Netzach | `abandon_threshold` | float 0-1 | 0.2 (abandonner si progrès < 20%) |
| 17 | Tiferet-dans-Netzach | `strategy_adaptation_interval` | string | "weekly" |
| 18 | Netzach-dans-Netzach | `max_duration_days` | int | 90 |
| 19 | Hod-dans-Netzach | `progress_report_interval` | string | "daily" |
| 20 | Yesod-dans-Netzach | `checkpoint_frequency` | string | "hourly" |
| 21 | Malkuth-dans-Netzach | `notification_style` | string | "summary" |

#### Pour DissensuEngine (Tiferet) :

| Jour | Combinaison | Paramètre | Type | Default |
|------|-------------|-----------|------|---------|
| 22 | Chesed-dans-Tiferet | `include_minority_views` | bool | true |
| 23 | Gevurah-dans-Tiferet | `divergence_threshold` | float 0-1 | 0.6 |
| 24 | Tiferet-dans-Tiferet | `synthesis_attempt_max` | int | 3 (essayer 3 fois avant mode dissensus) |
| 25 | Netzach-dans-Tiferet | `deliberation_max_rounds` | int | 10 |
| 26 | Hod-dans-Tiferet | `expose_tensions_format` | string | "structured" |
| 27 | Yesod-dans-Tiferet | `store_open_questions` | bool | true |
| 28 | Malkuth-dans-Tiferet | `user_facing_confidence` | bool | true |

Les jours 29-49 couvrent Gevurah, Chesed, et les degrés supérieurs (à détailler quand ces phases seront atteintes).

### Utilisation pratique

```python
# Chaque programme charge ses 7 paramètres Omer depuis la config
class OmerConfig:
    def __init__(self, sephirah: str):
        self.params = load_config(f"omer/{sephirah}.yaml")
    
    def get(self, combination: str) -> Any:
        """Ex: omer.get('gevurah_dans_yesod') → 0.5"""
        return self.params[combination]

# Usage dans EpisteMemory
class EpisteMemory:
    def __init__(self):
        self.omer = OmerConfig("yesod")
        self.gc_aggressiveness = self.omer.get("gevurah_dans_yesod")
        self.contradiction_threshold = self.omer.get("tiferet_dans_yesod")
```
