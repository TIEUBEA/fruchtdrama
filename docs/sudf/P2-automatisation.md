# P2 — Automatisation sans surveillance

Branche `sudf`. Objectif : laisser le studio produire seul (la nuit) sans jamais dépenser à l'aveugle,
et s'arrêter proprement quand un humain est réellement nécessaire.

Décision du propriétaire (02/11/2026) : la production continue seule **uniquement si**
- la transcription correspond au texte prévu à **85 % au moins** pour chaque clip ;
- aucun défaut technique n'est détecté ;
- la revue visuelle ne signale aucun problème (statut `pass` partout, `uncertain` compris comme un arrêt).

Sinon la production s'arrête « À vérifier ».

## Exigences

| ID | Exigence | Lot |
|---|---|---|
| P2-01 | Chaque échec de tâche porte un type : `login`, `challenge`, `quota`, `refusal`, `credits`, `interface`, `timeout`, `restart`, `other`. L'extension l'envoie quand elle le connaît ; le serveur le déduit du message sinon (anciennes extensions). | 1 |
| P2-02 | Connexion requise et vérification anti-robot : message d'action humaine clair. **Aucun contournement** de CAPTCHA, jamais. | 1 |
| P2-03 | ChatGPT : un refus de contenu sur une image est détecté (nouvelle réponse seulement, confirmé par deux lectures identiques) au lieu d'attendre 8 minutes. | 1 |
| P2-04 | ChatGPT : le délai de renouvellement affiché (« resets in 22 hours and 16 minutes ») est lu et transmis. | 1 |
| P2-05 | Refus d'image : reformulation automatique graduée, niveau 1 (vocabulaire adouci + cadre tout public, **même style visuel**), niveau 2 (plus consigne « laisse de côté le détail refusé »). Après le niveau 2 : arrêt avec message clair. Niveau remis à zéro quand l'image arrive ou quand on la refait. | 2 |
| P2-06 | Quotas appris : chaque génération réussie est un passage, chaque mur un refus horodaté. Fenêtre glissante de 6 h, capacité estimée, reste, heure de reprise. Écriture unique sous verrou serveur (corrige la perte de passages de l'atelier). | 3 |
| P2-07 | Mur de quota : la production passe en `waiting_quota` (pas « À vérifier ») et reprend seule à l'heure de reprise. Aucun envoi tant que le service est au mur. Un clip Flow peut-être envoyé reste traité comme incertain (P0). | 3 |
| P2-08 | Le propriétaire peut « oublier » un mur (changement de compte) : les productions en attente repartent. | 3 |
| P2-09 | Seuil de paroles porté à 0,85 ; décision automatique et raisons enregistrées dans le rapport qualité. | 4 |
| P2-10 | File de nuit : liste ordonnée de productions, une seule active à la fois, reprise automatique des échecs réessayables (3 au plus, délai croissant), attente des quotas et crédits, retrait avec raison quand un humain est nécessaire. | 5 |
| P2-11 | File de nuit interdite en essai à blanc ; survit au redémarrage du serveur ; la pause du propriétaire est toujours respectée. | 5 |
| P2-12 | Anti-veille Windows pendant la file de nuit (`SetThreadExecutionState`), relâchée à l'arrêt. Sans effet hors Windows. | 5 |

## Conception

- `errors.py` : types, classement par message, textes d'action.
- `refusal.py` : adoucissement gradué des prompts (EN/DE/FR).
- `quotas.py` : journal passages/murs, état par service, fonctions pures testables.
- `night.py` : moteur de la file de nuit (fonctions pures sur l'état + rappels serveur).
- `power.py` : anti-veille, `kernel32` injectable pour les tests.
- Extension : `FruchtComposer.refusal`, `FruchtComposer.retryAfter`, erreurs typées (`error.kind`) remontées dans le résultat.

Réessayable automatiquement : `interface`, `timeout`, `restart`, `other` (ChatGPT/Claude, ou Flow **non envoyé**).
Jamais réessayé seul : `login`, `challenge`, refus épuisé, clip Flow incertain, réserves du contrôle qualité,
relecture d'histoire en attente, pause du propriétaire.

## Plan de test

Unitaires (types, adoucissement, fenêtre de quotas, seuil 0,85, moteur de nuit, anti-veille),
intégration HTTP (résultats typés, attente de quota puis réveil, oubli de mur, actions de la file),
JS sous `vm` (détection de refus nouvelle réponse seulement, lecture du délai), rendu navigateur (bandeaux),
vérification par mutation des correctifs principaux.
