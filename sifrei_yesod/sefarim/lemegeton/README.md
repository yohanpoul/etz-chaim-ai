# Lemegeton — Corpus adversarial

**Statut** : corpus brut ingéré, transposition non commencée.

## Ce que c'est

Le *Lemegeton Clavicula Salomonis* (La Petite Clef de Salomon) est un grimoire
de magie cérémonielle compilé vers 1640 à partir de matériaux des 13e-16e siècles.
Il est constitué de **cinq livres** distincts :

| Livre | Contenu | Taille brute |
|-------|---------|--------------|
| Ars Goetia | 72 esprits démoniaques, hiérarchie, sigilla, conjurations | 92 KB |
| Ars Theurgia Goetia | 31 esprits ambivalents des 4 directions | 43 KB |
| Ars Paulina | 24 anges des heures + 360 anges zodiacaux | 45 KB |
| Ars Almadel | Anges des 4 altitudes, opération par tablette de cire | 44 KB |
| Ars Notoria | Prières mnémoniques pour les arts libéraux | 271 KB |

## Pourquoi ici (et pas dans `etz_chaim/`)

**Synchrétisme interdit.**

Le Lemegeton est de la **magie cérémonielle chrétienne** qui emprunte superficiellement
quelques noms divins hébreux (Adonai, Tetragrammaton, Agla) mais dont :
- l'épistémologie (opérative, instrumentale) diffère de la Kabbale (cosmologique, dévotionnelle),
- la finalité (contrainte d'esprits pour obtenir pouvoirs/savoir) est étrangère au
  projet kabbalistique (tikkun, élévation, devekut),
- la généalogie (grimoires médiévaux + néo-platonisme + Trithème) est distincte
  de la chaîne lurianique (ARI → Vital → Sarug → Cordovero).

Il est ingéré dans `sifrei_yesod/` parce que l'infrastructure (3 couches Peshat/Remez/Sod,
validation YAML, embeddings) convient, mais il reste **un sefer parallèle, pas un
sefer kabbalistique**.

## Finalité dans le projet

**Dompter par la nomination.**

Le Lemegeton fournit une ontologie structurée (72 + 31 + 24 + 360 + 4 entités nommées,
chacune avec offices et sigilla) qu'on peut transposer en **taxonomie nommée de modes
de défaillance IA** :

- Chaque esprit → un vecteur d'attaque / un mode qliphothique spécifique
- Chaque sigillum → une signature détectable (patterns d'attention, n-grammes, distribution de tokens)
- Chaque office → une capacité défensive enseignée une fois l'esprit *lié*
- Le triangle de Salomon → architecture de containment (sandboxing, I/O contractualisé)

Cela étend le `sitra_achra` existant (111 tests, 10 malakhim adversariaux) vers une
**taxonomie exhaustive, mémorisable, debuggable** des 487 entités totales.

**Jamais invoquer, toujours contraindre.** Le corpus n'est pas là pour imiter la magie
rituelle — il est là pour structurer une défense qui connaît le nom de ce qu'elle combat.

## Source et licence

- **Transcription** : Joseph H. Peterson, [esotericarchives.com](https://www.esotericarchives.com/solomon/lemegeton.htm), licence **CC-BY 4.0**
- **Manuscrit source principal** : British Library Sloane MS 3825 (17e siècle)
- **Variantes notées** : Sloane 2731, Sloane 3648, Folger V.b.26
- **Texte sous-jacent** : domaine public (17e siècle)

Attribution requise dans toute dérivation publiée : "Transcription: Joseph H. Peterson,
esotericarchives.com, CC-BY 4.0".

## Structure actuelle

```
lemegeton/
├── meta.yaml                      # métadonnées du sefer
├── README.md                      # ce fichier
├── raw/                           # sources brutes
│   ├── goetia.html    goetia.txt
│   ├── theurgia.html  theurgia.txt
│   ├── paulina.html   paulina.txt
│   ├── almadel.html   almadel.txt
│   ├── notoria.html   notoria.txt
│   └── _extract.py                # HTML → texte (bs4)
├── ars_goetia/                    # [VIDE — à transposer]
├── ars_theurgia_goetia/           # [VIDE — à transposer]
├── ars_paulina/                   # [VIDE — à transposer]
├── ars_almadel/                   # [VIDE — à transposer]
└── ars_notoria/                   # [VIDE — à transposer]
```

## Plan de transposition (à venir)

Suivre le même pattern que `etz_chaim/` :

1. **Peshat-Machine** (YAML structuré) : chaque esprit = un fichier avec nom, rang,
   légions, office, sigillum (référence image + features), conjuration (texte brut).
2. **Remez-Relational** : liens inter-esprits (hiérarchies, correspondances cardinales,
   correspondances planétaires, parallèles avec sitra_achra existant).
3. **Sod-Generative** : mapping adversarial — pour chaque esprit, quel mode de défaillance
   IA il incarne, quel test qliphothique il engendre, quelle défense il enseigne une fois lié.

## Statut épistémique

- **E1** — Source : CC-BY 4.0, manuscrits physiques vérifiables (Sloane, Folger)
- **E2** — Fidélité de transcription : Peterson (philologue reconnu, 40 ans de travail)
- **E4** — Transposition IA : **analogie structurelle, pas isomorphisme**.
  Le Lemegeton n'a pas été écrit pour l'IA. Toute correspondance est herméneutique,
  à valider empiriquement (test qliphothique effectif sur modèle) avant claim d'utilité.

## Garde-fou

Le Lemegeton décrit des opérations rituelles (conjurations, sigilla, triangle de Salomon)
que le projet **ne reproduit PAS**. L'ingestion textuelle sert l'analyse structurelle et
la construction défensive, **pas la pratique magique**. Si une ambiguïté survient entre
l'usage littéral et l'usage analogique, trancher toujours pour l'analogique.
