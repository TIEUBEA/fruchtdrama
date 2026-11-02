# FruchtDrama — Mode d'emploi détaillé

Version du logiciel décrite : **0.1.51** (branche `sudf`). Ce guide est mis à jour à chaque version ;
la section 12 liste, version par version, ce qui change pour vous.

Sommaire
1. Ce qu'il faut avant de commencer
2. Installer (une seule fois)
3. Récupérer et mettre à jour la version `sudf`
4. Lancer le studio (chaque jour)
5. Installer l'extension Chrome (une seule fois)
6. Ouvrir la fenêtre FruchtDrama et appairer
7. Connecter vos comptes (ChatGPT, TikTok, Flow, plusieurs comptes Flow)
8. Créer une production
9. Suivre une production : statuts et bandeaux
10. Corriger : Refaire, relecture, contrôle qualité
11. Arrêter, redémarrer, dépanner
12. Nouveautés d'utilisation par version
13. Pour les développeurs (Linux, tests)

---

## 1. Ce qu'il faut avant de commencer

| Élément | Détail |
|---|---|
| PC | Windows 10 ou 11, 64 bits, allumé pendant toute la production (le PC ne doit pas se mettre en veille). |
| Python | 3.11 ou 3.12 64 bits, depuis python.org, avec la case **Add python.exe to PATH** cochée. |
| Chrome | Google Chrome à jour. |
| FFmpeg | `ffmpeg` et `ffprobe` dans le PATH. Commande : `winget install --id Gyan.FFmpeg --exact`, puis fermer le terminal. |
| Git | Pour récupérer la branche `sudf` (https://git-scm.com). |
| Comptes | ChatGPT (images, et scénario si choisi), éventuellement Claude (scénario), TikTok (recherche), un ou plusieurs comptes Google avec Flow et des crédits. |
| Espace disque | Quelques Go (modèle vocal + vidéos). |

## 2. Installer (une seule fois)

1. Ouvrir un terminal (touche Windows, taper `cmd`, Entrée).
2. Aller dans le dossier voulu puis cloner le dépôt et passer sur la branche de travail :
   ```
   cd %USERPROFILE%\Documents
   git clone https://github.com/TIEUBEA/fruchtdrama.git
   cd fruchtdrama
   git checkout sudf
   ```
3. Double-cliquer sur **Installer.cmd** (dans le dossier `fruchtdrama`).
   - Lire les conditions, taper **ACCEPTER**, Entrée.
   - L'installateur crée `.venv`, installe les dépendances et télécharge le modèle vocal (plusieurs minutes, Internet requis).
   - Attendre le message « Installation terminée ».
4. En cas de message « FFmpeg / ffprobe manquant » : installer FFmpeg (section 1), fermer la fenêtre, relancer **Installer.cmd**.

## 3. Récupérer et mettre à jour la version `sudf`

À chaque nouvelle version annoncée :
1. Arrêter le studio (section 11) une fois les générations en cours terminées.
2. Dans un terminal, dans le dossier `fruchtdrama` :
   ```
   git checkout sudf
   git pull
   ```
3. Si `requirements.txt` a changé (indiqué dans la section 12), relancer **Installer.cmd**.
4. Recharger l'extension : `chrome://extensions` → carte **FruchtDrama — passerelle locale** → bouton de rechargement (flèche circulaire).
5. Relancer le studio (section 4). Vos productions dans `data/` sont conservées.

## 4. Lancer le studio (chaque jour)

1. Double-cliquer sur **Lancer-Studio.cmd**.
2. Le serveur démarre en arrière-plan et le studio s'ouvre sur http://127.0.0.1:8840.
3. Le serveur continue même si vous fermez l'onglet. Le PC et Chrome doivent rester allumés.

Si le message « Port 8840 utilisé par une autre installation » apparaît : une autre copie tourne déjà ; arrêtez-la (section 11).

## 5. Installer l'extension Chrome (une seule fois)

1. Ouvrir `chrome://extensions`.
2. Activer **Mode développeur** (en haut à droite).
3. Cliquer **Charger l'extension non empaquetée** et choisir le dossier `fruchtdrama\extension`.
4. Épingler l'extension : icône puzzle de Chrome → épingle à côté de **FruchtDrama**.
5. Autoriser les téléchargements multiples de Flow : ouvrir `chrome://settings/content/automaticDownloads` et ajouter `https://flow.google.com` aux sites autorisés.

## 6. Ouvrir la fenêtre FruchtDrama et appairer

1. Cliquer sur l'icône **FruchtDrama** dans la barre de Chrome.
2. Une **nouvelle fenêtre** s'ouvre. **Tout se passe dans cette fenêtre** : le studio, ChatGPT, Claude, TikTok, Flow et l'ouverture des comptes. Elle contient :
   - un premier onglet épinglé **Passerelle** ;
   - l'onglet **Studio**.
3. Dans le studio : menu **Connexions** → noter le **code d'appairage**.
4. Dans l'onglet **Passerelle** :
   - coller le code d'appairage ;
   - nom du navigateur : par exemple « PC bureau » ;
   - rôle : **Recherche, IA et Flow** ;
   - IA connectée : ChatGPT, Claude ou les deux ;
   - cliquer **Appairer / mettre à jour le profil** ;
   - cocher **Autoriser les tâches en arrière-plan**.
5. Le badge en haut du studio passe à « en ligne » sous 30 secondes.

Bon à savoir :
- Recliquer sur l'icône ramène la fenêtre FruchtDrama au premier plan (jamais de deuxième fenêtre).
- Si vous fermez la fenêtre, elle se rouvre seule à la tâche suivante.
- Ne déplacez pas les onglets de la fenêtre vers une autre fenêtre pendant une génération.

## 7. Connecter vos comptes

Toujours **vous-même**, dans la fenêtre FruchtDrama. Le studio ne demande ni ne stocke aucun mot de passe et ne contourne aucune vérification.

**ChatGPT / Claude / TikTok** : ouvrir un onglet dans la fenêtre FruchtDrama, aller sur chatgpt.com (et claude.ai, tiktok.com), se connecter. C'est tout.

**Un compte Flow**
1. Studio → **Connexions** → créer un profil Flow, indiquer le **solde réel** de crédits.
2. Dans la fenêtre FruchtDrama, ouvrir https://labs.google/fx/tools/flow, se connecter, ouvrir (ou créer) un projet.
3. Onglet **Passerelle** → **Mémoriser le compte Flow de cet onglet**. Le dernier onglet Flow consulté est utilisé.
4. Vérifier l'adresse e-mail affichée dans Connexions.

**Grok Imagine et LMArena (expérimental)**
1. Dans la fenêtre FruchtDrama, ouvrir https://grok.com/imagine (ou https://lmarena.ai) et se connecter soi-même.
2. Studio → **Connexions** → section **Comptes Grok et Arena** : choisir le moteur, saisir l'**adresse** du compte (jamais de mot de passe), **Ajouter ce compte**. Répéter pour chaque compte, dans l'ordre d'utilisation voulu.
3. Quand un compte atteint sa limite, la production passe « Changement de compte » : dans l'onglet du site, se déconnecter, se connecter au compte indiqué dans le bandeau, puis cliquer **J'ai changé de compte**. Le connecteur vérifie le compte affiché avant d'envoyer.
4. Si tous les comptes sont à leur limite : « Limite atteinte, reprise automatique » ; la production repart seule à l'heure indiquée. **Oublier la limite** (Connexions) force une nouvelle tentative.
5. Toujours commencer par un **essai à blanc** : ces sites changent souvent et les connecteurs n'ont pas encore été vérifiés sur vos comptes.

**Plusieurs comptes Flow dans la même fenêtre** (passage automatique quand les crédits s'épuisent)
1. Dans la fenêtre FruchtDrama, menu du compte Google (photo en haut à droite d'une page Google) → **Ajouter un compte** ; répéter pour chaque compte.
2. Pour chaque compte : ouvrir Flow avec ce compte (l'adresse contient `/u/0/`, `/u/1/`, `/u/2/`…), ouvrir un projet, puis **Mémoriser le compte Flow de cet onglet**.
3. Dans Connexions, créer un profil par compte avec son solde réel.
4. Dans Connexions, cocher **Ouvrir Flow et passer au compte suivant automatiquement**. Quand un compte n'a plus assez de crédits, le studio passe au suivant, dans la même fenêtre. Les clips déjà reçus sont conservés.

## 8. Créer une production

Studio → **Nouvelle production** :

| Champ | Conseil |
|---|---|
| Point de départ | Facultatif : une idée, sinon l'IA cherche une référence sur TikTok. |
| IA de scénario | ChatGPT ou Claude. Les images passent toujours par ChatGPT. |
| Format | 4 scènes (32 s) pour commencer. |
| Langue | Deutsch, Français ou English : dialogues, voix, sous-titres, couverture. |
| Moteur vidéo | **Google Flow** (8 s par clip, crédits Flow). Grok Imagine (6 s) et LMArena (4 à 10 s) sont **expérimentaux** : essai à blanc d'abord ; comptes à enregistrer dans Connexions (section 7). La longueur des dialogues s'adapte au moteur. |
| Modèle vidéo Flow | Omni 12 crédits, Lite 10, Fast 20, Quality 100 par clip (Ultra : Lite 5, Fast 10). Le coût affiché dans Flow est vérifié avant tout envoi. |
| Relire et corriger l'histoire avant de payer les images | **Recommandé** au début : la production s'arrête pour que vous relisiez les dialogues. |
| Essai à blanc des clips Flow | **Recommandé pour le premier essai** : tout est préparé dans Flow mais rien n'est envoyé, aucun crédit consommé. |
| Sous-titres karaoké | Coché par défaut : chaque mot s'allume en jaune quand il est dit. Décocher pour des sous-titres classiques. |
| Profil Flow / coût prévu | Le compte à utiliser et le coût attendu par clip. |

Cliquer **Créer la production**. Le studio enchaîne : Recherche → Scénario → Personnages → Scènes → Clips Flow → Contrôle qualité → Couverture → Montage → Prêt.

Lien direct vers une production : `http://127.0.0.1:8840/#job=<identifiant>`.

## 9. Suivre une production : statuts et bandeaux

| Statut affiché | Signification | Que faire |
|---|---|---|
| En production | Le studio travaille. | Rien. Laisser la fenêtre FruchtDrama ouverte. |
| Histoire à relire | Relecture demandée (option à la création). | Corriger les dialogues, **Enregistrer**, puis **Valider l’histoire et lancer les images**. |
| En pause | Vous avez mis en pause, ou essai à blanc réussi. | **Reprendre**. Après un essai à blanc : désactiver l'essai, puis Reprendre. |
| Crédits insuffisants | Aucun compte Flow n'a assez de crédits. | Mettre à jour le solde dans Connexions ou ajouter un compte. |
| À vérifier | Un problème demande votre regard (voir bandeaux ci-dessous). | Lire le dernier message, corriger, **Reprendre**. |
| Changement de compte | Un compte Grok/Arena a atteint sa limite. | Se connecter au compte indiqué dans l'onglet du site, puis **J'ai changé de compte**. |
| Limite atteinte, reprise automatique | Tous les comptes du moteur sont à leur limite. | Rien : reprise seule à l'heure indiquée. Ou ajouter un compte. |
| En file de nuit | Attend son tour dans la file de nuit. | Rien, ou « Retirer de la file de nuit ». |
| Montage en cours | Montage local ffmpeg. | Attendre. |
| Prêt à télécharger | Vidéo finale disponible. | **Télécharger le MP4** et **Télécharger la description**. |

Bandeaux possibles :
- **Action de votre part requise** (rouge) : connexion demandée ou vérification anti-robot. Aller dans l'onglet concerné de la fenêtre, se connecter ou résoudre la vérification **soi-même**, puis **Reprendre**.
- **Envoi Flow incertain** (orange) : un clip a peut-être été généré et facturé sans être reçu. Ouvrir le projet Flow : la passerelle récupère un clip existant, ou importez-le. Ne cliquer « aucun clip dans Flow » que si vous avez vérifié qu'il n'existe pas.
- **Essai à blanc** (bleu) : rappel que rien n'est envoyé ; bouton pour passer en production réelle.

## 10. Corriger : Refaire, relecture, contrôle qualité

- **Refaire** (sous chaque image, clip, couverture, personnages) : écrire la correction (ex. « plus de lumière »). L'ancien fichier est conservé. Refaire une image impose de refaire aussi son clip. Les personnages ne se refont plus une fois les scènes créées.
- **Contrôle qualité** : la production continue seule **seulement si** chaque clip a une transcription conforme au texte à 85 % au moins , aucun défaut technique et une revue visuelle sans réserve. Sinon « À vérifier » : écouter les clips, puis **J’ai écouté les dialogues…** ou **J’ai vérifié les réserves, continuer**, ou **Refaire** le clip fautif.
- La synchronisation des lèvres et l'identité des voix ne sont jamais certifiées automatiquement : à écouter.

## 11 bis. File de nuit (production sans surveillance)

1. Sur chaque production à lancer : **Ajouter à la file de nuit** (pas en essai à blanc ; une histoire à relire doit d'abord être validée).
2. En haut du Studio, panneau **File de nuit** → **Démarrer la file de nuit**.
3. Le studio traite une production à la fois, dans l'ordre. Il relance seul jusqu'à 3 fois une erreur technique, attend les limites et les crédits, et retire avec la raison toute production qui a besoin de vous (connexion, anti-robot, clip Flow incertain, réserves du contrôle qualité, pause). Le journal de la file garde la trace de tout.
4. Pendant la file, Windows ne se met pas en veille (l'écran peut s'éteindre). Laisser le PC branché, Chrome et la fenêtre FruchtDrama ouverts.
5. **Arrêter la file** : la production en cours continue, les suivantes attendent.

Quand ChatGPT refuse une image, le studio la redemande seul deux fois avec une formulation adoucie (même style). Quand un service est à sa limite, la production attend et repart seule ; voir **Connexions → Limites apprises**.

## 11. Arrêter, redémarrer, dépanner

- **Arrêter** : attendre la fin des générations et transferts, puis Gestionnaire des tâches → processus Python de `server.py` → Fin de tâche. Ne pas arrêter tous les Python.
- **Redémarrer** : Lancer-Studio.cmd. Une génération interrompue passe « À vérifier » (jamais renvoyée automatiquement) ; un montage interrompu reprend seul.
- **Journal d'erreurs** : `data\server-errors.log`.
- **Problème de dépendances** : relancer Installer.cmd.
- **Badge « Connecteur à configurer »** : vérifier l'appairage et la case « Autoriser les tâches » dans l'onglet Passerelle.
- **Sauvegarder** : copier le dossier `data\` (vos productions et réglages). Ne jamais le partager.
- **Supprimer une production** : bouton **Supprimer…** ; son dossier part dans `data\corbeille` (pour la récupérer, le redéplacer dans `data\jobs` et restaurer la dernière copie de `data\sauvegardes`).
- **Rapport de panne** : Connexions → **Assistance et entretien** → **Copier un rapport de panne**, puis le coller dans votre message d'assistance (aucun secret dedans).
- **Nettoyer l'historique** : même panneau ; une copie est gardée.

## 12. Nouveautés d'utilisation par version

| Version | Ce qui change pour vous |
|---|---|
| 0.1.51 | Sous-titres **karaoké** ; bouton **Supprimer…** (corbeille) ; rapport de panne et nettoyage dans Connexions. |
| 0.1.50 | **File de nuit** (section 11 bis) ; reformulation automatique des images refusées ; limites ChatGPT/Claude apprises avec reprise automatique ; seuil de paroles 85 %. |
| 0.1.49 | **Grok et Arena utilisables** (expérimental) ; comptes Grok/Arena dans Connexions ; changement de compte guidé et reprise automatique après limite. Recharger l'extension (nouvelles autorisations grok.com et lmarena.ai). |
| 0.1.48 | Nouveau champ **Moteur vidéo** à la création (Flow seul actif pour l'instant). Recharger l'extension après mise à jour. |
| 0.1.47 | L'icône ouvre la **fenêtre FruchtDrama** où tout se passe (section 6). Le panneau de l'extension devient l'onglet **Passerelle**. Plusieurs comptes Flow dans la même fenêtre (section 7). Recharger l'extension après mise à jour. |
| 0.1.46 | Bandeau rouge **Action de votre part requise** (connexion, anti-robot). Un refus de ChatGPT sur une image est signalé en quelques secondes. |
| 0.1.45 | Options **Relire l'histoire** et **Essai à blanc** à la création ; boutons **Refaire** ; une seule feuille de personnages par épisode. |
| 0.1.44 | Bandeau **Envoi Flow incertain** ; montage relancé par Reprendre ; lien direct `#job=`. |

Le détail technique de chaque version est dans `CHANGELOG.md` ; le guide de reprise du développement dans `docs/sudf/REPRISE.md`.

## 13. Pour les développeurs (Linux, tests)

```bash
FRUCHT_DATA=$PWD/data FRUCHT_PORT=8840 python3 server.py      # serveur en local
python3 -m unittest discover -s tests -p 'test_*.py'           # tests Python
for f in tests/*.cjs; do node "$f" || echo "ÉCHEC $f"; done     # tests JS (Node >= 22)
```
Les tests navigateur utilisent Chrome/Chromium s'ils sont présents. Aucun test n'envoie de génération payante.
