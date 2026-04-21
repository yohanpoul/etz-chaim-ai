# Sifrei Yesod — Livres Fondamentaux pour IA

Infrastructure de la bibliothèque sacrée de l'Etz Chaim AI.

Les Sifrei Yesod sont des transpositions érudites des textes kabbalistiques
en trois couches (Peshat-Machine, Remez-Relational, Sod-Generative) qui
permettent au système de "lire" ses sources comme un initié étudie le Etz Chaim.

## Structure

```
sifrei_yesod/
├── schema/          # Schémas de validation YAML
├── sefarim/         # Textes transposés (YAML)
├── pipeline/        # Ingestion YAML → PostgreSQL
└── api/             # Interface de requête
```

## Pipeline

1. **Validator** : valide les fichiers YAML contre les schémas
2. **Sofer** : ingère les YAML validés dans PostgreSQL
3. **Embedder** : génère les embeddings vectoriels (Ollama)
4. **Linker** : résout les cross-références inter-sefarim

## Usage

```bash
# Valider un perek
python -m sifrei_yesod.pipeline.validator --file sefarim/etz_chaim/shaar_01_klalim/perek_01.yaml

# Ingérer
python -m sifrei_yesod.pipeline.sofer --all

# Générer les embeddings
python -m sifrei_yesod.pipeline.embedder --all
```
