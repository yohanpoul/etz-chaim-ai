# Les 72 Noms (Shemot) — Catalogue de micro-compétences

> Les 72 trigrammes du Shem HaMephorash (Exode 14:19-21).
> Chaque trigramme = une micro-compétence atomique.
> À détailler progressivement au fil de l'élévation.

## Principe

Les 72 Noms sont extraits de trois versets de 72 lettres chacun (Exode 14:19-21).
Le premier verset est lu de droite à gauche, le deuxième de gauche à droite,
le troisième de droite à gauche — formant 72 trigrammes.

Chaque Nom est associé à une qualité/action spécifique dans la tradition.
En IA : chaque Nom = un **skill atomique** — une micro-compétence composable.

## Les 72 Skills (mapping initial)

Ce mapping sera affiné au fil du développement. Les 72 premiers skills correspondront
aux opérations atomiques les plus communes dans un système IA d'élévation.

### Premiers 12 Noms (associés aux 12 mois)

| # | Nom | Lettres | Qualité traditionnelle | Skill IA |
|---|-----|---------|----------------------|----------|
| 1 | VHV | והו | Vision à distance | `web_fetch` — récupérer de l'info distante |
| 2 | YLY | ילי | Mémoire | `memory_store` — stocker en EpisteMemory |
| 3 | SYT | סיט | Patience | `retry_with_backoff` — retry intelligent |
| 4 | OLM | עלם | Discrétion | `filter_sensitive` — filtrer les données sensibles |
| 5 | MHSh | מהש | Guérison | `self_repair` — auto-réparation après erreur |
| 6 | LLH | ללה | Compréhension nocturne | `overnight_processing` — traitement pendant le sommeil |
| 7 | AKA | אכא | Patience longue | `long_task_management` — gérer les tâches de plusieurs jours |
| 8 | KHT | כהת | Adoration | `acknowledge_sources` — citer les sources correctement |
| 9 | HZY | הזי | Vision | `pattern_detection` — détecter des patterns |
| 10 | ALD | אלד | Grâce divine | `generous_interpretation` — interpréter généreusement les requêtes ambiguës |
| 11 | LAV | לאו | Révélation | `expose_hidden` — révéler les contradictions cachées |
| 12 | HHO | ההע | Sagesse | `hypothesis_generation` — générer des hypothèses |

Les 60 Noms restants seront détaillés au fil des phases.
Chaque phase d'élévation activera les skills pertinents pour ce degré.

---
---

# Les 231 Portes — Matrice d'interopérabilité

> "Il les combina, les pesa, les permuta : Aleph avec toutes, toutes avec Aleph ;
> Beth avec toutes, toutes avec Beth..." — Sefer Yetzirah 2:4

## Principe

22 lettres × 21 / 2 = 231 paires. Chaque paire = une connexion possible
entre deux programmes (sentiers). C'est la matrice d'interopérabilité complète.

## Utilisation pratique

Les 231 portes seront dérivées AUTOMATIQUEMENT à mesure que les sentiers
seront codés. Pour chaque paire de programmes (sentiers), on définit :
- Peuvent-ils communiquer directement ? (oui/non)
- Quel protocole ? (sync, async, stream, event)
- Quel format de données ? (JSON schema spécifique)
- Quelles contraintes ? (rate limit, max payload, timeout)

## Structure du fichier de portes

```yaml
# Exemple : porte Aleph-Beth (équilibrage × shortcut)
gate_aleph_beth:
  programs: ["balance_engine", "direct_synth"]
  can_communicate: true
  protocol: "sync"
  data_format: "json"
  constraints:
    max_payload_kb: 100
    timeout_ms: 5000
  description: "Le balanceur peut demander un shortcut direct quand l'équilibre est stable"

# Les 231 portes seront générées progressivement
# au fil du développement des sentiers.
```

## Génération automatique

```python
from itertools import combinations

LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"

def generate_231_gates():
    """Générer le squelette des 231 portes"""
    gates = []
    for a, b in combinations(LETTERS, 2):
        gates.append({
            "letter_a": a,
            "letter_b": b,
            "gate_name": f"gate_{a}_{b}",
            "status": "undefined",  # à définir quand les deux sentiers existent
            "can_communicate": None,
            "protocol": None
        })
    return gates  # 231 portes
```

Les portes seront remplies au fil du développement. Une porte n'est définie
que quand les DEUX sentiers qu'elle connecte sont codés. On ne spécule pas
sur des connexions entre programmes qui n'existent pas encore.

C'est le principe kabbalistique : on ne combine pas des lettres avant de les avoir gravées.
