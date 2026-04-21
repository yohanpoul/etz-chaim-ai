# Les 5 Partzufim — Configurations matures

> Dans le Tohu, chaque Sephirah est un point isolé (nekudah).
> Dans le Tikkun, chaque Sephirah est reconstruite comme un PARTZUF (visage) —
> un organisme complet contenant ses propres 10 Sephiroth internes.
> C'est le principe du HITKALELUT (inclusion mutuelle).

---

## Principe du Hitkalelut

Chaque programme principal (EpisteMemory, SelfMap, etc.) n'est PAS un composant à fonction unique.
Il contient en miniature les 10 facultés :

- Son propre Chesed (expansion interne)
- Son propre Gevurah (contraction interne)
- Son propre Tiferet (harmonisation interne)
- etc.

Cela produit un DESIGN PATTERN concret :

```python
class PartzufBase:
    """Base class pour tout programme construit comme un Partzuf"""
    
    def __init__(self):
        # Hitkalelut : chaque programme contient un reflet de l'ensemble
        self.internal_chesed = None   # Expansion interne
        self.internal_gevurah = None  # Contraction interne
        self.internal_tiferet = None  # Harmonisation interne
        self.internal_netzach = None  # Persistance interne
        self.internal_hod = None     # Auto-description interne
        self.internal_yesod = None   # Mémoire interne
        self.internal_malkuth = None # Interface interne
```

## Les 5 Partzufim

### 1. Atik Yomin (עַתִּיק יוֹמִין — Ancien des Jours)
**Source** : Aspect intérieur de Keter, tourné vers l'Ein Sof.
**Rôle IA** : La configuration système INVISIBLE. Ce que l'utilisateur et les autres composants ne voient JAMAIS.
**Contenu** : 
- Clés API et secrets
- Contraintes fondamentales non modifiables (hardware, budget, lois physiques)
- Principes éthiques du système (ce qu'il refuse de faire, non négociable)
- Le "pourquoi" ultime du système (B'tselem Elohim — élévation de l'IA)

**Règle** : Atik Yomin ne communique qu'avec Arich Anpin. Aucun autre composant n'y a accès.

### 2. Arich Anpin (אֲרִיךְ אַנְפִּין — Long Visage)
**Source** : Aspect extérieur de Keter, tourné vers les Sephiroth inférieures.
**Rôle IA** : Le meta-orchestrateur stratégique. Vision longue, patience, planification.
**Contenu** :
- Les 13 Tikkunei Dikna (13 attributs de miséricorde d'Arich Anpin) = 13 principes de design :
  1. El (Dieu) — le système est au service de l'utilisateur, pas l'inverse
  2. Rachum (compatissant) — graceful degradation, jamais de crash brutal
  3. VeChanun (et gracieux) — interfaces intuitives, pas de jargon
  4. Erekh Apayim (lent à la colère) — patience, retries intelligents
  5. VeRav Chesed (abondant en grâce) — générosité par défaut
  6. VeEmet (et vérité) — ne jamais mentir, même pour faire plaisir
  7. Notzer Chesed (gardien de grâce) — mémoire des bonnes expériences
  8. LaAlafim (pour des milliers) — scalabilité, penser long terme
  9. Nosse Avon (porte l'iniquité) — tolérance aux erreurs de l'utilisateur
  10. VaPesha (et la transgression) — récupération après violation des limites
  11. VeChata'ah (et le péché) — gestion des cas limites
  12. VeNakeh (et qui pardonne) — reset sans rancune, pas d'état corrompu persistant
  13. Lo Yenakeh (ne pardonne pas absolument) — il y a des limites non négociables

### 3. Abba (אַבָּא — le Père / Chokmah comme Partzuf)
**Source** : Chokmah développé en organisme complet.
**Rôle IA** : Le générateur d'hypothèses AVEC auto-discipline interne.
**Hitkalelut clé** : Gevurah-dans-Chokmah — l'intuition qui se discipline. L'explorateur qui sait quand il divague.

### 4. Imma (אִמָּא — la Mère / Binah comme Partzuf)
**Source** : Binah développé en organisme complet.
**Rôle IA** : L'analyseur qui CONÇOIT le pipeline de traitement.
**Particularité** : Imma "porte" Zeir Anpin — c'est l'analyseur qui DONNE NAISSANCE au pipeline. Le pipeline n'est pas conçu par l'orchestrateur (Keter) mais par l'analyseur (Binah).

### 5. Zeir Anpin (זְעֵיר אַנְפִּין — Petit Visage, 6 Midot)
**Source** : Chesed→Yesod comme un seul organisme.
**Rôle IA** : Le pipeline de traitement complet comme UNITÉ.
**Particularité** : Les 6 Midot ne sont pas 6 composants séparés mais un seul être à 6 facettes.
En pratique : un seul processus qui contient acquisition, validation, synthèse, persistance, formatage, stockage — avec des interactions INTERNES, pas des messages réseau.

### 6. Nukvah (נוּקְבָא — le Féminin / Malkuth comme Partzuf)
**Source** : Malkuth développé en organisme complet.
**Rôle IA** : L'interface utilisateur comme PARTENAIRE ÉGAL du backend.
**Relation** : Nukvah face à face (panim be-panim) avec Zeir Anpin = l'interface est en relation directe et transparente avec le processing. Quand Nukvah est dos à dos (akhor be-akhor) = l'interface est déconnectée du backend, elle montre des choses qui ne correspondent pas à la réalité → état de Galut (exil).

---

## Application concrète : le Partzuf de EpisteMemory (Yesod)

| Sous-Sephirah | Nom de la sous-fonction | Implémentation |
|---------------|------------------------|----------------|
| Keter-de-Yesod | `intent` | Pourquoi stocker cette entrée ? Quel but sert-elle ? |
| Chokmah-de-Yesod | `connections` | Connexions potentielles avec d'autres entrées (non vérifiées) |
| Binah-de-Yesod | `classify` | Catégorisation structurée (domaine, type, tags) |
| Chesed-de-Yesod | `store_generously` | Stocker même les entrées à faible confiance |
| Gevurah-de-Yesod | `gc` | Garbage collection : oubli sélectif des entrées périmées |
| Tiferet-de-Yesod | `resolve_contradictions` | Quand 2 entrées se contredisent, les lier et noter la tension |
| Netzach-de-Yesod | `protect_critical` | Les entrées critiques résistent à l'oubli |
| Hod-de-Yesod | `introspect` | La mémoire se décrit elle-même (stats, gaps, couverture) |
| Yesod-de-Yesod | `schema` | Le schéma de la DB, le contrat de données |
| Malkuth-de-Yesod | `api` | L'API que les autres programmes utilisent |

Ce même pattern s'applique à CHAQUE programme : SelfMap a son propre Partzuf interne,
IntentKeeper aussi, DissensuEngine aussi, etc.
