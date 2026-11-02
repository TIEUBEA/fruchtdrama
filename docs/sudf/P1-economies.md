# P1 — Économies : rien de payé sans nécessité

| ID | Exigence | État |
|---|---|---|
| P1-1 | Option « Relire et corriger l’histoire avant de payer les images » à la création. Si elle est cochée, la production s’arrête après le scénario (statut `waiting_review`). Le propriétaire corrige titre, titre de couverture, description et répliques ; chaque correction est revalidée (locuteurs, 25 mots, ou 2 répliques et 20 mots pour les nouvelles productions). Aucune génération avant la validation ; « Reprendre » ne contourne pas la relecture. L’histoire n’est plus modifiable dès que les images ont commencé. Une correction non enregistrée survit au rafraîchissement et une sortie demande confirmation. | Fait |
| P1-2 | Les nouvelles productions à plusieurs personnages demandent UNE feuille de personnages (une seule image payée) au lieu d’une image par personnage. La feuille est jointe une seule fois aux scènes et à la revue qualité ; une scène identique à la feuille est rejetée ; la feuille échouée est récupérable sans nouvelle génération ; import manuel possible (emplacement `characters`). Productions à un personnage et anciennes productions : inchangées. | Fait |
| P1-3 | « Refaire » ciblé : une image, un clip, la couverture, un personnage ou la feuille, avec une correction écrite (500 caractères) ajoutée au prompt. Fichier précédent conservé et historisé (`redo_history`). Refaire une image dont le clip existe exige de refaire les deux (le clip vient de l’image). Personnages verrouillés dès qu’une scène existe. MP4 final et compte rendu invalidés ; la production reprend à l’étape concernée, sans jamais avancer une étape antérieure. Refusé pendant une tâche ou un montage. Les anciens envois Flow résolus ne redeviennent pas « incertains ». Confirmation de coût pour les clips dans l’interface. | Fait |
| P1-4 | Essai à blanc des clips Flow (option à la création ou action `set_dry_run`). Le connecteur configure et vérifie tout (compte, modèle, coût, x1, 9:16, image, prompt) puis s’arrête avant l’intention d’envoi et le clic : aucune réservation, rien de facturé. Un essai réussi met la production en pause ; un écart (coût, modèle) est signalé comme un échec normal. Le passage en production réelle demande confirmation, reconstruit les tâches en attente et est refusé pendant une tâche en cours. Un essai interrompu ne devient jamais « incertain ». Un résultat « essai » sur une tâche réelle n’est pas accepté comme essai. | Fait |

## Tests
- `tests/test_p1_review.py` : 8 unitaires, 3 intégration HTTP (dont refus d’une origine étrangère).
- `tests/test_ui_browser.py` : éditeur et option présents dans le rendu réel.
- `tests/test_ui_interactions.cjs` : Chrome piloté (DevTools) — saisie, rafraîchissement, enregistrement, refus visible, confirmation de sortie, validation. Vérifié en retirant la protection : le test échoue.
- `tests/test_p1_sheet.py` : 6 unitaires, 3 intégration HTTP (création, import manuel, récupération par la passerelle sans seconde génération).
- `tests/test_ui_browser.py` : feuille commune affichée une seule fois.
- `tests/test_p1_redo.py` : 9 unitaires, 1 intégration HTTP.
- `tests/test_ui_interactions.cjs` : « Refaire la couverture » piloté dans Chrome (dialogue de correction, tâche unique, final invalidé).
- Défaut trouvé par ce test et corrigé : le changement de `#job=` dans l’URL ne changeait pas la production affichée.
- `tests/test_dry_run.cjs` : `run()` complet sur une page Flow simulée — aucun clic Envoyer ni intention en essai, envoi réel inchangé, écart de coût détecté ; vérifié par mutation.
- `tests/test_p1_dry_run.py` : 5 tests via la passerelle HTTP (essai, pause, production réelle avec réservation, falsification refusée, changement de mode, redémarrage).
