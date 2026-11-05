# Journal des modifications

Chaque version liste ce qui a été **corrigé**, **amélioré** et **ajouté**, avec l'exigence
correspondante (P0-xx, P1-x, P2-xx) détaillée dans `docs/sudf/`. Guide pour reprendre le travail :
`docs/sudf/REPRISE.md`. **Mode d'emploi détaillé** (installer, lancer, utiliser), mis à jour à chaque
version : `docs/MODE-EMPLOI.md` (section 12 : ce qui change pour l'utilisateur, version par version).

## 0.1.83 — 05/11/2026
Revue de chaque menu face au live de l'Atelier Gourmand relu en détail (rapport : `docs/sudf/REVUE-MODULES-2026-11-05.md`).
- Corrigé : **carte d'histoire** qui prenait le statut de la version 16:9 ou d'une autre langue (« À tourner » sur une vidéo prête). Elle suit la partie principale et ajoute « · 16:9 à finir ».
- Corrigé : **compteurs du Studio** et sous-titre du menu comptés par histoire, comme les cartes (« 4 prêtes » pour 2 cartes prêtes auparavant).
- Corrigé : **description de publication** coupée à 240 caractères au milieu d'un mot, sans hashtags : affichée en entier.
- Corrigé : **descriptions des personnages** coupées au milieu d'un mot : texte complet sur 4 lignes, en entier au survol.
- Corrigé : « Clips 3 à revoir » en rouge après un montage accepté : « 3 acceptés avec réserve », un clic ouvre la scène.
- Corrigé : **Mes comptes** : le bandeau de détection (« 74 crédits ») contredisait le tableau (« 293 crédits ») ; il porte sa date et précise qu'il ne parle que d'une fenêtre. Numéros de compte en double : « fenêtre 1 · compte n° 1 ».
- Corrigé : **Filon** : « Croissance +0 » sur 40 % des vidéos (compteur TikTok arrondi). Croissance mesurée sur 24 h de lectures, « — » s'il n'y a qu'une lecture.
- Corrigé : le bouton « Langues » ressemblait à un cadre vide.

## 0.1.82 — 05/11/2026
- Corrigé : **diagnostic technique affiché tel quel** (« Lecture du scénario : {"candidates":4,…} ») dans la barre de fabrication, la carte « En cours » et le journal. Il devient une phrase : « L'IA écrit le scénario ; réponse pas encore complète », « Scénario reçu (8 scènes) : vérification en cours », « En attente de la réponse de l'IA » (`readable_progress`, aussi appliqué aux anciennes lignes).
- Corrigé : **refus du scénario imprécis**. « Il faut 1 à 5 personnages et exactement 8 scènes » devient le nombre réellement reçu (« 7 personnage(s) reçu(s), il en faut 1 à 5 : fusionner ou retirer les personnages secondaires »). La réécriture automatique reçoit cette raison exacte.
- Corrigé : l'étape 1 affichait « Fiche à écrire » pendant l'écriture du scénario ; elle affiche « scénario en cours » (et « à valider » quand la fiche attend le propriétaire).
- Corrigé : le texte de la carte « En cours » (barre latérale) débordait de la carte ; il est coupé à deux lignes.

## 0.1.81 — 05/11/2026
- Corrigé : **chrono de fabrication incohérent** (« 678 min » pour un épisode commencé la veille). Il comptait depuis la création de l'épisode, nuits et pauses comprises. Il compte maintenant le temps de travail seulement : un silence de plus de 10 minutes dans le journal (pause, nuit, attente du propriétaire) n'est pas compté. Affichage en heures au-delà de 60 minutes (`activeSeconds`).

## 0.1.80 — 05/11/2026
- Corrigé : **le studio ne démarrait plus** (port 8840 jamais ouvert, 100 % CPU). Au démarrage, la recherche de planches en double relisait chaque image entière pour chaque paire. L'empreinte d'une image est maintenant gardée en mémoire tant que le fichier ne change pas (`image_fingerprint`).
- Ajouté (demande du propriétaire) : **« Boucle complète » décide seule aux contrôles qualité**. Paroles sous 85 % et réserves visuelles (y compris « incertain ») sont acceptées automatiquement, sans nouvelle génération ni crédit, et le montage continue. Un défaut technique (média illisible) arrête toujours. « Pause » rend la main au propriétaire.
- Ajouté : **bandeau des messages importants** en haut de l'épisode. Rouge « Action requise » quand le studio attend le propriétaire (avec la raison) ; orange « Décidé automatiquement — à vérifier avant de publier » pour les scènes acceptées par la boucle complète.

## 0.1.79 — 04/11/2026
Fin de la liste tirée de l'étude de l'Atelier Gourmand.
- Ajouté : **« La planche a changé après le clip »**. Chaque clip retient la planche dont il est parti (`clip_from`). Si la planche change ensuite, un bandeau liste les scènes concernées. « Refaire ces clips… » les refait d'un coup, coût affiché, anciens clips gardés (`redo_clips`).
- Ajouté : **fenêtre de la scène plus complète** : raison du défaut (contrôle technique et regard sur le clip), « Entendu : « … » » avec la part du texte retrouvée, « Copier le prompt du clip » et « Copier le prompt de la planche », « Modifier le texte » (limite de mots du clip respectée ; si le clip existe déjà, il garde l'ancien texte jusqu'à ce qu'il soit refait) (`edit_scene`).
- Ajouté (demande du propriétaire) : **grand bandeau rouge de limite**, comme celui de l'Atelier, avec « Que faire ? » (attendre et heure de reprise, changer ou ajouter un compte, formule payante). S'il reste un compte avec des crédits, le studio passe dessus tout seul. S'il n'en reste aucun :
  - pour Flow, « Ajouter un compte Google » ouvre la page d'ajout de compte de Google dans la fenêtre FruchtDrama ; une fois connecté, le studio détecte le compte et reprend ;
  - pour ChatGPT ou Claude, « Changer de compte » ;
  - pour Grok ou Arena, « Ajouter un compte ».
- Ajouté : **feu de quota** sur les boutons « Dessiner » / « Tourner » des cartes Studio (vert, orange ou rouge, avec une infobulle « N possible(s) maintenant »). Bouton désactivé si rien n'est possible.
- Tests : `test_scene_tools.py` (+4), `test_login_watch.cjs` (ajout d'un compte Google), `test_ui_browser.py`.

## 0.1.78 — 04/11/2026
Suite de l'étude de l'Atelier Gourmand.
- Ajouté : **coût affiché avant toute action payante**. « Boucle complète », « Générer », les boutons « Dessiner » et « Tourner » des cartes Studio (qui lançaient la fabrication sans rien demander) et « Refaire… » disent ce qui sera payé : images ChatGPT, clips et crédits Flow estimés, crédits disponibles. L'essai à blanc est signalé comme gratuit.
- Ajouté : **historique par scène, « Remettre »**. La fenêtre d'une scène liste les versions précédentes de la planche et du clip (date, raison). « Remettre » rend une version ; celle qu'elle remplace est gardée. Gratuit (`restore_version`).
- Ajouté : bandeau **« Un clip a changé depuis le montage »** avec « Remonter la vidéo » (gratuit).
- Tests : `test_restore_version.py` (+2).

## 0.1.77 — 04/11/2026
D'après l'étude de l'Atelier Gourmand 1.0.22 (parcours lu dans son code ; aucun code repris).
- Ajouté : **ce qui se passe maintenant**. La dernière ligne du journal s'affiche en direct dans la barre de fabrication de l'épisode, dans la pile « En cours » du menu et sur la carte Studio.
- Ajouté : pastille **« En cours »** sur la carte Studio d'une histoire en fabrication. Un clic ouvre directement la partie en cours et sa progression, au lieu de la liste des parties.
- Corrigé : la pile « En cours » montre aussi le montage et l'analyse de la vidéo d'origine, qui n'ont pas de tâche navigateur.

## 0.1.76 — 04/11/2026
- Corrigé (retour du propriétaire) : **impossible de rouvrir une vidéo en cours depuis Studio**. Dans la page d'une histoire, la carte d'une partie n'était pas un bouton : le clic ne faisait rien. Elle ouvre maintenant l'épisode et sa progression ; elle répond aussi au clavier (Entrée, Espace).
- Corrigé : pendant une fabrication, la page se redessine toutes les 4 s. Un redessin entre l'appui et le relâchement de la souris faisait perdre le clic ; il attend maintenant la fin du clic. Test : `test_ui_interactions.cjs` (carte de partie ouverte au clic).

## 0.1.75 — 04/11/2026
- Corrigé (retour du propriétaire après la 0.1.74) : **plusieurs fenêtres s'ouvraient encore sur « Revérifier »**. Plusieurs vérifications lancées en même temps, sans fenêtre FruchtDrama ouverte, en créaient chacune une. La création de la fenêtre se fait maintenant une seule fois : les autres vérifications attendent la même fenêtre. Le studio est aussi retrouvé sur `localhost` et sans motif d'adresse avec port. Test : `test_workspace.cjs` (5 vérifications simultanées, 1 fenêtre ; l'ancien code en ouvrait 5).

## 0.1.74 — 04/11/2026
Retour du propriétaire : trop de fenêtres et d'onglets, la vue saute vers ChatGPT ou Flow, « Se connecter » sans effet, page Mes comptes trop touffue. Modèle : l'Atelier Gourmand.
- Corrigé : **une seule fenêtre**. Un studio déjà ouvert dans une fenêtre devient la fenêtre FruchtDrama ; une tâche n'en ouvre plus une seconde.
- Corrigé : **la vue reste sur le studio**. ChatGPT, Claude, Flow, Grok et Arena travaillent dans des onglets en arrière-plan de la fenêtre : plus d'onglet activé ni de fenêtre mise au premier plan par une tâche. Ces onglets sont protégés de l'économiseur de mémoire de Chrome (`autoDiscardable:false`).
- Corrigé : **un onglet terminé se ferme sans changer la vue**. S'il était à l'écran, le studio revient d'abord (`FruchtWorkspace.close`).
- Corrigé : **« Se connecter » suit la connexion**. Le site s'ouvre dans un onglet de la fenêtre (un onglet déjà ouvert est réutilisé). Dès que tu es connecté, la carte passe au vert, l'onglet ouvert par le studio se referme et le studio revient. La vérification relit aussi une page encore en chargement au lieu de la déclarer déconnectée.
- Amélioré : **Mes comptes à la façon de l'Atelier**. D'abord les cartes des sites, puis les comptes Google Flow en version compacte (total des crédits, aide pliée). Ensuite les réglages pliés, chacun avec son résumé d'une ligne : langue, montage, contrôles, sauvegardes, thème, et « Avancé » pour les navigateurs, la clé, les adresses, Grok et Arena, les limites et l'assistance. Un réglage ouvert le reste au rafraîchissement.
- Corrigé : **un compte Google retiré de Chrome gardait son numéro** (`/u/0`), qui ouvrait désormais un autre compte. Sa lecture de solde échouait toutes les 15 min, ce qui contribuait à rouvrir la fenêtre. « Détecter mes comptes » le met maintenant hors rotation (rien n'est supprimé).
- Tests : `test_flow_scan.py` (+1), `test_login_watch.cjs` (nouveau), `test_workspace.cjs` (fenêtre du studio adoptée, fermeture sans saut de vue), `test_chat_session.cjs`, `test_sites.cjs`.

## 0.1.73 — 04/11/2026
- Ajouté : **vidéo à publier toujours en 1080p**, règle du propriétaire. Les clips peuvent être plus petits (Flow 720p, Grok 480p) ; au montage, ils sont agrandis en 1080 × 1920 (ou 1920 × 1080). Un contrôle refuse désormais tout export d'une autre taille (`check_publish_size`). Test : `test_publish_size.py`.

## 0.1.72 — 04/11/2026
D'après le live du créateur de l'Atelier Gourmand (`docs/sudf/LIVE-ATELIER-2026-11-03.md`).
- Ajouté : **durée garantie**. Le nombre de plans couvre la durée choisie, fondus compris (plus de 60 s pour « 1 min », seuil de monétisation TikTok). Au montage, le silence coupé est rendu, à parts égales et sans jamais couper une réplique, jusqu'à atteindre la durée visée. L'essai réel réglé sur 30 s faisait 21,6 s. S'il manque des plans, le journal le dit (`montage.target`, `scenes_for`, `fit`).
- Ajouté : **trois appels de fin** dans la fiche de décision (faire choisir en commentaire, partie 2, question ouverte), au choix et modifiables. Les anciennes fiches à appel unique restent acceptées.
- Ajouté : **Refaire une virale voit la vidéo**. Le studio récupère la vidéo TikTok publique une fois (bibliothèque standard, cookies de la page), en tire une planche de 8 moments clés et la transcription locale, puis les joint à l'écriture (`source_video.py`). Avant, l'IA ne recevait que le lien. Si la vidéo ne peut pas être récupérée, l'écriture continue avec le lien et le journal le dit.
- Ajouté : case **Recréer à l'identique** (mêmes scènes dans le même ordre, répliques reformulées, autres prénoms), **Captures en plus** (4 images au plus, 8 Mo, PNG/JPEG/WebP, vérifiées avant la création ; aussi jointes au dessin des personnages, par exemple pour une photo du propriétaire) et **Instructions en plus**. Un avertissement rappelle le risque de « contenu non original » sur TikTok.
- Tests : `test_source_video.py` (+4), `test_link_creation.py` (+3), `test_ideas.py` (+1), `test_lots_atelier.py` (+1). Essai réel : vidéo TikTok de 80 s récupérée, planche et transcription en 14 s.

## 0.1.71 — 04/11/2026
- Corrigé : **fermer la fenêtre FruchtDrama la rouvrait** toute seule. Les relectures de solde Flow faites en arrière-plan (vérification et recharge quotidienne) attendent maintenant sa réouverture. Une recharge illisible est redemandée toutes les heures au lieu de toutes les 10 min. Une vraie production ouvre toujours la fenêtre.

## 0.1.70 — 03/11/2026
- Ajouté (préparé, **désactivé** dans cette édition) : **clés d'accès** pour la formation payante (`licence.py`, `docs/sudf/LICENCES.md`). 3 mois à partir de la 1ʳᵉ activation, 2 ordinateurs par clé, vérification une fois par jour, 3 jours sans internet, puis **consultation seule** (vidéos visibles et téléchargeables, rien de nouveau, rien supprimé). Le verdict du service des clés est signé (RSA) et vérifié sans dépendance ; le blocage est fait par le studio (création, file de tâches, montage), pas seulement par l'écran. Écran « Entre ta clé », bandeau 7 jours avant la fin, bouton « Vérifier maintenant ».
- Corrigé (essai réel) : après une réinstallation de l'extension (nouvel appairage), les **comptes Flow restaient liés à l'ancien navigateur** et l'épisode s'arrêtait sur « Solde insuffisant » malgré les crédits. Ils suivent maintenant le seul navigateur actif (jamais deviné s'il y en a plusieurs).
- Service des clés : projet séparé `fruchtdrama-licences` (page d'administration du formateur : créer, prolonger, annuler, libérer un ordinateur).
- Tests : `test_licence.py` (+10, jetons signés par openssl), `test_licence_gate.py` (+2), essai réel serveur Next.js ↔ studio.

## 0.1.69 — 03/11/2026
- Ajouté : **l'extension démarre le studio** (comme l'Atelier, qui vit entièrement dans Chrome). Le studio reste un programme local (montage ffmpeg, transcription), lancé par un hôte natif Chrome `com.fruchtdrama.studio` (`native_host.py`, `native-host.cmd`/`.sh`) qu'Installer.cmd enregistre pour l'utilisateur courant (registre HKCU sous Windows, `NativeMessagingHosts` sous Linux/macOS, aucun droit administrateur). Chrome démarré, icône cliquée ou boucle de 30 s : si le studio ne répond pas, l'extension le démarre ; sinon une page claire dit quoi faire. Le serveur survit à la fermeture de Chrome.
- Corrigé (essai réel) : une extension qui s'appaire (nouvelle copie, extension rechargée ou réinstallée) **prend la main** ; l'ancien navigateur est désactivé, sauf s'il exécute une tâche. Avant, elle restait « désactivée » derrière son propre ancien client et ne recevait aucune tâche. Toujours un seul navigateur au travail.
- Portable : chemins écrits à l'installation et réécrits à chaque lancement (dossier déplacé = réparé). L'extension a une **clé fixe** : même identifiant sur tous les ordinateurs, donc l'hôte natif l'autorise partout. Le studio accepte cette extension officielle à la place d'une ancienne copie déjà appairée.
- `installer.py` fonctionne aussi sous Linux (`.venv/bin`).
- Tests : `test_native_host.py` (+8), `test_studio_start.cjs` (nouveau), `test_unified_accounts.py` (+1 cas).

## 0.1.68 — 03/11/2026
- Corrigé (essai réel) : avec **Refaire tout seul**, quand la revue signalait plusieurs clips, le 2ᵉ « refaire » voyait la tâche du 1ᵉʳ et échouait (« Une tâche est en cours sur cette production ») : épisode « À vérifier » à moitié relancé, clip marqué refait sans l'être. Les clips sont maintenant détachés ensemble puis la file relancée une seule fois.
- Changé (décision du propriétaire) : seuls les clips en **défaut** (paroles sous 85 %, revue visuelle `issue`) sont refaits automatiquement. Un clip **incertain** n'est plus repayé : l'épisode passe « À vérifier ».
- Tests : `test_p2_quality.py` (+2, vérifiés par mutation).

## 0.1.67 — 03/11/2026
- Corrigé (essai réel) : un compte Google **sans accès à Flow** (page « Il semble que vous n'avez pas accès à Flow », adresse …/unavailable) bloquait l'épisode 90 s puis le mettait « À vérifier ». L'extension reconnaît maintenant cette page tout de suite ; le studio écarte ce compte (comme un compte sans crédits), rembourse la réservation et passe au compte suivant. Aucun crédit dépensé. Recharger l'extension.
- Tests : `test_flow_accounts.py` (+1), `test_p2_errors.py` (+1), `test_flow_session.cjs` (+1 cas).

## 0.1.66 — 03/11/2026
- Corrigé (essai réel) : l'extension ne reconnaissait pas la réponse de ChatGPT au **contrôle des planches** ; l'épisode passait en « À vérifier ». Elle lit maintenant ce verdict (une ligne par planche, lié à la tâche) et le récupère aussi après un rechargement. Recharger l'extension.
- Tests : `tests/test_response.cjs` (+4 contrôles).

## 0.1.65 — 03/11/2026
Lot 5 du parcours Atelier (dernier lot).
- Le Filon : puces de **niches** et **Mes niches** (Fruits, Animaux, Chats, Bébés, Gourmandises, Cartoon, Survie, Créatures, Avatar humain, ou ta propre niche ; huit au plus). Chaque niche a sa propre recherche TikTok ; Actualiser relève la niche choisie ; les vidéos sont rangées par niche.
- Le Filon : « Prochaine actualisation vers 15:40 » quand l'actualisation toutes les 2 h est active ; barre **Les mots-dièse qui portent** (pondérés par les vues, un clic filtre les vidéos).
- Studio : compteurs toujours visibles « images / clips / vidéos en 6 h ».
- Barre latérale : **EN COURS** empile toutes les productions en cours (quatre au plus), celle qui travaille d'abord.
- Tests : `tests/test_lot5_filon.py` (4), étape 11 bis de `tests/test_ui_interactions.cjs`.

## 0.1.64 — 03/11/2026
Lot 4 du parcours Atelier.
- Mes comptes : chaque carte connectée a **Changer de compte**, avec l'aide en 3 étapes (se déconnecter dans l'onglet, connecter l'autre compte soi-même, « C'est fait » revérifie). Nouvelle carte **Accès à tes fichiers** (montage sur cet ordinateur, ffmpeg).
- Mes comptes › **Contrôles et essai à blanc**, trois réglages :
  - **Planches** (nouveau) : avant les clips, ChatGPT compare les planches à la feuille des personnages (une pièce jointe pour cinq planches). Refaire toutes seules (une fois, quatre au plus, avec la raison en correction), Signaler seulement (noté, la production continue) ou Pas de contrôle (par défaut, aucune image ChatGPT en plus).
  - **Clips** : inchangé (Refaire tout seul, Signaler seulement, Pas de contrôle).
  - **Regard sur les clips** (nouveau) : Les regarder aussi, ou À l'oreille seulement (aucune revue visuelle ChatGPT ; le rapport l'écrit).
- Qualité Économie : planches et clips signalés seulement, clips contrôlés à l'oreille.
- Tests : `tests/test_lot4_controls.py` (7), étape 12 a bis de `tests/test_ui_interactions.cjs`.

## 0.1.63 — 03/11/2026
Lots 1 à 3 du parcours Atelier observé (`docs/sudf/PARCOURS-ATELIER.md`).
- Créer : **Qualité** Normale (clips signalés refaits, 3 au plus) ou Économie (signalés seulement) ; **Format** Vertical, Horizontal ou **Les deux** (la version 16:9 démarre seule quand la 9:16 est montée) ; **Personnages** Simple ou Détaillé (feuille avec trois quarts, gros plan et détails) ; **Sous-titres** Sans (seul le hook reste écrit) ou Avec.
- Production automatique : fenêtre « On y va ? » avec le coût annoncé (images ChatGPT, clips, crédits Flow, clips refaits) avant toute dépense.
- Page épisode : chrono « 4 min 12 · en général 8 à 16 min » à côté de Pause.
- Mes comptes › **Montage de mes vidéos** : coupe franche, fondu léger ou fondu long (image et son), coupes rapides (deux ou trois cadrages dans un plan), couper les silences (avant la première et après la dernière réplique, d'après les mots reconnus ; rien n'est coupé sans transcription fiable), karaoké. Réglé une fois, copié dans chaque nouvel épisode ; un épisode déjà monté garde les siens.
- Mes comptes › **Mes sauvegardes** : chaque histoire est sauvegardée après sa fabrication (texte, personnages, planches, miniature) dans Téléchargements › FruchtDrama › sauvegardes ; « Sauvegarder maintenant » ; « Remettre des histoires » les fait revenir en pause.
- Tests : `tests/test_lots_atelier.py` (11, dont 3 montages ffmpeg réels), étape 10 ter de `tests/test_ui_interactions.cjs` (Chrome réel).

## 0.1.62 — 03/11/2026
- Mes comptes › Autres réglages › Adresses : bouton « Retirer tous les comptes (N) ». Double confirmation (fenêtre puis taper RETIRER). L'état est sauvegardé avant dans data/sauvegardes ; les comptes qui génèrent un clip à ce moment sont gardés. Les vidéos ne sont jamais touchées.

## 0.1.61 — 03/11/2026
- Recharge quotidienne des crédits Flow : à la première dépense d'un compte, le studio note l'heure de retour des crédits (24 h plus tard). Mes comptes affiche « Crédits de retour dans 3 h 12 ». À l'heure dite, la fenêtre FruchtDrama relit seule tous les soldes ; si les crédits ne sont pas revenus, nouvel essai toutes les heures.
- Rotation : les comptes dont le minuteur tourne déjà sont utilisés en premier ; les comptes pleins sont gardés pour la suite.
- 23 adresses Google ajoutées (sans mot de passe) ; liste dans Documentation/MES-COMPTES.md.

## Non publié (branche `sudf`)

Prochain : P3 (séries, idées, kit de publication, veille, 16:9) et P4 (montage avancé, sous-titres karaoké, rapport de panne). Voir `docs/sudf/REPRISE.md`.

## 0.1.60 — Studio identique à l'Atelier, comptes Google détectés, montage dynamique (03/11/2026)

### Changé
- **Studio par histoires** (comme l'Atelier) : « Tes histoires et leurs parties », File de nuit, + Nouvelle histoire, compteurs à dessiner / à tourner / prêtes / à écrire, quotas (« N en 6 h », « au mur, reprise HH:MM », crédits Flow) ; grandes cartes avec badge, barre 5 segments, prochaine action et bouton direct (Tourner, Dessiner, Monter, Valider…).
- **Page d'histoire** : les parties (et versions 16:9 / langues), « Créer la partie N », personnages, Supprimer l'histoire.
- **Page de partie** : ← histoire, titre en majuscules ✎ (renommer), durée et scènes, Version horizontale / Langues, Télécharger les images, File de nuit, Le texte, ▶ Boucle complète ; cases Fiche / Personnages / Planches / Clips (« N à revoir ») / Montage (Monter… / Remonter…) ; Vidéo finale ; Miniature (Télécharger, **Contrôler** = originalité, Refaire) ; Publication (Tout copier, réécrire) ; Personnages (Tout refaire) ; Scènes ; journal replié.
- **Mes comptes** : « Comptes Google Flow » avec **Détecter mes comptes** (parcourt /u/0, /u/1… de la fenêtre, lit adresse, crédits réels et projet de chaque compte, active la rotation) ; le reste (clé, adresses, Grok / Arena) replié.
- **Ouverture de la fenêtre** : ChatGPT, Grok et Flow ouverts en onglets, sites revérifiés et crédits de tous les comptes relus.

### Amélioré
- **Montage dynamique** : zoom lent alterné (avant / arrière) sur chaque clip, en plus des coupes.

### Ajouté
- Remontage (« Remonter… ») avec les clips existants ; renommer un épisode.

### Tests
- `tests/test_flow_scan.py` (2), tests d'interface adaptés (navigation Studio › histoire › partie).

## 0.1.59 — résolution, hook, personnages en mouvement, réécriture anti-plagiat (03/11/2026)

Priorités du propriétaire pour monétiser TikTok : 1. la résolution, 2. le hook.

### Amélioré
- **Résolution** : vidéo finale en **1080 × 1920** (1920 × 1080 en horizontal) au lieu de 720 × 1280 ; agrandissement Lanczos + netteté légère ; encodage haute qualité (x264 slow, CRF 17, profil high, AAC 192 kb/s) ; sous-titres, marges et miniature mis à l'échelle. Option **clips Flow en 1080p** (Réglages Flow de Créer ; vérifiée dans Flow, sinon aucun envoi). Planches : « plus haute résolution disponible, ultra net ».
- **Hook** : accroche **écrite à l'écran** pendant les 3 premières secondes (gros texte en haut, dernier mot en jaune, fondu) ; champ `hook_text` demandé à l'IA ; consigne « HOOK OBLIGATOIRE » : instant le plus fort en scène 1, phrase choc de moins de 10 mots dans les 2 premières secondes, question résolue à la fin.
- **Personnages et mouvement** : 2 à 5 personnages (au moins 3 quand l'histoire le permet) ; cadrage différent par scène, caméra en mouvement, personnages qui agissent, arrière-plan vivant, au moins deux lieux ; même consigne dans les prompts de clips.

### Ajouté
- **Réécrire pour s'éloigner** (originalité) : sur la fiche (renvoyée avec les conseils et l'origine à éviter) et après le montage (nouveaux titre, couverture, accroche et description, kit de publication refait, score recalculé).

### Corrigé
- Flow : l'avertissement réel « Avertissement de crédits insuffisants » est reconnu ; la tâche s'arrête en « crédits » (passage au compte suivant) au lieu d'un « envoi bloqué » incompréhensible.
- Les boutons Navigateur du studio (mémoriser le compte Flow, ranger, récupérer) ne se bloquent plus eux-mêmes (« Attendez la fin de la tâche en cours »).
- Mes comptes : statuts fidèles (solde bas, compte réellement ouvert).
- Message clair quand un compte Flow a été mémorisé par un navigateur hors ligne.

## 0.1.58 — versions horizontale 16:9 et autres langues (03/11/2026)

### Ajouté
- **+ Version horizontale 16:9** (page épisode, comme l'Atelier) : nouvel épisode lié, même histoire et mêmes personnages (feuille copiée), planches redessinées en paysage, clips 16:9, sous-titres et montage 1280 × 720, miniature horizontale. Les prompts passent automatiquement de 9:16 à 16:9 ; Flow : réglage 16:9 choisi et vérifié avant envoi (`aspect`), sinon aucun envoi.
- **Langues** : version dans une autre langue, mêmes planches et mêmes images de personnages, répliques adaptées (pas de mot à mot), titre, couverture et description traduits, voix et clips refaits ; relecture possible si l'option est cochée.
- Les versions s'affichent sous le titre de l'épisode d'origine, avec leur état.

### Changé
- Contrôle qualité et import des clips vérifient l'orientation attendue (verticale ou horizontale).
- Mes comptes : statuts fidèles. Flow « solde bas » (orange) quand le solde ne paie pas un clip, « épuisé » à 0 ; ChatGPT, Claude, Grok, Arena : « Connecté » (vert) seulement pour l’adresse ouverte dans la fenêtre, « Enregistré · autre compte ouvert » sinon, « Pas connecté » (rouge) si le site est déconnecté.

### Tests
- `tests/test_variants.py` (3), `test_flow_models.cjs` (16:9 choisi, vérifié, refusé si absent).

## 0.1.57 — bandeau de limite, « En cours », contrôles et thèmes (03/11/2026)

### Ajouté
- **Bandeau de limite sur toutes les pages** (comme l'Atelier) : « Limite ChatGPT images / Grok vidéos… atteinte : ça revient vers HH:MM (estimation). Rien n'est perdu. » avec **Ouvrir** le site et **J'ai changé de compte**.
- **« En cours »** en bas du menu : la production en train d'être faite, sa prochaine action et sa progression ; un clic l'ouvre.
- **Contrôles des clips** (Mes comptes) : **Refaire tout seul** (un clip signalé par les paroles ou la revue visuelle est refait une fois, puis le propriétaire décide), **Signaler seulement** (défaut), **Pas de contrôle**. S'applique aux nouveaux épisodes.
- **Thèmes** : Clair (défaut), Sombre, Ardoise, Cinéma, Lagon, Papier ; gardés sur l'ordinateur.

### Tests
- `test_p2_quality.py` (+2 : sans contrôle, refait une fois puis arrêt), `test_ui_browser.py` (bandeau de limite).

## 0.1.56 — Filon détaillé, originalité avant publication, page épisode complétée (03/11/2026)

### Ajouté
- **Contrôle d'originalité** (`originality.py`) : TikTok ne publie pas sa méthode ; ses règles excluent les contenus copiés, repris avec de légères modifications ou faits des vidéos d'autres comptes, exigent l'étiquette IA, et la rémunération demande plus d'une minute. Le studio estime le risque : empreinte des images (dHash) comparée à la vidéo d'origine et à toutes les vidéos relevées, reprise de mots (titre, description, répliques), recréation d'une virale, répétition de nos propres épisodes, durée, mention IA. Score en %, verdict (publier / corriger / déconseillé), facteurs détaillés et changements conseillés. Calculé seul après le montage, bouton **Recalculer**. **Avant tout paiement**, la fiche d'une recréation signale les mots communs avec la vidéo d'origine.
- **Le Filon détaillé comme l'Atelier** : chiffres réels lus sur la page publique de chaque vidéo (vues — et non plus les likes —, vues/h, croissance entre deux relevés, engagement, durée, ancienneté, langue, compte, abonnés, avatar) ; onglets **Viral / Toutes les vidéos / Comptes** (abonnés, vidéos relevées, vues médianes, meilleure, virales, Suivre) ; filtres 24 h / 3 jours / 7 jours / Tout, durée (dont « 1 à 3 min, monétisables »), tri (plus vues, plus rapides, croissance, engagement), comptes non suivis, recherche ; badges Viral, Recréée, durée ; **Voir ma recréation**.
- Vidéos du Filon **lancées seules dès qu'elles sont visibles** (10 à la fois), la miniature haute qualité (720 px) reste dessous si TikTok refuse la lecture.
- Page épisode : **Télécharger les images** (zip), **Le texte**, **Boucle complète**, liens **Refaire… / Générer** dans les cases d'étapes, **Miniature** : choix de la scène de base puis Faire / Refaire la miniature.

### Tests
- `tests/test_originality.py` (4), `tests/test_thumbs.py` (3 : fiche, historique, croissance, sans réseau), `test_ui_interactions.cjs` (lecture automatique, chiffres).

## 0.1.55 — interface façon Atelier : dix histoires, fiche de décision, pages refaites (03/11/2026)

### Ajouté
- **Dix histoires** (option « Pas d'idée ») : titre, pitch, pourquoi ça accroche, inspirés des titres du Filon ; un clic = la demande ; « Dix autres ». Module `ideas.py`, étape `ideas`.
- **Fiche de décision** avant tout paiement (étape `sheet`) : l'histoire en une phrase, moteur, obstacle, twist, image d'ouverture, question du spectateur, 3 titres, 3 premières répliques, appel de fin, casting ; modifiable ; **Valider et écrire l'épisode** ou **Revoir avec mes remarques**. En production automatique : premier titre, première réplique, premier appel (comme l'Atelier). La fiche validée devient la consigne du scénario (première réplique imposée).
- **Page Créer en pleine page** (plus de petite fenêtre) : qui écrit, quatre options (Pas d'idée, J'ai une idée, Refaire une virale, Décide tout à ma place), niche, **durées fixes 30 s / 1 min / 2 min / 3 min** (1 min = minimum de monétisation TikTok ; nombre de plans et coût Flow estimé affichés), moteur, langue, format, fabrication automatique ou validée.
- **Miniatures du Filon chargées tout de suite** : couverture lue sur la page publique de la vidéo TikTok, réduite et gardée en local (`thumbs.py`, `GET /api/thumb`), préchargée après chaque relevé ; grille plus dense (moins de défilement) ; titres qui ne sont qu'un compteur remplacés par le compte.
- **Logo** FruchtDrama (page, onglet, icônes de l'extension).

### Changé
- Le Filon ouvre l'application ; menu à quatre entrées avec sous-titres vivants (vidéos relevées, à écrire / à dessiner / à tourner) ; la Bibliothèque devient le filtre « Prêtes » du Studio.
- **Studio** : grandes cartes illustrées (badge Prête / À finir, barre en 5 segments, prochaine action), compteurs, filtres.
- **Page épisode** : cinq grandes cases d'étapes, barre de progression en %, personnages, mur de scènes (une vignette par scène, titre court) ; un clic ouvre la **planche et le clip côte à côte** avec les répliques et les boutons Remplacer / Refaire ; réglages et journal repliés.
- **Mes comptes** : plus de formulaires en double ni de synthèse redondante ; un seul tableau d'adresses, puis trois onglets (Navigateur, Crédits et limites, Assistance).
- Scénario : titre court par scène demandé à l'IA. Nombre de scènes accepté de 3 à 30.

### Tests
- `tests/test_ideas.py` (6), `tests/test_thumbs.py` (2, sans réseau), `test_ui_browser.py` et `test_ui_interactions.cjs` réécrits pour les nouvelles pages.

## 0.1.54 — tout dans la page du studio, plus d'onglet Passerelle (03/11/2026)

Comme l'Atelier : l'extension n'a plus de page à elle ; tout se règle dans le studio.

### Changé
- La fenêtre FruchtDrama s'ouvre sur le studio seul. L'ancien onglet Passerelle épinglé est fermé au clic suivant ; il reste accessible en secours par « Options » de l'extension.
- Mes comptes › **Navigateur** : **Oublier** un navigateur hors ligne ; état de l’extension, **Mémoriser le compte Flow ouvert**, **Ranger les onglets**, **Récupérer une réponse** ; le résultat de l'extension s'affiche dans la page (`bridge_notice`).

### Ajouté
- Script de contenu `studio-bridge.js` (page du studio uniquement) : signale la présence de l'extension et la réveille aussitôt après chaque action (plus d'attente de 30 s).
- `POST /api/sites` accepte `register_flow`, `tidy`, `recover` ; `POST /api/bridge/notice` (extension authentifiée).

### Tests
- `test_workspace.cjs` (studio seul, ancien onglet fermé), `test_workspace_chrome.cjs` (Chromium réel), `test_unified_accounts.py` (actions transmises une seule fois, retour affiché), étape 12 ter de `test_ui_interactions.cjs`.

## 0.1.53 — comptes par adresse et clé cachée (03/11/2026)

Sur le modèle de l'Atelier Gourmand : une adresse s'ajoute une seule fois, la clé ne se recopie jamais.

### Ajouté
- **Mes comptes › Mes comptes** : une ligne par adresse e-mail, une colonne par service (ChatGPT, Claude, Google Flow, Grok, Arena). Formulaire unique : adresse, nom affiché, services cochés, crédits Flow facultatifs. Le studio crée lui-même le profil Flow et les comptes de rotation Grok / Arena. Ajouter ou retirer un service directement dans la ligne ; « Retirer » supprime l'adresse et tout ce qui y est rattaché (refusé pendant un clip en cours). Module `identities.py`, route `POST /api/account`.
- **Clé du studio cachée** : au premier clic sur l'icône, l'extension s'appaire seule (`POST /api/bridge/auto-pair`, réservé à une origine `chrome-extension://`), garde la clé et ne la montre plus. Rôle complet, tâches autorisées. La première extension liée est mémorisée ; une autre (réinstallation) demande « Autoriser une nouvelle extension » (`POST /api/key/reset`). Un deuxième navigateur appairé alors qu'un autre est en ligne démarre désactivé.

### Amélioré
- Les anciens profils Flow et comptes Grok / Arena sont regroupés automatiquement par adresse (soldes additionnés).
- Code d'appairage manuel replié dans « Appairage manuel (secours) ».
- `public_state` ne publie ni la clé ni l'origine de l'extension (`key_saved` seulement).

### Tests
- `tests/test_unified_accounts.py` (7 : ajout multi-services sans doublon, regroupement des anciens comptes, limites, suppression refusée pendant un clip, API, appairage automatique unique et origine mémorisée, second navigateur désactivé), `tests/test_auto_pair.cjs`, étape 12 bis de `tests/test_ui_interactions.cjs` (Chrome réel).

## Branche `sudf-ui` — test réel de bout en bout (02/11/2026)

Parcours réel dans le Chrome dédié : fenêtre unique, appairage, compte Flow rattaché (solde réel lu : 50 crédits), création d'après un lien TikTok, histoire validée, feuille de personnages, 4 images de scènes, projet Flow créé, **essai à blanc du clip réussi** (rien facturé).

### Corrigé
- Plusieurs passerelles en ligne se partageaient les tâches (une passerelle sans fenêtre provoquait « No current window ») : bouton **Désactiver / Réactiver** par passerelle (Mes comptes, onglet Passerelle) ; une passerelle désactivée ne reçoit plus aucune tâche.
- « Mémoriser le compte Flow » reconnaît les adresses de projet sans `/u/N/`.
- Vignettes des productions : couverture, sinon première scène, sinon feuille de personnages.
- Le badge « connecteur(s) en ligne » ignore les passerelles désactivées.

## Branche `sudf-ui` — finition professionnelle et comptes façon Atelier (02/11/2026)

### Ajouté
- **Mes comptes** refait comme l'Atelier : synthèse (crédits Flow, comptes Grok/Arena disponibles, passerelles en ligne), un tableau par plateforme (compte, crédits, état, actions : Vérifier, Réglages, Retirer, Oublier la limite), un **formulaire unique « Ajouter un compte »** pour Flow, Grok et Arena, limites ChatGPT/Claude, passerelle et code d'appairage.
- État « Solde bas » quand un compte Flow ne peut plus payer un clip.

### Amélioré
- **Aucune icône emoji** : un seul jeu d'icônes au trait (SVG, géométrie Lucide, licence ISC) pour la navigation, les boutons, les statistiques et les vignettes ; logo typographique « FruchtDrama ».
- Durée de scène affichée selon le moteur (6 s Grok, 8 s Flow) au lieu de 8 s fixes.
- Documentation : « Connexions » devient « Mes comptes ».

### Tests
- `test_ui_interactions.cjs` : ajout d'un compte Flow par le formulaire unique, tableaux par plateforme, aucune icône emoji sur les 5 pages, icônes de navigation SVG.

## Branche `sudf-ui` — interface façon Atelier (02/11/2026)

### Ajouté
- Navigation d'action avec sous-titres : **Le Filon** (vidéos virales relevées), **Créer une vidéo** (d'un lien ou d'une idée), **Studio**, **Mes comptes**, Bibliothèque, Mode d'emploi.
- **Le Filon** : toutes les vidéos TikTok relevées par les recherches, meilleur signal d'abord, bouton « Créer d'après cette vidéo ».
- **Créer d'après un lien TikTok** : la recherche est sautée, l'histoire originale s'inspire de la vidéo fournie (paramètres de suivi retirés, autres sites refusés).
- **Thème sombre** par défaut (bouton ◐ pour le thème clair, mémorisé).

### Amélioré
- Police agrandie sur toute la plateforme ; images des scènes, clips et couverture affichés en grand, agrandissement plein écran au clic ; barre latérale élargie.

### Tests
- `tests/test_link_creation.py` ; `tests/test_ui_interactions.cjs` étendu (thème, Filon, création pré-remplie, tailles de police et d'images, agrandissement).

## Branche `sudf-ui` — correctifs du test réel (02/11/2026)

Test réel automatisé sur ce PC : serveur réel, Chromium avec l'extension, vrais sites (sans compte). Détail et liste de contrôle : `docs/ESSAI-REEL.md`.

### Corrigé
- ChatGPT/Claude déconnectés gardent un éditeur (chat anonyme) : le connecteur refuse maintenant d'envoyer (« non connecté »).
- La page Cloudflare « Just a moment... » est reconnue comme vérification anti-robot.
- LMArena redirige vers arena.ai : autorisations et page vidéo (arena.ai/video) mises à jour (recharger l'extension).
- Message clair quand une page reste vide 90 s (connexion ou vérification à faire dans l'onglet).

### Tests
- `test_composer.cjs` et `test_engine_video.cjs` étendus avec les libellés réels observés.

## Branche `sudf-ui` (sur 0.1.52) — interface complète

### Amélioré
- Mode d'emploi intégré (page « Mode d'emploi ») : section « Nouveautés » avec toutes les fonctions (fenêtre unique, moteurs, changement de compte, limites et refus, file de nuit, corrections, séries, assistance) et la version.
- Formulaire de création : les champs propres à Flow (modèle, profil, coût) se masquent quand Grok ou Arena est choisi.
- Production Grok/Arena : badge du moteur, sélecteur de profil Flow masqué.
- Couleurs des nouveaux statuts (limite, file de nuit, changement de compte, relecture).

### Tests
- `tests/test_ui_interactions.cjs` étendu (Chrome réel : guide, formulaire par moteur, badge moteur).

## 0.1.52 — 2026-11-02 (branche `sudf`) — P3 lot 1 : séries et kit de publication

Détail : `docs/sudf/P3-croissance.md`.

### Ajouté
- **Écrire la suite (partie N+1)** sur un épisode terminé : mêmes personnages, scénario lancé directement, idée facultative.
- Les images de référence des personnages repris sont **réutilisées** : seuls les nouveaux personnages sont payés.
- **Kit de publication** à la fin du montage : titre, description, hashtags, premier commentaire, créneaux suggérés (bouton « Kit de publication ↓ »).

### Mode d'emploi
- Section 10 bis et ligne 0.1.52 de `docs/MODE-EMPLOI.md`.

### Tests
- `tests/test_p3_series.py` (unitaires + HTTP).

## 0.1.51 — 2026-11-02 (branche `sudf`) — P4 lots 1 et 2 : entretien et sous-titres karaoké

Détail : `docs/sudf/P4-montage-ux.md`.

### Ajouté
- **Supprimer une production** (bouton « Supprimer… ») : dossier déplacé dans `data/corbeille`, récupérable ; copie de l'état prise avant ; refusé pendant une tâche, un montage ou avec un clip Flow incertain.
- **Nettoyer l'historique** (Connexions → Assistance et entretien, et au démarrage) : anciennes tâches et journaux trop longs purgés, copie de sauvegarde gardée dans `data/sauvegardes`.
- **Rapport de panne copiable** sans jeton, code d'appairage ni adresse e-mail (`/api/report`).
- **Sous-titres karaoké** : chaque mot s'allume en jaune au moment où il est prononcé ; option cochée par défaut à la création.

### Corrigé
- L'alignement des sous-titres n'était plus calé pour des clips de plus de 8 s (Arena) : il suit maintenant la durée réelle du clip.
- Test navigateur : attente fixe remplacée par une attente conditionnelle (échec intermittent sous charge).

### Mode d'emploi
- Sections 8, 10, 11 et 12 de `docs/MODE-EMPLOI.md`.

### Tests
- `test_p4_maintenance.py`, `test_p4_karaoke.py` (montage ffmpeg réel avec karaoké).

## 0.1.50 — 2026-11-02 (branche `sudf`) — P2 lots 2 à 5 : automatisation sans surveillance

Détail : `docs/sudf/P2-automatisation.md` (P2-05 à P2-12).

### Ajouté
- **Reformulation anti-refus graduée** (`refusal.py`) : une image refusée par ChatGPT est redemandée au niveau 1 (vocabulaire adouci EN/DE/FR, cadre tout public, **même style visuel**), puis niveau 2 (âges neutres, « laisse de côté le détail refusé »). Ensuite, arrêt avec message clair. Niveau remis à zéro quand l'image arrive ou avec « Refaire ».
- **Limites apprises** de ChatGPT et Claude (`quotas.py`) : passages et murs sur 6 h glissantes, capacité estimée, reste, heure de reprise (délai annoncé par le fournisseur en priorité). Panneau « Limites apprises » dans Connexions avec « J'ai changé de compte : oublier la limite ».
- **Attente au lieu d'échec** : à la limite, statut « Limite atteinte, reprise automatique » ; aucun envoi tant que le service est au mur, même pour les autres productions ; reprise seule à l'heure prévue.
- **File de nuit** : liste ordonnée, une production à la fois, échecs réessayables relancés jusqu'à 3 fois (délai croissant), attente des limites et crédits, retrait avec raison quand un humain est nécessaire (connexion, anti-robot, clip Flow incertain, réserves qualité, relecture, pause). Interdite en essai à blanc. Survit au redémarrage.
- **Anti-veille Windows** (`power.py`) pendant la file de nuit, relâchée à l'arrêt.

### Amélioré
- Contrôle qualité : seuil de paroles porté à **85 %** (décision du propriétaire) ; décision automatique, raisons et seuils enregistrés dans le rapport (`auto`), avec la trace d'une validation par le propriétaire.

### Mode d'emploi
- Sections 9, 10, 11 bis (file de nuit) et 12 de `docs/MODE-EMPLOI.md`.

### Tests
- `test_p2_refusal.py`, `test_p2_quotas.py`, `test_p2_quality.py`, `test_p2_night.py` (unitaires + HTTP, vérifiés par mutation), `test_ui_interactions.cjs` étendu (Chrome réel : file de nuit).

## 0.1.49 — 2026-11-02 (branche `sudf`) — P5 lots 3 à 5 : Grok, Arena et changement de compte

Détail : `docs/sudf/P5-fenetre-moteurs.md` (P5-07 à P5-11).

### Ajouté
- **Connecteurs Grok Imagine et LMArena vidéo** (`extension/engine-video.js`), dans la fenêtre FruchtDrama : vérification de la connexion et du compte attendu, mode vidéo, image de départ, prompt, intention d'envoi puis envoi unique, détection de la nouvelle vidéo, téléchargement. Erreurs typées : connexion, mauvais compte, limite (avec délai annoncé), modération, délai dépassé. Aucun bouton d'achat n'est jamais cliqué. **Expérimental** : écrit sur fixtures, à vérifier en essai à blanc sur vos comptes.
- **Comptes Grok et Arena** dans Connexions (adresse seulement, jamais de mot de passe) (`engine_accounts.py`, route `/api/engine-account`).
- **Changement de compte guidé** : quand un compte atteint sa limite, il est marqué (heure de renouvellement lue ou 3 h par défaut), le compte suivant est proposé (statut « Changement de compte ») ; vous vous connectez vous-même dans l'onglet, puis « J'ai changé de compte » ; l'identité affichée est vérifiée avant tout envoi.
- **Attente automatique** : si tous les comptes sont à leur limite, statut « Limite atteinte, reprise automatique » et reprise seule à l'heure de renouvellement. Bouton « Oublier la limite » par compte.
- Essai à blanc pour Grok et Arena (aucun compte requis).

### Modifié
- Grok et Arena sont sélectionnables à la création (marqués expérimental). Nouvelles autorisations d'hôtes : grok.com, lmarena.ai (recharger l'extension).

### Mode d'emploi
- Sections 7, 8, 9 et 12 de `docs/MODE-EMPLOI.md`.

### Tests
- `tests/test_engine_video.cjs` (connecteurs sur fixtures DOM, vérifiés par mutation), `tests/test_p5_accounts.py` (unitaires + HTTP), `tests/test_ui_interactions.cjs` étendu (Chrome réel : changement de compte guidé, ajout d'un compte Grok).

## 0.1.48 — 2026-11-02 (branche `sudf`) — P5 lot 2 : moteur vidéo par production

Détail : `docs/sudf/P5-fenetre-moteurs.md` (P5-06).

### Ajouté
- Choix du **moteur vidéo** à la création : Google Flow (8 s), Grok Imagine (6 s), LMArena vidéo (4 à 10 s) (`engines.py`). Grok et Arena sont affichés « bientôt » et refusés par le serveur tant que leur connecteur n'est pas livré.
- Nouvelle tâche `engine_video` pour Grok/Arena : pas de réservation de crédits, jamais bloquée comme « envoi incertain » (aucun argent en jeu), essai à blanc pris en charge.

### Amélioré
- Le prompt de scénario, la limite de mots par scène (20 mots pour 8 s, 15 pour 6 s), la correction d'histoire et le contrôle de durée suivent le moteur choisi.
- Montage : chaque clip garde sa durée réelle (bornée par le moteur) au lieu d'être complété par une image figée jusqu'à 8 s ; les sous-titres se calent sur les durées réelles. Flow reste exactement 8 s.

### Mode d'emploi
- `docs/MODE-EMPLOI.md` : champ « Moteur vidéo » (section 8) et ligne 0.1.48 (section 12).

### Tests
- `tests/test_p5_engines.py` : unitaires, planification, routage, HTTP, contrôle de durée et **montage ffmpeg réel** de clips de 6 s (vérifié par mutation).

## 0.1.47 — 2026-11-02 (branche `sudf`) — P5 lot 1 : fenêtre unique

Détail : `docs/sudf/P5-fenetre-moteurs.md` (P5-01 à P5-05).

### Ajouté
- Un clic sur l'icône de l'extension ouvre la **fenêtre FruchtDrama** (onglet passerelle épinglé + studio) ou la ramène au premier plan. Tout s'y passe : studio, ChatGPT, Claude, TikTok, Flow et ouverture des comptes (`extension/workspace.js`).
- Les onglets de fournisseurs sont créés dans cette fenêtre ; un onglet déjà ouvert ailleurs (projet Flow mémorisé, recherche TikTok) y est déplacé avec sa session.
- Plusieurs comptes Google dans la même fenêtre (`/u/0/`, `/u/1/`…) : passage au compte suivant quand les crédits manquent, sans changer de fenêtre (INSTALLATION.md, étape 5).

### Amélioré
- Fenêtre fermée : recréée automatiquement à la tâche suivante ; identifiant oublié au redémarrage du navigateur.
- « Mémoriser le compte Flow » et « Récupérer la réponse » visent le dernier onglet consulté dans la fenêtre, et non plus l'onglet actif (qui est maintenant la passerelle).

### Modifié
- Le panneau popup de l'extension est remplacé par l'onglet passerelle de la fenêtre (même contenu). Aucune nouvelle permission.

### Mode d'emploi
- `docs/MODE-EMPLOI.md` créé : installation, mise à jour de `sudf`, lancement, extension, fenêtre FruchtDrama, appairage, comptes (dont plusieurs comptes Flow), production, statuts et bandeaux, corrections, dépannage.

### Tests
- `tests/test_workspace.cjs` (logique + contrôles statiques, vérifié par mutation) et `tests/test_workspace_chrome.cjs` (Chromium réel avec l'extension chargée, piloté par DevTools).

## 0.1.46 — 2026-11-02 (branche `sudf`) — P2 lot 1 : erreurs typées

Détail : `docs/sudf/P2-automatisation.md` (P2-01 à P2-04).

### Ajouté
- Chaque échec de tâche porte un type : `login`, `challenge`, `quota`, `refusal`, `credits`, `interface`, `timeout`, `restart`, `other` (`errors.py`). L'extension envoie `error_kind` ; le serveur classe les messages des anciennes extensions. Le type est conservé sur la tâche (`error_kind`) et sur la production (`last_error`), effacé par une reprise ou un média reçu.
- Encart « Action de votre part requise » pour une connexion ou une vérification anti-robot. Le studio ne contourne jamais ces contrôles.
- ChatGPT : le délai de renouvellement affiché (« resets in 22 hours and 16 minutes », FR/DE/EN) est lu et transmis (`retry_after`).

### Amélioré
- Un refus de contenu de ChatGPT sur une image est détecté en quelques secondes (nouvelle réponse seulement, deux lectures identiques) au lieu d'attendre 8 minutes. Un ancien refus resté dans la conversation est ignoré.

### Tests
- `tests/test_p2_errors.py` (unitaires + intégration HTTP), `tests/test_refusal_runner.cjs` (connecteur sous `vm`, vérifié par mutation), cas ajoutés dans `tests/test_composer.cjs`.

## 0.1.45 — 2026-11-02 (branche `sudf`) — P1 : économies

Détail : `docs/sudf/P1-economies.md`.

### Ajouté
- Relecture et correction de l'histoire avant de payer les images (option à la création, P1-1). « Reprendre » ne contourne pas la relecture ; chaque correction est revalidée ; une saisie non enregistrée survit au rafraîchissement.
- Feuille de personnages unique pour les productions à plusieurs personnages : une image payée au lieu d'une par personnage (P1-2).
- « Refaire » ciblé d'une image, d'un clip, de la couverture ou des personnages, avec correction écrite ; fichier précédent conservé ; refaire une image impose de refaire son clip (P1-3).
- Essai à blanc des clips Flow : tout est préparé et vérifié dans Flow, arrêt avant l'envoi, aucun crédit réservé (P1-4).
- Test d'interaction navigateur piloté par le protocole DevTools (`tests/test_ui_interactions.cjs`).

### Corrigé
- Le changement de `#job=` dans l'adresse ouvre la production demandée sans recharger la page.

## 0.1.44 — 2026-11-02 (branche `sudf`)

Fiabilité de la chaîne de production (P0). Détail des exigences : `docs/sudf/P0-fiabilite.md`.

### Corrigé
- Un montage échoué se relance avec « Reprendre », sans régénérer de média ; un montage interrompu par un redémarrage du serveur reprend automatiquement.
- Une scène dont l'envoi Flow est incertain n'est plus jamais renvoyée automatiquement. La production passe « À vérifier » ; le propriétaire confirme, scène par scène, qu'aucun clip n'existe dans Flow avant une nouvelle génération (action `confirm_no_clip`). La réservation locale n'est pas remboursée en silence.
- Le prompt Flow n'emploie plus le mot allemand « Stimme » pour toutes les langues (« Voice: »).
- Les erreurs de la boucle Flow sont écrites dans `data/server-errors.log` (une fois par minute au plus pour une même erreur).
- Un JSON de scénario invalide suit la réécriture automatique bornée (2 au plus), comme un refus éditorial.
- Un import manuel n'annule plus une génération en cours sur une autre scène.
- La requête de recherche par défaut suit la langue de création.
- La reprise d'un projet Flow mémorisé transmet l'URL du projet même pendant la navigation de l'onglet.
- La limite de mots annoncée à l'IA est celle appliquée par le validateur (20 ou 25).
- Interface : un connecteur est « en ligne » pendant 75 s, comme côté serveur ; le passage d'un connecteur ne redessine plus la page.

### Ajouté
- Lien direct `/#job=<identifiant>` vers une production.
- Encart « Envoi Flow incertain » avec un bouton de confirmation par scène.
- Tests : `tests/test_p0_reliability.py` (unitaires, intégration HTTP, montage ffmpeg réel), `tests/test_ui_browser.py` (serveur réel + Chrome sans tête), cas supplémentaire dans `tests/test_flow_session.cjs`.
