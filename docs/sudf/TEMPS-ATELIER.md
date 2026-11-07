# Temps par étape : Atelier Gourmand contre FruchtDrama

Référence : essai réel de l'Atelier 1.0.22 du 06/11/2026, vidéo @fruitystories36 « Bananito pretended to be poor »
(118 s, 3,8 M vues), Claude Opus 5.5 Élevé, Moyenne, Normale, Recréer à l'identique, boucle complète.
Règle : chaque étape de FruchtDrama doit prendre sensiblement le même temps (écart visé : 25 % au plus).

| Étape | Atelier | Détail Atelier |
|---|---|---|
| Récupération de la vidéo | ≈ 2 min | téléchargement, transcription, 63 images |
| Fiche de décision + correction | ≈ 2 min 40 | 1 min 20 fiche, 20 s correction |
| Plans (épisode) + correction | ≈ 6 min 40 | 4 min 40 écriture, 2 min correction |
| Feuille de personnages | ≈ 1 min 20 | 5 personnages |
| Planches (17) | ≈ 25 min | ≈ 1 min 30 par planche, contrôles groupés par 2 à 6 |
| Clips | non mesuré | Grok à sa limite pendant l'essai |

Total jusqu'aux planches finies : ≈ 38 min.

Mesure FruchtDrama : `tools/temps_etapes.py <id d'épisode>` lit le journal de l'épisode et affiche le même tableau.

## Écarts relevés et corrigés (journal)

| Date | Écart mesuré | Cause | Correctif |
|---|---|---|---|
| 06/11 | Scénario 52 min contre 9 min 20 | 4 refus d'affilée, un défaut signalé à la fois, réécriture complète (5 à 7 min) à chaque refus | 0.1.88 : tous les défauts dans un seul refus ; mots de taille interdits d'avance ; tolérance 3 mots/s ; réécriture légère (scénario refusé + défauts, sans images) |
| 06/11 | Clips après les 16 planches (l'Atelier les lance pendant) | une seule tâche à la fois par fenêtre | 0.1.89 : deux voies (texte/images et vidéo) ; les clips continuent pendant la limite d'images ChatGPT |
| 06/11 | 30 min perdues après rechargement de l'extension | nouvelle fenêtre laissée désactivée, comptes Flow liés à l'ancienne | 0.1.89-0.1.90 : la fenêtre en ligne reprend le travail et les comptes ; plus de lancement de Chrome inutile |
| 06/11 | Planches : 59, 90, 120, 151 s (multiples de 30 s) | l'extension ne regardait le studio que toutes les 30 s (alarme) | 0.1.90 : nouveau passage 3 s après chaque passage tant qu'une tâche tourne |
| 06/11 | Clip Flow : « page vide après 90 s » (2 fois) | à établir : l'extension dit maintenant ce qu'elle voit dans l'onglet | en cours |
