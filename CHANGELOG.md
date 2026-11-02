# Journal des modifications

Chaque version liste ce qui a été **corrigé**, **amélioré** et **ajouté**, avec l'exigence
correspondante (P0-xx, P1-x, P2-xx) détaillée dans `docs/sudf/`. Guide pour reprendre le travail :
`docs/sudf/REPRISE.md`. **Mode d'emploi détaillé** (installer, lancer, utiliser), mis à jour à chaque
version : `docs/MODE-EMPLOI.md` (section 12 : ce qui change pour l'utilisateur, version par version).

## Non publié (branche `sudf`)

Prochain : P5 lots 2 à 5 (moteurs Grok et Arena, comptes par moteur, changement de compte guidé), puis P2 lots 2 à 5. Voir `docs/sudf/REPRISE.md`.

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
