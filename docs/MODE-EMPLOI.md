# FruchtDrama — Mode d'emploi détaillé

Version du logiciel décrite : **0.1.52** (branche `sudf`). Ce guide est mis à jour à chaque version ;
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

Depuis la 0.1.69, il n'y a rien à lancer : **ouvrez Chrome et cliquez l'icône FruchtDrama**. L'extension démarre elle-même le studio de cet ordinateur (aussi à l'ouverture de Chrome et après un redémarrage du PC), puis ouvre la fenêtre FruchtDrama. Cela marche quel que soit l'endroit où le dossier a été décompressé : Installer.cmd enregistre ce dossier auprès de Chrome (sans droits administrateur). Si vous déplacez le dossier, relancez Installer.cmd ou Lancer-Studio.cmd une fois.

1. Si le studio ne peut pas démarrer, une page **« Le studio FruchtDrama ne tourne pas »** dit pourquoi (installation à faire, port occupé…) avec un bouton **Réessayer**.
2. **Lancer-Studio.cmd** reste disponible : il démarre le serveur et ouvre http://127.0.0.1:8840.
3. Le serveur continue même si vous fermez l'onglet ou Chrome. Le PC doit rester allumé.

Si le message « Port 8840 utilisé par une autre installation » apparaît : une autre copie tourne déjà ; arrêtez-la (section 11).

## 5. Installer l'extension Chrome (une seule fois)

1. Ouvrir `chrome://extensions`.
2. Activer **Mode développeur** (en haut à droite).
3. Cliquer **Charger l'extension non empaquetée** et choisir le dossier `fruchtdrama\extension`.
4. Épingler l'extension : icône puzzle de Chrome → épingle à côté de **FruchtDrama**.
5. Autoriser les téléchargements multiples de Flow : ouvrir `chrome://settings/content/automaticDownloads` et ajouter `https://flow.google.com` aux sites autorisés.

## 6. Ouvrir la fenêtre FruchtDrama et appairer

1. Cliquer sur l'icône **FruchtDrama** dans la barre de Chrome.
2. Une **nouvelle fenêtre** s'ouvre sur le **Studio**. **Tout se passe dans cette fenêtre et dans la page du studio** : ChatGPT, Claude, TikTok, Flow, l'ouverture des comptes. Depuis 0.1.54 il n'y a plus d'onglet Passerelle : ses boutons sont dans Mes comptes › **Navigateur**.
3. **Rien à copier** (depuis 0.1.53) : au premier clic, l'extension enregistre seule la clé du studio, la garde cachée et active les tâches. Mes comptes affiche « Clé du studio : Enregistrée ».
4. Le badge en haut du studio passe à « en ligne » sous 30 secondes.
5. Après une réinstallation de l'extension : Mes comptes → **Autoriser une nouvelle extension**, puis recliquer sur l'icône.
6. Secours (autre ordinateur, ancienne extension) : Mes comptes → Passerelle → **Appairage manuel** ; coller le code dans l'onglet Passerelle, rôle **Recherche, IA et Flow**, **Appairer**, cocher **Autoriser les tâches**.

Bon à savoir :
- Recliquer sur l'icône ramène la fenêtre FruchtDrama au premier plan (jamais de deuxième fenêtre).
- Si vous fermez la fenêtre, elle se rouvre seule à la tâche suivante.
- Ne déplacez pas les onglets de la fenêtre vers une autre fenêtre pendant une génération.

## 7. Connecter vos comptes

Toujours **vous-même**, dans la fenêtre FruchtDrama. Le studio ne demande ni ne stocke aucun mot de passe et ne contourne aucune vérification.

**Ajouter une adresse une seule fois** (depuis 0.1.53) : Mes comptes → bloc **Mes comptes** → adresse, nom facultatif, cocher les services que cette adresse ouvre (ChatGPT, Claude, Google Flow, Grok, Arena), crédits Flow si connus → **Ajouter ce compte**. Une seule ligne par adresse ; « Ajouter » / « Retirer » dans une colonne pour un service, « Retirer » au bout de la ligne pour tout supprimer. Les étapes ci-dessous (connexion dans la fenêtre, mémoriser le compte Flow) restent nécessaires.

**ChatGPT / Claude / TikTok** : ouvrir un onglet dans la fenêtre FruchtDrama, aller sur chatgpt.com (et claude.ai, tiktok.com), se connecter. C'est tout.

**Un compte Flow**
1. **Mes comptes** → créer un profil Flow, indiquer le **solde réel** de crédits.
2. Dans la fenêtre FruchtDrama, ouvrir https://labs.google/fx/tools/flow, se connecter, ouvrir (ou créer) un projet.
3. Studio → Mes comptes › **Navigateur** → **Mémoriser le compte Flow ouvert**. Le dernier onglet Flow consulté est utilisé ; le résultat s'affiche sous les boutons.
4. Vérifier l'adresse e-mail affichée dans Mes comptes.

**Grok Imagine et LMArena (expérimental)**
1. Dans la fenêtre FruchtDrama, ouvrir https://grok.com/imagine (ou https://lmarena.ai) et se connecter soi-même.
2. **Mes comptes** → section **Comptes Grok et Arena** : choisir le moteur, saisir l'**adresse** du compte (jamais de mot de passe), **Ajouter ce compte**. Répéter pour chaque compte, dans l'ordre d'utilisation voulu.
3. Quand un compte atteint sa limite, la production passe « Changement de compte » : dans l'onglet du site, se déconnecter, se connecter au compte indiqué dans le bandeau, puis cliquer **J'ai changé de compte**. Le connecteur vérifie le compte affiché avant d'envoyer.
4. Si tous les comptes sont à leur limite : « Limite atteinte, reprise automatique » ; la production repart seule à l'heure indiquée. **Oublier la limite** (Mes comptes) force une nouvelle tentative.
5. Toujours commencer par un **essai à blanc** : ces sites changent souvent et les connecteurs n'ont pas encore été vérifiés sur vos comptes.

**Plusieurs comptes Flow dans la même fenêtre** (passage automatique quand les crédits s'épuisent)
1. Dans la fenêtre FruchtDrama, menu du compte Google (photo en haut à droite d'une page Google) → **Ajouter un compte** ; répéter pour chaque compte.
2. Pour chaque compte : ouvrir Flow avec ce compte (l'adresse contient `/u/0/`, `/u/1/`, `/u/2/`…), ouvrir un projet, puis **Mémoriser le compte Flow de cet onglet**.
3. Dans Mes comptes, créer un profil par compte avec son solde réel.
4. Dans Mes comptes, cocher **Ouvrir Flow et passer au compte suivant automatiquement**. Quand un compte n'a plus assez de crédits, le studio passe au suivant, dans la même fenêtre. Les clips déjà reçus sont conservés.

## 8. Créer une production

Studio → **Nouvelle production** :

| Champ | Conseil |
|---|---|
| Point de départ | Facultatif : une idée, sinon l'IA cherche une référence sur TikTok. |
| IA de scénario | ChatGPT ou Claude. Les images passent toujours par ChatGPT. |
| Format | 4 scènes (32 s) pour commencer. |
| Langue | Deutsch, Français ou English : dialogues, voix, sous-titres, couverture. |
| Moteur vidéo | **Google Flow** (8 s par clip, crédits Flow). Grok Imagine (6 s) et LMArena (4 à 10 s) sont **expérimentaux** : essai à blanc d'abord ; comptes à enregistrer dans Mes comptes (section 7). La longueur des dialogues s'adapte au moteur. |
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
| Crédits insuffisants | Aucun compte Flow n'a assez de crédits. | Mettre à jour le solde dans Mes comptes ou ajouter un compte. |
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
- **Contrôle qualité** : la production continue seule **seulement si** chaque clip a une transcription conforme au texte à 85 % au moins , aucun défaut technique et une revue visuelle sans réserve. Sinon « À vérifier » : écouter les clips, puis **J’ai écouté les dialogues…** ou **J’ai vérifié les réserves, continuer**, ou **Refaire** le clip fautif. Avec **Refaire tout seul**, seuls les clips en défaut (paroles sous 85 % ou défaut visuel net) sont regénérés une fois, tous ensemble ; un clip « incertain » (les images extraites ne suffisent pas pour juger) n'est jamais repayé : il vous est montré.
- La synchronisation des lèvres et l'identité des voix ne sont jamais certifiées automatiquement : à écouter.

## 10 bis. Séries et publication

- **Écrire la suite (partie N)** (production terminée) : donne une idée facultative ; la partie suivante reprend les mêmes personnages et leurs images (rien n'est repayé pour eux) et lance directement le scénario.
- **Kit de publication ↓** : titre, description, hashtags, premier commentaire et créneaux suggérés. Ce sont des hypothèses à tester avec vos statistiques.

## 11 bis. File de nuit (production sans surveillance)

1. Sur chaque production à lancer : **Ajouter à la file de nuit** (pas en essai à blanc ; une histoire à relire doit d'abord être validée).
2. En haut du Studio, panneau **File de nuit** → **Démarrer la file de nuit**.
3. Le studio traite une production à la fois, dans l'ordre. Il relance seul jusqu'à 3 fois une erreur technique, attend les limites et les crédits, et retire avec la raison toute production qui a besoin de vous (connexion, anti-robot, clip Flow incertain, réserves du contrôle qualité, pause). Le journal de la file garde la trace de tout.
4. Pendant la file, Windows ne se met pas en veille (l'écran peut s'éteindre). Laisser le PC branché, Chrome et la fenêtre FruchtDrama ouverts.
5. **Arrêter la file** : la production en cours continue, les suivantes attendent.

Quand ChatGPT refuse une image, le studio la redemande seul deux fois avec une formulation adoucie (même style). Quand un service est à sa limite, la production attend et repart seule ; voir **Mes comptes → Limites apprises**.

## 11. Arrêter, redémarrer, dépanner

- **Arrêter** : attendre la fin des générations et transferts, puis Gestionnaire des tâches → processus Python de `server.py` → Fin de tâche. Ne pas arrêter tous les Python.
- **Redémarrer** : cliquer l'icône FruchtDrama dans Chrome (ou Lancer-Studio.cmd). Une génération interrompue passe « À vérifier » (jamais renvoyée automatiquement) ; un montage interrompu reprend seul.
- **Journal d'erreurs** : `data\server-errors.log`.
- **Problème de dépendances** : relancer Installer.cmd.
- **Badge « Connecteur à configurer »** : vérifier l'appairage et la case « Autoriser les tâches » dans l'onglet Passerelle.
- **Sauvegarder** : copier le dossier `data\` (vos productions et réglages). Ne jamais le partager.
- **Supprimer une production** : bouton **Supprimer…** ; son dossier part dans `data\corbeille` (pour la récupérer, le redéplacer dans `data\jobs` et restaurer la dernière copie de `data\sauvegardes`).
- **Rapport de panne** : Mes comptes → **Assistance et entretien** → **Copier un rapport de panne**, puis le coller dans votre message d'assistance (aucun secret dedans).
- **Nettoyer l'historique** : même panneau ; une copie est gardée.

## 12. Nouveautés d'utilisation par version

| Version | Ce qui change pour vous |
|---|---|
| 0.1.79 | **Grand bandeau rouge** quand une limite est atteinte, avec **Que faire ?**. Plus de crédits Flow sur aucun compte : **Ajouter un compte Google**, le studio le détecte et reprend seul. Bandeau **La planche a changé après le clip** avec **Refaire ces clips**. Fenêtre de la scène : défaut, phrase entendue, **Copier le prompt**, **Modifier le texte**. Feu vert, orange ou rouge sur les boutons des cartes. Recharger l'extension. |
| 0.1.80 | **▶ Boucle complète décide seule** aux contrôles qualité : paroles un peu différentes du texte et réserves visuelles acceptées sans nouveau crédit, le montage continue. **Bandeau en haut de l’épisode** : rouge « Action requise » quand le studio t’attend, orange « Décidé automatiquement — à vérifier avant de publier ». Le studio redémarre de nouveau en quelques secondes. |
| 0.1.81 | Le **chrono de fabrication** compte le temps de travail réel (les nuits et les pauses ne comptent plus) et passe en heures au-delà de 60 minutes. |
| 0.1.78 | **Coût affiché** avant chaque action payante (Boucle complète, Dessiner, Tourner, Refaire). Fenêtre d'une scène : **versions précédentes** de la planche et du clip, bouton **Remettre** (gratuit). Bandeau **Remonter la vidéo** quand un clip a changé. |
| 0.1.77 | Studio : une histoire en fabrication porte la pastille **En cours** ; un clic ouvre la partie en cours. La dernière ligne du journal (« ce qui se passe maintenant ») s'affiche dans l'épisode, dans le menu et sur la carte. |
| 0.1.76 | Studio : un clic sur la carte d'une partie ouvre l'épisode et sa progression, même pendant la fabrication. |
| 0.1.75 | « Revérifier » et « Détecter mes comptes » n'ouvrent plus plusieurs fenêtres : tout se passe dans la fenêtre FruchtDrama. Recharger l'extension. |
| 0.1.74 | **Une seule fenêtre**, et la vue reste sur le studio : ChatGPT, Flow et les autres sites travaillent dans des onglets en arrière-plan, qui se ferment seuls une fois terminés. **Se connecter** : connecte-toi dans l'onglet ouvert, la carte passe au vert toute seule et le studio revient. **Mes comptes** simplifié : les cartes, les comptes Flow, puis les réglages pliés (clic sur « Régler »). Recharger l'extension. |
| 0.1.73 | La vidéo à publier est **toujours en 1080p** (1080 × 1920, ou 1920 × 1080 en horizontal), même si les clips sont plus petits. Recharger l'extension. |
| 0.1.72 | **Durée garantie** : la vidéo finale atteint la durée choisie (plus de 60 s pour « 1 min », donc monétisable) ; le studio rend du silence coupé si besoin. **Trois appels de fin** au choix dans la fiche, modifiables (« dis 1 / dis 2 », partie 2, question). **Refaire une virale** : le studio récupère la vidéo et la montre à l'IA (moments clés + ce qui est dit) ; case **Recréer à l'identique**, **Captures en plus** (jusqu'à 4 images, par exemple ta photo pour un personnage), **Instructions en plus**. Recharger l'extension. |
| 0.1.71 | Fermer la fenêtre FruchtDrama ne la rouvre plus : la relecture des soldes Flow attend sa prochaine ouverture. Recharger l'extension. |
| 0.1.70 | Rien ne change pour vous dans cette édition. Préparé pour la formation : écran **Entre ta clé**, bandeau avant la fin d'accès, consultation seule après. |
| 0.1.69 | **Plus rien à lancer** : l'extension démarre le studio toute seule (ouverture de Chrome, clic sur l'icône, après un redémarrage du PC), où que soit le dossier. Relancer **Installer.cmd** une fois, puis recharger l'extension : elle change d'identifiant une seule fois et se réappaire seule. |
| 0.1.68 | **Refaire tout seul** ne regénère plus un clip seulement « incertain » (vous le regardez) ; plusieurs clips en défaut sont refaits ensemble au lieu de bloquer l'épisode. |
| 0.1.65 | Le Filon : **niches** (puces + Mes niches, une recherche TikTok par niche), prochaine actualisation, **mots-dièse qui portent**. Studio : compteurs **en 6 h**. Menu : toutes les productions **en cours**. Recharger l'extension. |
| 0.1.64 | Mes comptes : **Changer de compte** guidé sur chaque carte, carte **Accès à tes fichiers**, **Contrôles** des planches (avant les clips), des clips et **Regard sur les clips** (à l'oreille seulement possible). Recharger l'extension. |
| 0.1.63 | Créer : **Qualité** (Normale / Économie), **Format** (Vertical / Horizontal / Les deux), **Personnages** (Simple / Détaillé), **Sous-titres** (Sans / Avec), coût affiché avant la production automatique, chrono pendant la fabrication. Mes comptes : **Montage de mes vidéos** (transitions, coupes rapides, silences, karaoké) et **Mes sauvegardes**. Recharger l'extension. |
| 0.1.60 | Studio par **histoires** puis **parties** (comme l'Atelier) ; Mes comptes : **Détecter mes comptes** Google Flow avec leurs crédits réels ; montage dynamique. Recharger l'extension. |
| 0.1.59 | Vidéo finale **1080 × 1920**, **accroche écrite** au début, histoires à 3–5 personnages en mouvement ; bouton **Réécrire pour s'éloigner** (originalité). Recharger l'extension. |
| 0.1.58 | Page épisode : **+ Version horizontale 16:9** et **Langues** (crée une version liée ; crédits images et/ou vidéo demandés avant). Recharger l'extension (réglage 16:9 de Flow). |
| 0.1.57 | Bandeau **Limite atteinte** en haut de chaque page (Ouvrir le site, J'ai changé de compte) ; **En cours** dans le menu ; Mes comptes : **Contrôles des clips** (Refaire tout seul, Signaler seulement, Pas de contrôle) et **Thème**. |
| 0.1.56 | **Originalité** : un score avant publication (page de l'épisode) avec les changements conseillés ; alerte dès la fiche si vous refaites une virale. **Le Filon** : vrais chiffres, onglets Viral / Toutes / Comptes, filtres, vidéos lancées seules. Page épisode : télécharger les images, le texte, choisir la scène de la miniature. |
| 0.1.55 | **Créer** est une page entière : choisir qui écrit, l'option (dix histoires, mon idée, refaire une virale, tout automatique), la **durée (30 s, 1 min, 2 min, 3 min)**, le moteur et la langue. **Dix histoires** puis **fiche de décision** à valider avant tout paiement. Studio en grandes cartes ; page épisode : étapes, scènes en vignettes, clic = planche et clip côte à côte. Le Filon s'ouvre en premier, miniatures immédiates. |
| 0.1.54 | Plus d'onglet **Passerelle** : tout se fait dans le studio (Mes comptes › Navigateur : mémoriser le compte Flow, ranger les onglets, récupérer une réponse). Recharger l'extension. |
| 0.1.53 | **Une adresse, plusieurs services** : ajoutée une seule fois dans Mes comptes. **Clé du studio** enregistrée seule au premier clic sur l'icône, jamais recopiée (section 6). Recharger l'extension. |
| sudf-ui | Interface façon Atelier : **Le Filon**, **Créer une vidéo** d'un lien TikTok ou d'une idée, thème sombre (◐), police et images agrandies (clic pour agrandir). |
| 0.1.52 | **Écrire la suite** d'un épisode (série) ; **Kit de publication**. |
| 0.1.51 | Sous-titres **karaoké** ; bouton **Supprimer…** (corbeille) ; rapport de panne et nettoyage dans Mes comptes. |
| 0.1.50 | **File de nuit** (section 11 bis) ; reformulation automatique des images refusées ; limites ChatGPT/Claude apprises avec reprise automatique ; seuil de paroles 85 %. |
| 0.1.49 | **Grok et Arena utilisables** (expérimental) ; comptes Grok/Arena dans Mes comptes ; changement de compte guidé et reprise automatique après limite. Recharger l'extension (nouvelles autorisations grok.com et lmarena.ai). |
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
