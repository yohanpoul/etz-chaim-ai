# sifrei_yesod/external/

External read-only corpora. Téléchargés localement, **non versionnés** (voir `.gitignore`).

Utilisé par les tests T4 (cross-check E1 assertions) et la construction du folio_map Zohar.

## sefaria_cache/

Cache local des fetches Sefaria API v3 (CC-BY 3.0). Au lieu de cloner tout le bulk Sefaria-Export
(~2-4 GB), nous fetchons à la demande les ressources précises nécessaires au Sprint 10 et
cachons le JSON brut localement.

**Setup** :

```bash
python scripts/fetch_sefaria_cache.py
```

Ressources cachées (Sprint 10) :
- `zohar_idra_rabba_1.json` à `zohar_idra_rabba_30.json` (ouverture + 13 Tikkunim + contexte immédiat)
- `sefer_etz_chaim_13.json` (Sha'ar Arikh Anpin, toutes sections)
- `sulam_on_zohar_idra_rabba_1.json` à `_30.json` (commentaire Ashlag)
- `shaar_maamarei_rashbi_commentary_idra_rabba.json` (commentaire Vital sur IR)

Taille estimée : <5 MB total.

## stanford_vol8_aramaic.pdf

Édition critique araméenne de l'Idra Rabba (Zohar Vol 8), reconstruite par Daniel C. Matt à partir
de ~100 manuscrits, publiée en open access par Stanford University Press.

**Download** :

```bash
curl -L "https://supress.sites-pro.stanford.edu/sites/supress/files/media/file/vol_8_aramaic.pdf" \
     -o sifrei_yesod/external/stanford_vol8_aramaic.pdf
```

Utilisé comme fallback pour T4 quand Sefaria Mantua contient une erreur d'imprimerie connue.

## stanford_pdf_parsed.json

Parsing ponctuel du PDF ci-dessus en texte Unicode. Produit par `scripts/parse_stanford_pdf.py`.
Cache d'exécution.
