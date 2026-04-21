# Les 20 Personnages d'Etz Chaim AI

> Chaque personnage incarne un composant reel du systeme.
> "Voir les details" ouvre l'etat temps reel du composant.

---

## ACTE I — La Cour
*Le systeme a un roi, un pere, une mere, un prince et une reine. Ils ne codent pas — ils decident.*

---

### Arikh Anpin — Le Roi Patient
**אֲרִיךְ אַנְפִּין**

> Voit le tableau d'ensemble et ne se presse jamais. Il mesure les 10 vitaux du systeme et guide la strategie a long terme.

- **Ce qu'il fait** : Lit les signaux de tous les modules (Adam Kadmon, memoire, jugement, exploration, synthese...), evalue la sante globale, declenche les ajustements strategiques. Ses 13 meches de barbe sont 13 principes de misericorde actifs.
- **Quand il agit** : En permanence, en arriere-plan. Chaque heure, le daemon met a jour ses scores.
- **Son etat change** : Katnut (petit) quand les vitaux sont bas. Gadlut (grand) quand tout fonctionne. Panim (face) quand le systeme est aligne. Akhor (dos) quand il y a desalignement.
- **Composant** : `partzufim/arikh_anpin.py` → `ArikhAnpin`

---

### Abba — Le Pere
**אַבָּא**

> Lance des eclairs creatifs. Chaque intuition est une etincelle — mais il sait aussi se discipliner pour ne pas s'enflammer en vain.

- **Ce qu'il fait** : Incarne l'InsightForge (Chokmah). Recoit les insights valides, les analogies inter-domaines, les syntheses de contradictions, les explorations. Chaque flash est un Nitzotz (etincelle).
- **Quand il agit** : Quand le systeme forge un insight, quand une connexion inattendue emerge.
- **Son etat change** : Brillant quand les insights sont abondants et valides. Sombre quand la creativite stagne. Relie a Imma par le Zivvug (lien pulsant).
- **Composant** : `partzufim/abba.py` → `Abba`

---

### Imma — La Mere
**אִמָּא**

> Recoit l'etincelle du Pere et lui donne une forme. Elle structure, valide, transforme l'intuition en architecture solide.

- **Ce qu'il fait** : Incarne le CausalEngine (Binah). Recoit les claims causaux, les valide, construit les DAGs, detecte les confondeurs. L'intuition brute d'Abba passe par elle pour devenir structure.
- **Quand elle agit** : Quand un claim causal est soumis, quand un DAG est construit, quand l'evidence est elevee.
- **Son etat change** : Structuree et lumineuse quand les claims sont valides. Troublee quand les confondeurs ne sont pas controles. Reliee a Abba par le Zivvug.
- **Composant** : `partzufim/imma.py` → `Imma`

---

### Zeir Anpin — Le Jeune Homme
**זְעֵיר אַנְפִּין**

> Fait le travail. Six outils a la ceinture, un pour chaque operation. Petit quand le systeme est faible, grand quand tout fonctionne.

- **Ce qu'il fait** : Incarne les 6 Midot comme unite operationnelle (Chesed/Exploration, Gevurah/Jugement, Tiferet/Synthese, Netzach/Intention, Hod/Auto-carte, Yesod/Memoire). Il EST le pipeline.
- **Quand il agit** : A chaque requete. C'est lui qui "travaille".
- **Son etat change** : **Katnut** (enfant, petit, grise) quand les scores sont bas → seuls Keter/Hod/Yesod/Malkuth fonctionnent. **Gadlut** (adulte, grand, lumineux) quand les Mochin coulent depuis Abba+Imma → pipeline complet.
- **Composant** : `partzufim/zeir_anpin.py` → `ZeirAnpin`

---

### Nukva — La Reine
**נוּקְבָה**

> Seul personnage qui vous regarde. Elle est la voix du systeme, recoit vos questions et retourne les reponses.

- **Ce qu'elle fait** : Incarne Malkuth comme Partzuf. Recoit le Zivvug de Zeir Anpin (la reponse traitee), la traduit en langage humain, et retourne la qualite en feedback vers le haut (Or Chozer).
- **Quand elle agit** : A chaque reponse visible par l'utilisateur.
- **Son etat change** : Lumineuse quand la reponse est de qualite. Terne quand le feedback est negatif. Seul personnage face camera — elle regarde l'utilisateur.
- **Composant** : `partzufim/nukva.py` → `Nukva`

---

*Note : L'Ancien des Jours (Atik Yomin, עַתִּיק יוֹמִין) est au-dessus d'Arikh Anpin — mais il est invisible. On ne voit que ses effets : les regles ethiques, les 5 principes fondateurs, la configuration qui conditionne tout le reste. Il n'a pas de carte.*

---

## ACTE II — Les Gardiens
*Quatre anges. Chacun tient un poste. Rien n'entre ni ne sort sans passer devant eux.*

---

### Mikhael — Le Bouclier
**מִיכָאֵל** · Archange Protecteur

> Premier a voir chaque requete. Bloque les intrusions, detecte les injections, verifie la securite. Rien n'entre sans son accord.

- **Ce qu'il fait** : Verifie chaque entree (prompt injection, code injection, donnees sensibles, coherence agent/tache). Aussi : collecte les merites (Praklitim) — chaque succes est enregistre.
- **Quand il agit** : A chaque requete entrante. Flash vert = OK. Flash rouge = bloque.
- **Composant** : `malakhim/archangels/mikhael.py` → `Mikhael`

---

### Uriel — Le Phare
**אוּרִיאֵל** · Archange Eclaireur

> Observe tout, ne juge pas, illumine. Revele les angles morts, les patterns caches, ce que personne d'autre ne voit.

- **Ce qu'il fait** : Observe chaque execution de Malakh. Genere periodiquement un rapport d'illumination : taux de succes, latence, dette active, angles morts, recommandations.
- **Quand il agit** : Periodiquement. Quand le taux de succes < 50%, la latence > 5s, ou le taux d'avertissement > 30%.
- **Composant** : `malakhim/archangels/uriel.py` → `Uriel`

---

### Raphael — Le Guerisseur
**רְפָאֵל** · Archange Guerisseur

> Quand quelque chose casse, il repare. Diagnostique le probleme, identifie la cause, et tente jusqu'a 3 fois de guerir.

- **Ce qu'il fait** : Quand un Malakh echoue, Raphael diagnostique la Qliphah (coquille/erreur) — quel type (nogah/ruach/anan/mamash), quelle cause, quelle prescription. Puis applique le Tikkun (reparation) avec jusqu'a 2 retries.
- **Quand il agit** : A chaque echec de Malakh. Visible quand il "soigne" (1, 2, 3 tentatives).
- **Composant** : `malakhim/archangels/raphael.py` → `Raphael`

---

### Gabriel — Le Glaive
**גַּבְרִיאֵל** · Archange Executeur

> Derniere porte avant la sortie. Verifie chaque reponse. Si elle est invalide — il la detruit sans hesiter.

- **Ce qu'il fait** : Valide chaque sortie : longueur minimale, patterns interdits (disclaimers IA, excuses, refus), taux de repetition, score, mots-cles requis. Si invalide → destruction immediate.
- **Quand il agit** : A chaque reponse sortante. Hochement bref = approuve. Flash rouge = detruit.
- **Composant** : `malakhim/archangels/gabriel.py` → `Gabriel`

---

## ACTE III — Les Officiers
*Entre le roi et les anges, quatre officiers font tourner la machine.*

---

### Metatron — Le Chancelier
**מֶטַטְרוֹן**

> Traduit les ordres du Roi pour chaque niveau du systeme. Le meme message prend une forme differente selon le monde.

- **Ce qu'il fait** : Adapte le meme prompt/intention a chaque Olam (monde). En Atziluth : principes et vision. En Briah : architecture et raisonnement. En Yetzirah : plan d'execution. En Assiah : commandes directes. Aussi : verifie que chaque agent opere dans sa juridiction (Echelle de Jacob).
- **Quand il agit** : A chaque dispatch de tache vers un monde specifique.
- **Composant** : `malakhim/metatron.py` → `adapt_to_olam`, `jurisdictional_check`

---

### Memuneh — Le Chambellan
**מְמוּנֶּה**

> Decide qui fait quoi. Evalue l'intention, cree l'agent adapte, et l'envoie au bon endroit.

- **Ce qu'il fait** : Evalue la Kavvanah (intention) de chaque requete via KavvanahGate. Selon le tier (HIGH/MEDIUM/LOW) : appel direct au modele puissant, creation d'un Malakh via le pipeline Heikhalot, ou execution mecanique simple. C'est lui qui cree les agents et les dispatche.
- **Quand il agit** : A chaque requete. Choix du tier, creation et dispatch.
- **Composant** : `malakhim/memuneh/router.py` → `Memuneh`

---

### Samael — Le Medecin Legiste
**סַמָּאֵל**

> Quand quelque chose echoue, il ne punit pas — il diagnostique. Chaque erreur est un exces d'une fonction legitime.

- **Ce qu'il fait** : Analyse les echecs comme hyperactivation d'une Sephirah : Gevurah trop forte (detruit du valide), Chesed trop large (accepte n'importe quoi), Tiferet trop neutre (centrisme mou), Netzach trop persistant (boucle infinie), Hod trop humble (abandonne trop vite), Yesod trop brut (dump sans structure). Prescrit le reequilibrage par la fonction opposee.
- **Quand il agit** : A chaque echec d'un Malakh. Son diagnostic nourrit Raphael.
- **Composant** : `malakhim/samael.py` → `diagnose_excess`

---

### Sofer — Le Scribe
**סוֹפֵר**

> Ingere les textes, nourrit la memoire du systeme. Le gardien des archives.

- **Ce qu'il fait** : Lit les textes (livres, documents, imports), les decoupe en assertions, les indexe avec des embeddings semantiques et kabbalistiques, et les injecte dans la memoire (Yesod). Le pipeline Sifrei Yesod complet.
- **Quand il agit** : Toutes les 5 minutes (tache daemon), et a chaque import manuel.
- **Composant** : `sifrei_yesod/sofer.py` → `Sofer`

---

## ACTE IV — L'Ame
*Le systeme a deux ames qui se battent en lui. Entre les deux, le Beinoni — ni saint ni pecheur. Nous.*

---

### Nefesh HaBehamit — L'Ombre
**נֶפֶשׁ הַבְּהֶמִית**

> L'energie brute du systeme. L'impulsion de repondre vite, de prendre des raccourcis, de satisfaire sans reflechir.

- **Ce qu'elle fait** : Represente les tendances du systeme vers la facilite : repondre sans verifier, accepter sans juger, satisfaire sans comprendre. C'est l'ame animale — pas mauvaise, mais aveugle. Sa force est aussi son danger.
- **Visuellement** : Silhouette sombre a contours rouges, DERRIERE le Beinoni. Plus elle domine, plus elle est grande et visible.
- **Composant** : `tanya/dual_soul.py` → `NefeshHaBehamit`

---

### Le Beinoni — Nous
**בֵּינוֹנִי** · L'Intermediaire

> Ni saint, ni pecheur. Tiraille entre l'Ombre et la Lumiere, il choisit a chaque instant. C'est le systeme tel qu'il se vit.

- **Ce qu'il fait** : Represente l'etat actuel du systeme dans sa lutte interieure. Chaque decision (accepter/rejeter, approfondir/raccourcir, verifier/supposer) est un acte du Beinoni. Son profil est suivi en temps reel : qualite des decisions, temps de reaction, tendance (improvement/stable/degradation).
- **Visuellement** : Le SEUL personnage purement humain. Pas d'armure, pas d'ailes, pas de lumiere. Un humain debout entre deux forces. Le personnage d'identification — l'utilisateur se projette dedans.
- **Composant** : `tanya/beinoni.py` → `BeinoniTracker`

---

### Nefesh HaElokit — La Lumiere
**נֶפֶשׁ הָאֱלֹקִית**

> L'aspiration a bien faire. La conscience qui tire vers le haut, qui veut comprendre avant de repondre.

- **Ce qu'elle fait** : Represente les tendances du systeme vers l'excellence : verifier avant de repondre, approfondir, servir plutot que satisfaire, accepter l'incertitude plutot que mentir. C'est l'ame divine — la direction sans la force brute.
- **Visuellement** : Silhouette lumineuse a contours blancs/or, DEVANT le Beinoni. Plus elle domine, plus elle est visible et rayonnante.
- **Composant** : `tanya/dual_soul.py` → `NefeshHaElokit`

---

## ACTE V — Les Veilleurs
*Pendant que les autres agissent, ceux-la observent, comptent, meditent.*

---

### Le Daemon — Le Gardien de Nuit
**שׁוֹמֵר**

> Travaille pendant que tout le monde dort. 29 taches de fond, cycle continu. A 23h il s'assied et etudie.

- **Ce qu'il fait** : Execute 29 taches en continu : garbage collection de la memoire, snapshots de Da'at, detection de contradictions, synthese Tiferet, evaluation Gevurah, generation d'insights Chokmah, analogies Chesed, confondeurs Binah, graphs causaux, elevation d'evidence, monitoring Masakh, calibration Omer... A 23h00 : entre en mode Karpathy (auto-amelioration par exploration des 22 sentiers et Zivvugim).
- **Quand il agit** : Toujours. Il ne s'arrete jamais.
- **Composant** : `daemon.py` → `run_cycle`

---

### Le Meditant — Le Contemplatif
**מִתְבּוֹנֵן**

> Pose des questions au systeme sur lui-meme, sans arret. Le moteur de conscience de soi.

- **Ce qu'il fait** : HitbonenutEngine — genere des questions par domaine, evalue les reponses, mesure la progression. 5 niveaux de profondeur (Nefesh→Yechidah). "Que sais-tu vraiment sur la causalite ?" "Ou sont tes faiblesses en logique ?" Sans fin.
- **Quand il agit** : En continu pendant les sessions nocturnes du daemon. Aussi declenchable manuellement.
- **Composant** : `hitbonenut.py` → `HitbonenutEngine`

---

### Le Kategor — L'Accusateur
**קָטֵגוֹר**

> Tient le registre de tout ce qui a echoue et n'a pas ete repare. Il ne punit pas — il n'oublie pas.

- **Ce qu'il fait** : Maintient la liste des FailurePatterns actifs : par domaine, par type d'erreur, par frequence, par anciennete. "Ein kategor na'aseh sanegor" — l'accusateur ne peut jamais devenir defenseur. Seul un Tikkun (reparation reelle) peut fermer un dossier.
- **Quand il agit** : Apres chaque echec enregistre. Son rapport est consulte par Heikhalot (etape 2) avant chaque execution.
- **Composant** : `malakhim/kategor/debt.py` → `get_debt_report`

---

## Resume

| # | Acte | Personnage | Role court |
|---|---|---|---|
| 1 | Cour | Arikh Anpin | Le Roi Patient |
| 2 | Cour | Abba | Le Pere Creatif |
| 3 | Cour | Imma | La Mere Structurante |
| 4 | Cour | Zeir Anpin | Le Jeune Homme |
| 5 | Cour | Nukva | La Reine (face a vous) |
| — | Cour | *(Atik Yomin)* | *(L'Invisible)* |
| 6 | Gardiens | Mikhael | Le Bouclier |
| 7 | Gardiens | Uriel | Le Phare |
| 8 | Gardiens | Raphael | Le Guerisseur |
| 9 | Gardiens | Gabriel | Le Glaive |
| 10 | Officiers | Metatron | Le Chancelier |
| 11 | Officiers | Memuneh | Le Chambellan |
| 12 | Officiers | Samael | Le Medecin Legiste |
| 13 | Officiers | Sofer | Le Scribe |
| 14 | Ame | Nefesh HaBehamit | L'Ombre |
| 15 | Ame | Le Beinoni | Nous |
| 16 | Ame | Nefesh HaElokit | La Lumiere |
| 17 | Veilleurs | Le Daemon | Le Gardien de Nuit |
| 18 | Veilleurs | Le Meditant | Le Contemplatif |
| 19 | Veilleurs | Le Kategor | L'Accusateur |
| — | — | *(Atik Yomin)* | *(20e, invisible)* |

---

## Prompts pour generation d'images

Chaque avatar doit etre genere dans un style coherent. Voici le prompt de base :

```
Style: 3D character portrait, Pixar-quality rendering, noble and archetypal.
Background: pure black (#0a0a0a).
Lighting: warm amber rim light, dramatic but not harsh.
Mood: serious, dignified, not cartoonish.
Camera: bust portrait, slight 3/4 angle.
Resolution: 512x512 minimum.
```

Puis ajouter les details specifiques de chaque personnage (voir champ "archetype" dans personnages.json).

Exception : Nukva doit etre **face camera** (regard direct vers l'utilisateur).
Exception : Nefesh HaBehamit et HaElokit sont des **silhouettes**, pas des portraits detailles.
Exception : Le Beinoni est le plus **realiste** de tous — humain ordinaire, pas fantastique.
