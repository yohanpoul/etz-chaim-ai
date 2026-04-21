# ═══════════════════════════════════════════════════════════════════
# GUIDE DE TRANSPOSITION — SIFREI YESOD (ספרי יסוד)
# Codifié par Claude Opus 4.7 (instance stratégique Etz Chaim AI)
# ═══════════════════════════════════════════════════════════════════
# 
# Ce document encode la TECHNIQUE COMPLÈTE de transposition des
# textes kabbalistiques sacrés en format YAML pour l'IA.
# Tout modèle Claude (Code ou autre) qui suit ce guide produira
# des transpositions de qualité érudite.
#
# RÈGLE ABSOLUE : JAMAIS condenser les textes sacrés. 
# Toujours viser 100% de couverture du texte source.
# Si un texte est trop long → split en perek_XXa.yaml, perek_XXb.yaml
# ═══════════════════════════════════════════════════════════════════

## 1. PHILOSOPHIE

Les Sifrei Yesod sont des textes kabbalistiques transposés pour l'IA en 3 couches :
- **Peshat-Machine** : assertions formelles (ce que le texte AFFIRME)
- **Remez-Relational** : relations entre concepts (graphe traversable)
- **Sod-Generative** : principes dynamiques pour générer de nouvelles compréhensions

Chaque concept kabbalistique doit être FONCTIONNELLEMENT OPÉRATIF — pas décoratif.
L'érudition est OBLIGATOIRE — pas de simplification, pas de raccourcis.

## 2. STRUCTURE DU FICHIER YAML

```yaml
# ═══════════════════════════════════════════════════════════════════
# SIFREI YESOD — ספרי יסוד
# Sefer: Etz Chaim (עץ חיים)
# Heikhal: N — Nom du Heikhal (nom hébreu)
# Sha'ar: N — Nom du Sha'ar (nom hébreu)
# Perek: N — Titre du Perek (titre hébreu)
# ═══════════════════════════════════════════════════════════════════

meta:
  sefer: etz_chaim
  heikhal: 1          # numéro du Heikhal (0 si standalone comme Sha'ar HaKlalim)
  shaar: 1            # numéro du Sha'ar dans le Heikhal
  shaar_name_he: "שער עגולים ויושר"
  perek: 1            # numéro du Perek
  part: "a"           # OPTIONNEL — seulement si le texte est splitté (a, b, c...)
  source_edition: "Sefaria / hebrew.grimoar.cz (Public Domain)"
  transposed_by: "Claude Opus 4.7 (auto-transposition)"
  version: 1
  strates: ["base"]
  note: "Description optionnelle du contenu"

# ═══════════════════════════════════════════════════════════════════
#                    COUCHE 1 : PESHAT-MACHINE
# ═══════════════════════════════════════════════════════════════════

assertions:
  - id: "EC-H{heikhal}S{shaar}-{NNN}"   # EC = Etz Chaim, H=Heikhal, S=Sha'ar
    source_he: "le texte hébreu SOURCE exact (pas de traduction)"
    source_ref: "Heikhal N, Sha'ar N:N"
    assertion: |
      L'assertion DÉTAILLÉE en français.
      Doit contenir :
      - Ce que le texte AFFIRME explicitement
      - Les TERMES TECHNIQUES en hébreu translittéré avec traduction
      - Les PREUVES scripturaires citées par le texte
      - Les IMPLICATIONS logiques
    type: axiome_explicite  # voir types ci-dessous
    concepts:
      - {id: concept_id_snake_case, role: description_du_rôle}
    mapping:
      modules: ["chemin/vers/module.py"]  # modules du système qui implémentent ce concept
      tables: ["nom_table"]               # tables PostgreSQL pertinentes
      partzufim: ["nom_partzuf"]          # Partzufim concernés
      relevance: "Pourquoi cette assertion est importante pour le système IA"

# ═══════════════════════════════════════════════════════════════════
#                    COUCHE 2 : REMEZ-RELATIONAL
# ═══════════════════════════════════════════════════════════════════

relations:
  - id: "REL-H{heikhal}S{shaar}-{NNN}"
    type: causal          # voir types ci-dessous
    from: concept_id_1
    to: concept_id_2
    via: [concept_intermédiaire]  # OPTIONNEL
    nature: "Description de la relation en une phrase"
    assertions_source: ["EC-H1S1-001", "EC-H1S1-002"]

# ═══════════════════════════════════════════════════════════════════
#                    COUCHE 3 : SOD-GENERATIVE
# ═══════════════════════════════════════════════════════════════════

principes_generatifs:
  - id: "PG-H{heikhal}S{shaar}-{NNN}"
    nom: "Nom du Principe (Court et Descriptif)"
    source_assertions: ["EC-H1S1-001", "EC-H1S1-002"]
    formalisation: |
      Description FORMELLE du principe :
      - Ce qu'il AFFIRME
      - Sa FORMULE ou son MÉCANISME
      - Ses PROPRIÉTÉS
      - Ses CONDITIONS d'application
    applications_ia:
      - "Comment ce principe s'applique au système Etz Chaim AI"
      - "Parallèles avec l'architecture logicielle"
      - "Implications pratiques pour le code"
    questions_ouvertes:
      - "Questions non résolues par le texte"
```

## 3. TYPES D'ASSERTIONS

| Type | Description | Usage |
|------|------------|-------|
| `axiome_explicite` | Le texte affirme directement | ~80% des assertions |
| `interprétation_lurianique` | Interprétation spécifique du ARI | ~10% |
| `déduction_scripturaire` | Déduit d'un verset biblique | ~5% |
| `analogie_explicative` | Analogie utilisée par le texte | ~3% |
| `déduction_logique` | Logique déductive du texte | ~2% |

## 4. TYPES DE RELATIONS

| Type | Description | Exemple |
|------|------------|---------|
| `causal` | A cause B | Le Tzimtzum cause la formation des Kelim |
| `séquentiel` | A puis B (ordre temporel) | Igulim d'abord, Yosher ensuite |
| `contenance` | A contient B | A"K contient tous les mondes |
| `flux` | A alimente B | Le Kav alimente les Igulim |
| `transformation` | A se transforme en B | 4 Mohin deviennent 3 (Mem→Lamed) |
| `dualité_structurelle` | A et B sont un couple | Igulim et Yosher coexistent |
| `hiérarchique` | A est au-dessus de B | Ruah au-dessus de Nefesh |
| `analogie` | A est comme B | Foie:Nefesh comme Igulim:Nefesh |

## 5. RÈGLES DE TRANSPOSITION

### 5.1 Couverture
- CHAQUE phrase significative du texte hébreu doit produire au moins une assertion
- Ne JAMAIS sauter un passage — même s'il semble répétitif
- Les renvois ("comme expliqué en Branch 2") doivent être notés explicitement
- Les questions ouvertes du texte ("Tzarikh Iyun") doivent être capturées

### 5.2 Termes Techniques
- Toujours donner le terme HÉBREU en translittération + traduction française
- Format : TERME_HÉBREU (translittération — traduction)
- Exemple : TZIMTZUM (צמצום — contraction)
- Ne JAMAIS remplacer un terme technique par une approximation

### 5.3 Concepts (IDs)
- Format : snake_case en anglais/hébreu translittéré
- Exemples : `ohr_pnimi`, `tzimtzum`, `kav_yashar`, `adam_kadmon`
- Chaque concept a un `role` qui décrit sa fonction dans l'assertion
- Les concepts sont RÉUTILISÉS entre assertions si le même concept apparaît

### 5.4 Mapping
- `modules` : les fichiers Python du système qui implémentent ce concept
- `tables` : les tables PostgreSQL pertinentes
- `partzufim` : les Partzufim concernés (adam_kadmon, arikh_anpin, abba, imma, etc.)
- `relevance` : une phrase expliquant pourquoi c'est important pour l'IA

### 5.5 Principes Génératifs
- Le NOM doit être court et descriptif (pas plus de 10 mots)
- La FORMALISATION doit être assez précise pour être implémentable
- Les APPLICATIONS_IA doivent faire le lien avec l'architecture logicielle
- Les QUESTIONS_OUVERTES montrent l'honnêteté intellectuelle

### 5.6 Numérotation
- Assertions : EC-H{heikhal}S{shaar}-{NNN} (ex: EC-H1S1-001)
  - Pour le Sha'ar HaKlalim (heikhal=0) : EC-K{perek}-{NNN} (ex: EC-K1-001)
- Relations : REL-H{heikhal}S{shaar}-{NNN}
- Principes : PG-H{heikhal}S{shaar}-{NNN}
- La numérotation est CONTINUE dans tout le Sha'ar (pas reset par perek)

### 5.7 Splitting
- Si un texte produit plus de ~30 assertions → split en parties (a, b, c...)
- Chaque partie doit être thématiquement cohérente
- Les IDs continuent sans reset entre parties (a finit à -042, b commence à -043)
- Le champ `part: "a"` dans le meta indique la partie

## 6. MODULES DU SYSTÈME ETZ CHAIM AI

Pour le mapping, voici les modules principaux :

| Module | Domaine |
|--------|---------|
| `core/ohr_system.py` | Système de lumières (Ohr Pnimi/Makif) |
| `core/sefirot.py` | Les 10 Sefirot et leur hiérarchie |
| `core/shefa_flow.py` | Flux de Shefa entre composants |
| `core/zivvug_engine.py` | Moteur de Zivvug (unions) |
| `core/shem_havayah.py` | Les Shemot (noms divins) et Miluyim |
| `partzufim/arikh_anpin.py` | Arikh Anpin |
| `partzufim/abba.py` | Abba (Chokhmah) |
| `partzufim/imma.py` | Imma (Binah) |
| `partzufim/zeir_anpin.py` | Ze'ir Anpin |
| `partzufim/nukvah.py` | Nukvah (Malkhut) |
| `partzufim/leah.py` | Leah |
| `partzufim/atik_yomin.py` | Atik Yomin |
| `olamot/adam_kadmon.py` | Adam Kadmon |
| `olamot/atzilut.py` | Monde d'Atzilut |
| `olamot/beriah.py` | Monde de Beriah |
| `tzimtzum/regulator.py` | Régulateur de Tzimtzum |
| `madregot/madregot_neshamah.py` | Niveaux de l'âme (NaRaNHaY) |
| `tikkun/kavanah_planner.py` | Planificateur de Kavanot |
| `sefer_yetzirah/tzeruf.py` | Tzeruf spatial |

## 7. TABLES POSTGRESQL

| Table | Contenu |
|-------|---------|
| `partzufim_states` | États des Partzufim |
| `sefirot_hierarchy` | Hiérarchie des Sefirot |
| `ohr_states` | États des lumières (Pnimi/Makif) |
| `shefa_flows` | Flux de Shefa |
| `zivvug_states` | États des Zivvugim |
| `olamot_config` | Configuration des mondes |
| `madregot_states` | Niveaux de l'âme |
| `kavanah_intentions` | Intentions/Kavanot |

## 8. EXEMPLES DE BONNES ASSERTIONS

### Exemple 1 : Axiome Explicite (standard)
```yaml
- id: "EC-H1S1-016"
  source_he: "והנה אז צמצם את עצמו א\"ס בנקודה האמצעית"
  source_ref: "Heikhal 1, Sha'ar 1:2"
  assertion: |
    LE TZIMTZUM — l'acte fondateur :
    Le Ein Sof a CONTRACTÉ (tzimtzem) Lui-même dans la NEKUDAH HA-EMTZA'IT
    (le point central) qui est au MILIEU EXACT de Son Ohr.
    L'Ohr s'est ÉLOIGNÉ (nitrahek) vers les CÔTÉS.
    RÉSULTAT : un MAKOM PANUI (lieu libre), HALAL RIKANI (espace vide).
  type: axiome_explicite
  concepts:
    - {id: tzimtzum, role: contraction_fondamentale}
    - {id: nekudah_emtza_it, role: point_central}
    - {id: halal_rikani, role: espace_vide_résultant}
  mapping:
    modules: ["tzimtzum/regulator.py"]
    tables: ["ohr_states"]
    partzufim: []
    relevance: "LE Tzimtzum — le moment fondateur de tout le système"
```

### Exemple 2 : Principe Génératif (bon)
```yaml
- id: "PG-H1S1-005"
  nom: "Principe du Tzimtzum (Retrait pour Créer l'Espace)"
  source_assertions: ["EC-H1S1-015", "EC-H1S1-016"]
  formalisation: |
    Pour que quelque chose de NOUVEAU puisse exister, la source doit SE RETIRER :
    ÉTAT 0 : L'Ohr Pashut remplit TOUTE la réalité
    ACTE : Tzimtzum = retrait du centre vers la périphérie
    RÉSULTAT : HALAL où les mondes peuvent être
    SANS Tzimtzum → pas de Din → pas de forme → pas de création
  applications_ia:
    - "Le Tzimtzum Regulator fait exactement ça"
    - "Pour qu'un nouveau module existe, l'existant doit se retirer"
    - "Le vide (Halal) est l'espace NÉCESSAIRE pour la création"
  questions_ouvertes:
    - "Le Tzimtzum est-il un acte unique ou continu ?"
```

## 9. PROCESSUS DE TRANSPOSITION

1. LIRE le texte hébreu en ENTIER d'abord
2. IDENTIFIER les blocs thématiques (A, B, C, D...)
3. Pour chaque bloc : extraire TOUTES les assertions
4. Pour chaque assertion : identifier les concepts, le type, les sources
5. APRÈS toutes les assertions : identifier les RELATIONS entre concepts
6. ENFIN : extraire les PRINCIPES GÉNÉRATIFS (synthèse de plusieurs assertions)
7. VÉRIFIER : chaque phrase significative est-elle couverte ?
8. Si non → ajouter les assertions manquantes

## 10. CONTEXTE KABBALISTIQUE

Le transposeur doit connaître :
- Les 10 SEFIROT et leur ordre (KHB-D-HGT-NHY-M)
- Les 5 PARTZUFIM (A"A, Abba, Imma, Z"A, Nukvah)
- Les 4 MONDES (ABYA : Atzilut, Beriah, Yetzirah, Asiyah)
- Les 5 niveaux de l'ÂME (NaRaNHaY)
- Les 4 MILUYIM de YHVH (AV=72, SAG=63, MAH=45, BEN=52)
- La distinction IGULIM (cercles) vs YOSHER (rectitude)
- Le OHR PNIMI vs OHR MAKIF
- Le TZIMTZUM, le KAV, le HALAL
- Les PARTZUFIM secondaires (Atik, Leah, Rachel, Yisra'el Saba, Tevunah)
- Le processus IBUR → YENIKAH → GADLUT
- La SHEVIRAT HA-KELIM et le TIKKUN

## 11. QUALITÉ — AUDIT QA 10 CRITÈRES (/100)

### Score cible : ≥ 95/100. Protocole codifié depuis perek_03 Sha'ar 4 (premier 100/100 auto).

### Commande automatique :
```bash
python -m sifrei_yesod.pipeline.qa_audit <perek.yaml> --sefaria "Sefer_Etz_Chaim.S.P"
```

### Les 10 critères :

| # | Critère | /10 | Auto/Manuel | Ce qui est vérifié |
|---|---------|-----|-------------|-------------------|
| 1 | COUVERTURE | /10 | Manuel | Chaque phrase hébreu = ≥1 assertion. Comparer §§ source vs assertions |
| 2 | STYLE | /10 | Auto | MAJUSCULES percutantes, →, phrases courtes, parenthèses hébraïques |
| 3 | GRANULARITÉ | /10 | Auto | 1 assertion = 1 point doctrinal. Max 8 lignes/assertion |
| 4 | SOURCE_HE | /10 | Manuel | Vérifier 3+ citations mot-à-mot contre le texte fetché |
| 5 | NUSAH AHER | /10 | Auto | Tous les [נ"א] et (ל"ג) du source capturés dans le yaml |
| 6 | ÉRUDITION | /10 | Manuel | Gematriot correctes, noms exacts, translittérations, pas d'erreur doctrinale |
| 7 | RELATIONS | /10 | Auto | Types précis, from/to existent dans les concepts des assertions |
| 8 | PRINCIPES | /10 | Auto | applications_ia avec modules CONCRETS (core/xxx.py, partzufim/xxx.py) |
| 9 | MAPPING | /10 | Auto | [PLANNED] sur TOUS les modules inexistants. Vérification os.path.exists() |
| 10 | RENVOIS | /10 | Auto | Cross-références (cf. EC-xxx) vers les perakim précédents du même sha'ar |

### Corrections typiques (si < 95) :
- Assertion >8 lignes → découper ou condenser
- [PLANNED] manquant → ajouter
- Nusah aher oublié → regex source : `\([^)]*ל"ג[^)]*\)`, `\[...\]`, `\(נ"א...\)`
- Calcul brouillon visible → nettoyer (artefact d'auto-transposition)
- applications_ia génériques → ajouter `core/ohr_system.py`, `partzufim/imma.py`, etc.
- Renvois manquants → cf. EC-xxx des perakim 01/02 du même sha'ar

### Gold standards :
- **Manuel** : `shaar_01_igulim/perek_02a.yaml` (transposé par humain+Claude)
- **Auto 100/100** : `shaar_04_ozen_hotem_peh/perek_03.yaml` (auto-transposé + audit corrigé)

### Checklist rapide (avant soumission) :
- [ ] Chaque phrase significative du texte est couverte par une assertion
- [ ] Tous les termes techniques sont en hébreu translittéré + traduction
- [ ] Les source_he sont des citations EXACTES du texte original
- [ ] Les IDs suivent la convention (EC-H{h}S{s}-{NNN})
- [ ] Les concepts ont des IDs en snake_case cohérents
- [ ] Les relations relient des concepts qui existent dans les assertions
- [ ] Les principes génératifs ont des applications_ia avec modules concrets
- [ ] Le mapping : modules existants sans tag, inexistants avec [PLANNED]
- [ ] Le meta block est complet et correct
- [ ] Si le texte est trop long → splitté en parties avec continuité des IDs
- [ ] ≥3 cross-références vers les perakim précédents du même sha'ar
