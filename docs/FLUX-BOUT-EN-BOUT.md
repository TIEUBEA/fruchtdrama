# FruchtDrama — Flux de bout en bout : une vidéo entièrement automatisée

Version 0.1.60 (branches `sudf` / `sudf-ui`). Ce document décrit ce qui se passe, étape par étape,
quand vous lancez une production sans intervenir, et ce que vous devez préparer une seule fois.

## A. Préparation unique (environ 30 minutes)

1. Installer : voir `INSTALLATION.md` (Python 3.11/3.12, Chrome, FFmpeg, `Installer.cmd`).
2. Lancer le studio : `Lancer-Studio.cmd` → http://127.0.0.1:8840.
3. Charger l'extension : `chrome://extensions` → Mode développeur → **Charger l'extension non empaquetée** → dossier `extension`. Épingler l'icône.
4. Cliquer sur l'icône : la **fenêtre FruchtDrama** s'ouvre sur le studio. Tout se passe dans cette fenêtre et dans la page du studio (plus d'onglet Passerelle).
5. Rien à copier : l'extension enregistre seule la clé cachée du studio au premier clic (Mes comptes affiche « Clé enregistrée »).
6. Dans la fenêtre, se connecter soi-même à : ChatGPT, TikTok, Google Flow et Grok (il prend les clips que Flow ne fait pas).
7. Flow : Mes comptes → profil avec solde réel ; ouvrir un projet Flow → Passerelle → **Mémoriser le compte Flow de cet onglet**. Répéter pour chaque compte Google (ajoutés au même profil Chrome). Cocher **Ouvrir Flow et passer au compte suivant automatiquement**.
8. Mes comptes → **Mes comptes** : chaque adresse une seule fois, services cochés (ChatGPT, Flow, Grok…), crédits Flow si connus.
9. Chrome : autoriser les téléchargements multiples pour https://flow.google.com.
10. **Premier essai : cocher « Essai à blanc »** pour vérifier les connecteurs sans rien dépenser.

## B. Ce que fait le studio, seul, pour une vidéo

| # | Étape | Où | Ce qui se passe | Arrêt possible (et quoi faire) |
|---|---|---|---|---|
| 1 | Recherche | TikTok (fenêtre FruchtDrama) | Recherche de références dans la langue choisie, classement par chiffres vérifiables. | « Références requises » : choisir ou importer une référence. |
| 2 | Scénario | ChatGPT ou Claude | Cinq concepts comparés, histoire originale en JSON (scènes, dialogues courts adaptés à la durée du clip), validation éditoriale, réécriture automatique (2 fois max). | « Histoire à relire » si l'option est cochée : corriger puis valider. |
| 3 | Personnages | ChatGPT | Une seule feuille pour tout le casting (ou images reprises de la partie précédente d'une série). | Refus : reformulation automatique niveau 1 puis 2. |
| 4 | Scènes | ChatGPT | Une image par scène avec la feuille de personnages en référence ; copies exactes rejetées. | Limite ChatGPT : attente puis reprise seule. |
| 5 | Clips | Flow puis Grok | Plans de 10 s chez Flow (Grok : 6 s). Image de la scène + prompt + dialogue exact ; coût vérifié avant envoi (Flow). Un essai Flow ; clip non généré (refus, erreur, délai, envoi incertain) : bascule immédiate sur Grok, sans validation ; le clip Grok est téléchargé et ajouté, la production continue. | Crédits Flow épuisés : compte suivant automatiquement. Flow puis Grok en échec : alerte « Clip N : Flow (raison) puis Grok (raison) — clip à refaire », clip mis de côté, les autres continuent ; « Refaire » sur ce clip. Envoi Flow incertain : ne bloque rien ; si le clip Flow est retrouvé ensuite, il complète ou remplace celui de Grok. |
| 6 | Contrôle qualité | Local + ChatGPT | Durée, vertical, audio, transcription (faster-whisper), revue visuelle des images extraites. Continue seul si paroles ≥ 85 %, aucun défaut, revue visuelle sans réserve. | « À vérifier » : écouter, valider ou « Refaire » le clip. |
| 7 | Couverture | ChatGPT | Couverture avec titre court, style de référence. | Refus : reformulation automatique. |
| 8 | Montage | Local (ffmpeg) | Clips normalisés 720×1280, durée réelle par moteur, sous-titres karaoké calés sur la voix, son normalisé −14 LUFS. | Attend tous les clips. Échec : « Reprendre » relance le montage sans régénérer. |
| 8 bis | Originalité | Local | Score d'originalité estimé (images comparées aux vidéos du Filon, textes, origine, répétition, durée, mention IA), recommandation et changements conseillés. | « Corrigez avant de publier » ou « Publication déconseillée » : suivre les conseils, Refaire l'élément, Recalculer. |
| 9 | Prêt | Studio | MP4, couverture, description, **kit de publication** (titre, hashtags, premier commentaire, créneaux). | — |

Puis, au choix : **Écrire la suite** (partie N+1, mêmes personnages, rien repayé pour eux).

## B bis. Jamais d'étape silencieuse

- Une étape (scénario, planches, clips, montage) qui dépasse sa durée normale affiche un bandeau rouge « Bloqué : … depuis N min » sur la page épisode, la carte du Studio et le menu latéral, avec la raison et **Relancer cette étape**.
- En pause ou en action requise : gros bandeau « En pause — rien ne tourne » ou « Arrêté — action requise », avec la raison et **Reprendre**.

## C. Plusieurs vidéos sans surveillance : la file de nuit

1. Créer les productions (sans essai à blanc ; histoire validée si relecture cochée).
2. Sur chacune : **Ajouter à la file de nuit**. Puis Studio → **Démarrer la file de nuit**.
3. Une production à la fois ; erreurs techniques relancées 3 fois ; limites et crédits attendus ;
   productions qui ont besoin de vous retirées avec la raison (voir le journal de la file).
4. Windows ne se met pas en veille pendant la file. Laisser le PC branché, Chrome et la fenêtre FruchtDrama ouverts.

## D. Ce qui reste toujours manuel (par sécurité ou par règle des sites)

- Se connecter aux comptes et résoudre une vérification anti-robot : jamais contourné.
- Changer de compte Grok (un seul compte connecté par site et par profil Chrome).
- Refaire un clip que Flow puis Grok n'ont pas fait (« Refaire » avec une consigne, ou importer un clip).
- Valider un contrôle qualité avec réserves, confirmer qu'un clip Flow incertain n'existe pas.
- Publier sur TikTok (le studio prépare le kit, il ne publie pas).

## E. Limites connues

- Grok Imagine n'a pas de réglage de durée dans son connecteur : ses clips restent à 6 s (Flow : 10 s).
- Arena et Vidogrid sont retirés du studio (0.1.97) : seuls Google Flow et Grok font les clips.
- Les pages ChatGPT, Flow et Grok changent souvent : un connecteur peut demander une correction.
- Synchronisation labiale et identité des voix : jamais certifiées automatiquement.
