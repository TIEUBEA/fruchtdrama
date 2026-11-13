# Passer FruchtDrama Studio sur le MacBook

Tout le studio part sur le Mac : épisodes, vidéos, personnages, comptes, réglages et sauvegardes.
Une seule chose ne se copie pas : **les connexions** (Google, ChatGPT, Grok). Pour ta sécurité, macOS et Chrome
ne permettent pas de transférer les sessions d'un ordinateur à l'autre. Tu te reconnectes une fois sur le Mac.

## 1. Sur le PC : préparer les deux archives

1. Laisse finir la production en cours, ou mets-la en pause.
2. Double-clique sur **Preparer-Migration-Mac.cmd**.
3. Il crée, dans le dossier `FruchtDrama-pour-Mac`, à côté du dossier du studio :
   - `FruchtDrama-Mac-code.zip` (quelques Mo) : le studio et l'extension ;
   - `FruchtDrama-Mac-donnees.zip` (environ 5 Go) : tout le dossier `data`.

   Pour une archive plus légère, sans les anciennes sauvegardes automatiques, lance-le avec `--sans-sauvegardes`.
4. Copie ces deux fichiers sur le Mac : disque USB, AirDrop, Google Drive…

Le PC n'est pas modifié : tu peux continuer à l'utiliser.

## 2. Sur le Mac : installer ce dont le studio a besoin

Dans le Terminal, une seule fois :

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

```bash
brew install python@3.12 ffmpeg
```

Installe aussi **Google Chrome** s'il n'est pas déjà sur le Mac.

## 3. Sur le Mac : décompresser et installer le studio

1. Crée un dossier, par exemple `Documents/FruchtDrama`.
2. Décompresse **d'abord** `FruchtDrama-Mac-code.zip`, **puis** `FruchtDrama-Mac-donnees.zip` dans ce même dossier.
   Les deux remplissent le même sous-dossier `fruchtdrama-studio`.
3. Dans `fruchtdrama-studio`, fais un clic droit sur **Installer-Mac.command**, puis **Ouvrir**.
   Il faut le faire une première fois avec le clic droit : macOS bloque les scripts venus d'un autre ordinateur.
   L'installation crée l'environnement Python, installe les outils, télécharge le modèle de transcription (environ 140 Mo)
   et relie l'extension à Chrome.

## 4. Sur le Mac : Chrome et tes comptes

1. Dans Chrome, ouvre `chrome://extensions`, active le **Mode développeur**, clique sur **Charger l'extension non empaquetée**
   et choisis le dossier `fruchtdrama-studio/extension`.
2. Recrée tes profils Chrome et connecte-toi à tes comptes Google. Rappel : environ 10 comptes Google au maximum par profil Chrome.
   Pour éviter les comptes refusés par Flow, garde l'organisation qui marche sur le PC :
   - un profil pour `euloge.moussa` et `borismoussa5` ;
   - un profil pour `borismoussa55`, `237bigjoe237`, `tbecker7099`, `borismoussa54`, `borismoussa57`, `borismoussa56` et `moussaletono1` ;
   - un profil pour `arnauddjoum88`.
3. Dans un des profils, connecte-toi aussi à ChatGPT et à Grok.
4. Installe l'extension dans chaque profil qui a des comptes Flow (voir le point 1), puis clique sur son icône FruchtDrama dans chaque profil.

## 5. Sur le Mac : lancer et vérifier

1. Double-clique sur **Lancer-Studio-Mac.command**. Ensuite, l'icône FruchtDrama de Chrome suffit : elle démarre le studio toute seule.
2. Si le studio demande la clé d'accès, entre ta clé `FD-…`. Une clé sert sur 2 ordinateurs, le Mac sera le deuxième.
3. Dans **Mes comptes**, clique sur **Détecter les comptes Flow**, puis sur **Vérifier**. Chaque compte retrouve son solde et sa place.
4. Tes épisodes sont tous là. Ceux qui étaient en cours sont **en pause** : clique sur **Reprendre** quand les comptes sont prêts.

## Ce qui change sur le Mac

- Le studio garde le MacBook éveillé pendant la file de nuit (commande `caffeinate`). Laisse le MacBook branché, couvercle ouvert.
- Les vidéos sont montées comme sur le PC (720p natif, sous-titres, couverture).
- Le PC et le Mac sont deux studios séparés. Ne lance pas la même production sur les deux en même temps.
