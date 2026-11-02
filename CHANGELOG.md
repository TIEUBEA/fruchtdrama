# Journal des modifications

Chaque version liste ce qui a été **corrigé**, **amélioré** et **ajouté**, avec l'exigence
correspondante (P0-xx, P1-x, P2-xx) détaillée dans `docs/sudf/`. Guide pour reprendre le travail :
`docs/sudf/REPRISE.md`. **Mode d'emploi détaillé** (installer, lancer, utiliser), mis à jour à chaque
version : `docs/MODE-EMPLOI.md` (section 12 : ce qui change pour l'utilisateur, version par version).

## Non publié (branche `sudf`)

Prochain : P3 (séries, idées, kit de publication, veille, 16:9) et P4 (montage avancé, sous-titres karaoké, rapport de panne). Voir `docs/sudf/REPRISE.md`.

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
