# Live TikTok du créateur de l'Atelier Gourmand (03/11/2026, 55 min)

Source : `~/Videos/Screen_Recording_20261103_233451_TikTok.mp4` (enregistrement d'écran du live « Fruits Atelier »).
Transcription faite en local (faster-whisper small). Images relevées toutes les 30 s.

## Ce que montre son outil (Atelier Gourmand)

- Extension Chrome + clé d'accès (« on a mis une clé d'accès, c'est pour sécuriser »). Prix : 29 €/mois avec le Skool (formation + outil), sans engagement. 65 membres en 10 jours.
- Pages : Le Film (studio), Créer une vidéo, Studio, Mes comptes. IA nécessaires : ChatGPT et Grok ; Claude facultatif.
- Parcours d'un épisode : fiche de décision, personnages, planches (storyboard), clips, montage (sous-titres, fond musical), miniature avec titre et hashtags.
- Créer : Écrite par (Claude/ChatGPT), Option (Pas d'idée / J'ai une idée / Refaire une virale), niche, durée, langue (5 drapeaux : FR, EN, ES, PT, DE), qualité, format.
- Refaire une virale : lien TikTok, puis « Vidéo prise » (aperçu), **« Captures en plus (facultatif) »**, case **« Recréer à l'identique »** (reformule dialogues et scènes, reste très fidèle), **« Instructions en plus »** (ex. « mets ma tête à la place du personnage X » avec une image de référence), « Lancer la production automatiquement ».
- Fiche de décision : 3 titres, hook (première réplique) personnalisable, **3 CTA proposés** et modifiables, casting avec rôles (protagoniste, antagoniste, témoin) et descriptions.
- Personnages : simple (une seule feuille pour tous, économise ChatGPT) ou détaillé (pied, visage, texture, objet iconique).
- Veille (« Le Filon ») : vidéos virales, vues, vues/h, niches (fruits, bébé…), bouton « Recréer la vidéo » puis « Voir ma recréation ».
- Production de nuit (« je dors, mon outil travaille »). Tourne sur des PC de 4 Go de RAM.
- Le Skool fournit une bibliothèque de personnages et de prompts qui ont déjà marché.

## Ses règles de contenu

- Viser la monétisation : vidéos d'au moins 1 min, environ 10 plans de 6 à 15 s, environ une vidéo par jour.
- Hook dès la 1ʳᵉ seconde (chiffre, info concrète, émotion forte), première image soignée, rétention jusqu'au bout.
- CTA final qui fait commenter : « partie 2, abonne-toi ; je dénonce mon père dis 1, je ne le dénonce pas dis 2 » (387 commentaires).
- Séries en plusieurs parties : une vidéo qui marche (80 k vues) reçoit une partie 2 et 3. Grille de profil cohérente.
- Hashtags de la niche et de la langue visée, pas des hashtags généraux comme #ia.
- Tester le même contenu sur TikTok, Instagram, YouTube Shorts et Facebook, mais jamais sur plusieurs comptes TikTok (contenu non original, risque de shadow ban).
- Certaines langues et certains pays ne sont pas éligibles à la monétisation. L'audience espagnole réagit très bien.

## Ses astuces pour Grok

- Grok Premium à 30 €/mois : environ 30 vidéos d'une minute par mois.
- Prompt précis mais court : au-delà d'environ 4 000 caractères, Grok « lit en diagonale ».
- Faire les clips en 480p, puis passer le montage final en 1080p (upscale) : moins cher.
- Désigner les personnages par position dans l'image, couleur et identité.
- Flow : meilleure qualité, plus cher. Seedance : très bon, trop cher.

## Écarts avec FruchtDrama 0.1.71

Déjà présent : Filon + Recréer + Voir ma recréation, fiche avec 3 titres et 3 hooks, casting à rôles, personnages simple/détaillé, sous-titres, nuit, séries, miniature, hashtags, clé d'accès (lot 2).

Absent ou différent :
1. Durée réelle : l'essai réglé sur 30 s a donné 21,6 s (4 plans, puis silences coupés). Une cible d'1 min peut finir sous 60 s, donc non monétisable.
2. Pas de « Recréer à l'identique », pas de « Captures en plus », pas d'instructions pour remplacer un personnage par une photo de référence.
3. Un seul appel de fin (`end_call`) au lieu de 3 CTA au choix.
4. 3 langues (DE, FR, EN) au lieu de 5 (ES et PT manquent). Pas d'accent ni de langue libre (créole). Pas d'alerte sur l'éligibilité à la monétisation.
5. Pas de mode « brouillon 480p puis upscale 1080p ».
6. Pas de bibliothèque de personnages réutilisables d'une histoire à l'autre.
7. Pas d'aide à la publication sur plusieurs plateformes.

## Suite donnée (04/11/2026, 0.1.72)

Choix du propriétaire : durée garantie, trois appels de fin et Recréer à l'identique. Les trois sont faits.
Restent à décider : espagnol et portugais, langue libre et alerte de monétisation par pays, brouillon 480p puis 1080p, bibliothèque de personnages, aide à la publication sur plusieurs plateformes.
