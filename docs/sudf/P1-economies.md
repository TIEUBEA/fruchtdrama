# P1 — Économies : rien de payé sans nécessité

| ID | Exigence | État |
|---|---|---|
| P1-1 | Option « Relire et corriger l’histoire avant de payer les images » à la création. Si elle est cochée, la production s’arrête après le scénario (statut `waiting_review`). Le propriétaire corrige titre, titre de couverture, description et répliques ; chaque correction est revalidée (locuteurs, 25 mots, ou 2 répliques et 20 mots pour les nouvelles productions). Aucune génération avant la validation ; « Reprendre » ne contourne pas la relecture. L’histoire n’est plus modifiable dès que les images ont commencé. Une correction non enregistrée survit au rafraîchissement et une sortie demande confirmation. | Fait |
| P1-2 | Les nouvelles productions à plusieurs personnages demandent UNE feuille de personnages (une seule image payée) au lieu d’une image par personnage. La feuille est jointe une seule fois aux scènes et à la revue qualité ; une scène identique à la feuille est rejetée ; la feuille échouée est récupérable sans nouvelle génération ; import manuel possible (emplacement `characters`). Productions à un personnage et anciennes productions : inchangées. | Fait |

## Tests
- `tests/test_p1_review.py` : 8 unitaires, 3 intégration HTTP (dont refus d’une origine étrangère).
- `tests/test_ui_browser.py` : éditeur et option présents dans le rendu réel.
- `tests/test_ui_interactions.cjs` : Chrome piloté (DevTools) — saisie, rafraîchissement, enregistrement, refus visible, confirmation de sortie, validation. Vérifié en retirant la protection : le test échoue.
- `tests/test_p1_sheet.py` : 6 unitaires, 3 intégration HTTP (création, import manuel, récupération par la passerelle sans seconde génération).
- `tests/test_ui_browser.py` : feuille commune affichée une seule fois.
