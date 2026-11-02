# P0 — Fiabilité de la chaîne de production

Branche : `sudf`. Base : `main` 5ecbe42 (v0.1.43). Référence : audit du 2 novembre 2026.

## 1. Exigences

| ID | Exigence | Origine (audit) |
|---|---|---|
| P0-01 | Une production à l'étape Montage dont le montage a échoué doit pouvoir être relancée par « Reprendre », sans régénérer aucun média. | Bug 1 |
| P0-02 | Après un redémarrage du serveur, une production restée en statut `rendering` doit relancer automatiquement son montage local. | Bug 2 |
| P0-03 | Aucun chemin du serveur ne doit créer un nouvel envoi Flow pour une scène dont un envoi précédent est incertain (réservation non remboursée, clip absent). La production passe « À vérifier » avec un message clair. | Bug 3 |
| P0-04 | Le propriétaire peut lever ce blocage, scène par scène, en confirmant explicitement qu'aucun clip n'existe dans Flow. L'action est journalisée. Récupérer ou importer le clip lève aussi le blocage. | Bug 3 |
| P0-05 | Le prompt Flow ne contient aucun mot propre à une langue de création autre que celle demandée (suppression de « Stimme »). | Bug 4 |
| P0-06 | Toute mutation de l’état partagé se fait sous `LOCK`. Vérification : l’échec de lancement était déjà sous verrou (faux positif de l’audit) ; il est désormais écrit sur le profil vivant, sous verrou explicite. | Bug 5 |
| P0-07 | Une exception de la boucle de dispatch est journalisée sur la sortie d'erreur (`data/server-errors.log`), sans inonder le journal (même erreur au plus une fois par minute), et la boucle continue. | Bug 6 |
| P0-08 | L'interface considère un connecteur en ligne pendant 75 s, comme le serveur. Le passage d'un connecteur (champ `seen`) ne redessine pas la page. | Bugs 7 et 8 |
| P0-09 | Une réponse de scénario structurellement invalide déclenche la même réécriture automatique (2 au plus) qu'un refus éditorial. | Bug 9 |
| P0-10 | Un import manuel n'annule plus une génération en cours sur une autre scène ; seules les tâches en attente et la tâche de la même scène sont annulées. | Bug 10 |
| P0-11 | La requête de recherche par défaut suit la langue de création. | Bug 11 |
| P0-12 | La reprise d'un projet Flow mémorisé transmet l'URL du projet, même si Chrome renvoie encore l'ancienne URL de l'onglet. | Bug 12 |
| P0-13 | La limite de mots par scène annoncée dans le prompt est celle que le validateur applique (20 pour les nouvelles productions, 25 sinon). | Bug 15 |

Hors périmètre P0 (planifié P1 à P4) : purge de `state.json`, suppression de productions, gabarits de couverture, chemins Chrome non Windows, version de Python annoncée.

## 2. Conception

- `schedule()` traite l'étape `edit` : si aucun MP4 final n'existe, statut `rendering` et `start_render()`.
- `recover_after_restart()` regroupe la logique de démarrage (tâches réclamées en échec, réparation des scènes, relance des montages) ; testable sans lancer le serveur HTTP.
- `uncertain_clip_tasks(j)` : tâches `flow_video` en échec, avec réservation non remboursée, non acquittées, dont la scène n'a pas de clip. Utilisé par `schedule()` (blocage), l'action `resume` (message), l'action `confirm_no_clip` (acquittement) et `public_state()` (champ `uncertain_clips` pour l'interface).
- L'acquittement ne rembourse pas la réservation locale : le solde réel reste à vérifier dans Flow (vérification automatique ou manuelle existante).
- `dispatch_once()` encapsule un tour de boucle avec journalisation limitée.

## 3. Plan de test

| Type | Contenu |
|---|---|
| Unitaires Python | Un test par exigence P0-01 à P0-13 côté serveur (`tests/test_p0_reliability.py`) |
| Intégration HTTP | Reprise refusée puis autorisée après `confirm_no_clip`, import manuel ciblé, requête par langue, via le vrai serveur HTTP |
| Unitaires JS | `prepareProject` avec une URL d'onglet périmée (`tests/test_flow_session.cjs`) |
| Non-régression | Les 96 tests Python et 19 suites JS existants |
| Statique | `python -m py_compile`, `node --check` sur tous les scripts, `git diff --check` |
| Interface (bout en bout) | Serveur réel lancé sur un dossier temporaire, page chargée dans Chrome sans tête, rendu vérifié |
| Montage réel | ffmpeg sur de vrais clips générés localement, relancé après échec |
