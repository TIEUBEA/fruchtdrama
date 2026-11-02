# Journal des modifications

## Non publié (branche `sudf`)

### Ajouté
- Relecture et correction de l’histoire avant de payer les images (option à la création, P1-1). Détail : `docs/sudf/P1-economies.md`.
- Feuille de personnages unique pour les nouvelles productions à plusieurs personnages : une image payée au lieu d’une par personnage (P1-2).
- « Refaire » ciblé d’une image, d’un clip, de la couverture ou des personnages, avec correction écrite et fichier précédent conservé (P1-3).
- Test d’interaction navigateur piloté par le protocole DevTools (`tests/test_ui_interactions.cjs`).

### Corrigé
- Le changement de `#job=` dans l’adresse ouvre la production demandée sans recharger la page.

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
