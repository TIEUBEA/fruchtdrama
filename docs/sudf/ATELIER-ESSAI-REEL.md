# Essai réel de l'Atelier Gourmand (03/11/2026, 02:20–02:30)

Objectif : produire une vraie vidéo avec l'Atelier pour relever ses écrans, ses messages, ses erreurs et sa
gestion des comptes, puis reproduire ce qui manque dans FruchtDrama. Abonnement du propriétaire ; licence
seulement décrite, jamais contournée.

## Parcours suivi

Créer → Écrite par **ChatGPT** → **Pas d'idée** → niche Fruits, Courte (8 à 10 plans, ≈ 1 min), Normale,
Vertical, Français → « Lancer la production automatiquement » coché (par défaut) → **Propose-moi dix histoires**.

| Heure | Ce que l'Atelier affiche |
|---|---|
| +0 s | « ChatGPT cherche dix histoires… 0 min 23 · en général 2 à 4 min » avec bouton ✕ |
| +40 s | **Dix histoires** : titre, pitch d'une phrase (« À dix ans, un petit citron découvre… »), pourquoi ça marche. « Clique celle que tu veux, elle deviendra ta demande. » |
| clic | L'option passe à « J'ai une idée », l'idée remplit « L'histoire, en quelques phrases » (+ « Ce qu'on voit : … »). « Histoire reprise. Clique « Écrire la fiche ». » |
| Écrire | Confirmation dans la page (pas une boîte du navigateur) : « Lancer la production automatiquement est coché : … avec tes crédits ChatGPT et Grok. On y va ? » Annuler / OK |
| +1 min | **Fiche de décision** (étape 1 sur 2) : l'histoire en une phrase, Moteur, Obstacle, Twist, Ce qu'on voit en une image, La question du spectateur ; 3 titres, 3 premières répliques, l'appel de fin, le casting (rôles), « Tu veux changer quelque chose ? », **Valider et écrire l'épisode** / Revoir la fiche avec mes remarques. En automatique : « Je prends le premier titre, le premier hook et le premier appel. » |
| +2 min | « ChatGPT écrit les plans à partir de ta fiche… 0 min 12 · en général 5 à 10 min ». Widget **EN COURS** en bas du menu avec barre de progression. |
| +8 min | « Épisode écrit : 9 plan(s) » ; **Respiration : 3.20 s/réplique · 2.86 mots/s · 0.33 tour/s** ; plan d'appel ajouté seul à la fin (« Abonne-toi pour la partie 2 ! Écris 1 pour sauver…, 2 pour… ») ; avertissements « à surveiller » : densité de parole sous 2,9 mots/s, plans avec un ou deux mots de trop (« Rien de bloquant »). |
| +8 min | Panneau **Fabriquer** : Tout fabriquer, ✎ Relire le texte, La feuille seule, Les planches seules, Les clips seuls ; compteurs Personnages 0/1, Planches 0/0, Clips 0/0 ; section Tes personnages (Ajouter, « J'ai déjà ma feuille »). |
| +8 min | **Mur ChatGPT** : bandeau en haut « Limite ChatGPT atteinte : tes images ChatGPT. Ça revient vers 08:28 (estimation). Rien n'est perdu. Tu peux attendre, ou changer de compte ChatGPT. Que faire ? » **Ouvrir ChatGPT** / **J'ai changé de compte**. Journal : « J'arrête là : le compteur ChatGPT est au mur. MUR: La limite gratuite de génération d'images est actuellement atteinte… » |

Arrêt : le compte ChatGPT connecté n'a plus d'images avant 08:28. Rien n'a été dépensé chez Grok.
Pour finir la vidéo : changer de compte ChatGPT dans la fenêtre puis « J'ai changé de compte », ou attendre.

## Écarts avec FruchtDrama (à reproduire)

| # | Atelier | FruchtDrama 0.1.53 | Priorité |
|---|---|---|---|
| 1 | Dix histoires (titre, pitch, pourquoi ça marche), un clic = la demande | absent | haute |
| 2 | Fiche de décision : moteur, obstacle, twist, image, question ; 3 titres, 3 premières répliques, appel de fin, casting ; valider ou revoir avec remarques | relecture du scénario JSON complet | haute |
| 3 | Mesure de respiration (s/réplique, mots/s, tours/s), seuil 2,9 mots/s, mots en trop par plan, « Rien de bloquant » | limite de mots par clip seulement | moyenne |
| 4 | Plan d'appel ajouté automatiquement à la fin (planche + clip) | kit de publication (texte) seulement | moyenne |
| 5 | Panneau Fabriquer : tout / feuille seule / planches seules / clips seuls, compteurs, « J'ai déjà ma feuille » | enchaînement automatique, Refaire par élément | moyenne |
| 6 | Widget « En cours » dans le menu, durée écoulée + durée habituelle | statut dans la production | moyenne |
| 7 | Bandeau de mur en haut avec heure de retour, Ouvrir ChatGPT / J'ai changé de compte | `waiting_quota` + « J'ai changé de compte » (équivalent) | fait |
| 8 | Confirmation dans la page avant de dépenser | `window.confirm` du navigateur | basse |
| 9 | Filon : onglet Comptes (abonnés, vidéos relevées, vues médianes, meilleure, virales, suivre) | vidéos seulement | moyenne |
| 10 | Options : personnages Simple/Détaillé, sous-titres Sans/Avec, captures, instructions, « Encore plus virale », « Recréer à l'identique », essai à blanc, « Chercher avec mon compte » | karaoké, essai à blanc, relecture | basse |

Captures : `atelier-creer.jpg`, `atelier-fiche-decision.jpg`.
