# Frontend Avatars — Specification

## Concept

20 personnages incarnent les composants du systeme Etz Chaim AI.
Presentes en 5 actes (scroll vertical), chaque acte = un groupe logique.
Style : 3D cartoon noble (Pixar/Prince d'Egypte), fond noir, cartes individuelles.

## Structure des cartes

Chaque carte contient :
- **Image** : avatar 3D (a generer via AI image tool ou Midjourney)
- **Role** : titre fonctionnel court (ex: "Archange Protecteur")
- **Nom** : nom du personnage (ex: "Mikhael")
- **Nom hebreu** : en caracteres hebraiques
- **Description** : 2 lignes max, langage simple
- **Lien** : "Voir les details" -> panneau etat temps reel du composant

## Layout par acte

### Acte I — La Cour (5+1 personnages)
Disposition : pyramide
- Rang 1 (1 carte centree) : Arikh Anpin
- Rang 2 (2 cartes cote a cote) : Abba + Imma (lien Zivvug entre eux)
- Rang 3 (1 carte centree) : Zeir Anpin
- Rang 4 (1 carte centree) : Nukva
- Note sous la pyramide : mention d'Atik Yomin (invisible)

### Acte II — Les Gardiens (4 personnages)
Disposition : carre 2x2
- Haut gauche : Mikhael (entree)
- Haut droite : Uriel (observation)
- Bas gauche : Raphael (soin)
- Bas droite : Gabriel (sortie)

### Acte III — Les Officiers (4 personnages)
Disposition : ligne horizontale 4 colonnes
- Metatron -> Memuneh -> Samael -> Sofer

### Acte IV — L'Ame (3 personnages)
Disposition : triptyque centre
- Gauche : Nefesh HaBehamit (ombre rouge)
- Centre (plus grand) : Le Beinoni
- Droite : Nefesh HaElokit (lumiere)

### Acte V — Les Veilleurs (3 personnages)
Disposition : ligne horizontale 3 colonnes
- Le Daemon -> Le Meditant -> Le Kategor

## Style visuel

- Fond : #0a0a0a (noir profond)
- Cartes : #111111 fond, bordure #ffb000 (amber)
- Texte : IBM Plex Mono
- Images : 3D style noble, pas cartoon bureau
- Couleurs accents par acte :
  - Acte I (Cour) : or #ffcc00
  - Acte II (Gardiens) : amber #ffb000
  - Acte III (Officiers) : bleu #6688cc
  - Acte IV (Ame) : rouge/blanc #ff4444 / #ffffff
  - Acte V (Veilleurs) : gris-vert #88aa88

## Mapping composant technique

Chaque avatar correspond a un composant reel du systeme.
Le "Voir les details" ouvre les donnees temps reel de ce composant.
Voir personnages.json pour le mapping complet.
