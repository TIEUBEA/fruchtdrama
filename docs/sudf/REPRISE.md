# Guide de reprise — branche `sudf`

Ce document permet de reprendre le travail à tout moment, par n'importe qui (humain ou IA),
sans relire tout l'historique. Mis à jour le 03/11/2026 (soir).

> **0.1.69 (03/11, soir) : l'extension démarre le studio.** Hôte natif Chrome `com.fruchtdrama.studio` enregistré par Installer.cmd (HKCU) / installer.sh / chaque lancement ; clé fixe dans `extension/manifest.json` → identifiant `bhdmibhibonmaamgcbpmbhedhohfongj` partout. Essai réel Linux OK (studio arrêté → relancé par l'hôte en 9 s, survit à l'hôte). **Pas encore essayé sur Windows** : à faire sur un PC Windows propre avec le zip. `test_ui_interactions.cjs` échoue « retour Fruits » aussi sur l'ancien code (aléa existant).

> **REPRISE DU 03/11/2026, 18 h (à lire en premier).** Version déployée **0.1.68**, branche `sudf-ui` (non poussée).
> - Le clip 4 de l'épisode `13241637db0849a1` avait en fait été rapatrié seul à 16:59 (correspondance exacte du prompt). La revue visuelle a suivi : clip 1 conforme, clips 2-3 « incertains », clip 4 en défaut (Anissa n'enlève pas le haut de sa salopette).
> - Bug corrigé en 0.1.68 : « Refaire tout seul » sur plusieurs clips plantait au 2ᵉ (« Une tâche est en cours »). Décision du propriétaire : un clip seulement « incertain » n'est plus jamais regénéré automatiquement.
> - État réparé à la main (sauvegarde `~/Sauvegardes/state-avant-0.1.68-*.json`) : relance du clip 2 annulée, clip 2 remis. Épisode en « À vérifier », étape qualité. **Reprendre** → seul le clip 4 est refait (12 crédits, compte arnaudpkf), puis miniature, montage, sauvegarde.
> - Toujours vrai : soldes Flow à relire (« Détecter mes comptes »), notification « Port 9263 » = autre outil (fruit-france).
> - Tests : 304 Python + suites navigateur vertes.

## 1. Contexte en 30 secondes

FruchtDrama est un studio local (Windows) qui produit des vidéos « drames de fruits » :
recherche TikTok, scénario (ChatGPT/Claude), images (ChatGPT), clips (Google Flow), contrôle qualité
(faster-whisper + revue visuelle), couverture, montage ffmpeg. Serveur Python sans dépendance web
(`server.py`, port 8840), état dans `data/state.json`, extension Chrome MV3 (`extension/`) qui exécute
les tâches dans les onglets, interface `web/`.

Objectif de la branche `sudf` : automatisation de bout en bout, fiable et économe, en reprenant les
**idées** (pas le code) de l'extension « L'Atelier Gourmand » analysée dans le rapport
`Rapport_FruchtDrama_Atelier_2026-11-02` (bureau du propriétaire).

## 2. Où en est-on

| Phase | Contenu | État | Version | Doc |
|---|---|---|---|---|
| P0 | Fiabilité (13 exigences) | Terminé | 0.1.44 | `P0-fiabilite.md` |
| P1 | Économies : relecture, feuille unique, Refaire, essai à blanc | Terminé | 0.1.45 | `P1-economies.md` |
| P2 lot 1 | Erreurs typées, détection refus, délai de quota | Terminé | 0.1.46 | `P2-automatisation.md` |
| P5 lot 1 | Fenêtre unique : tout se passe dans la fenêtre FruchtDrama (P5-01..05) | Terminé | 0.1.47 | `P5-fenetre-moteurs.md` |
| P5 lot 2 | Moteur vidéo par production, durées réelles QC/montage (P5-06) | Terminé | 0.1.48 |
| P5 lots 3-5 | Comptes par moteur, changement de compte guidé, connecteurs Grok et Arena, essai à blanc (P5-07..11) | Terminé (à vérifier sur vrais comptes) | 0.1.49 | `P5-fenetre-moteurs.md` |
| P2 lots 2-5 | Anti-refus, quotas appris, seuil 85 %, file de nuit, anti-veille | Terminé | 0.1.50 | `P2-automatisation.md` |
| P3 lot 1 | Séries (suite, personnages réutilisés), kit de publication | Terminé | 0.1.52 | `P3-croissance.md` |
| P3 suite | Séries/parties, dix idées, kit publication, veille, 16:9 | À faire | | rapport `00-SYNTHESE.md` |
| P4 lots 1-2 | Corbeille, purge, rapport de panne, karaoké | Terminé | 0.1.51 | `P4-montage-ux.md` |
| P4 suite | Transitions ffmpeg, sous-titres karaoké, contrôle hauteur de voix, rapport de panne, purge `state.json`, suppression de production | À faire | | rapport `00-SYNTHESE.md` |

Avancement global estimé : environ 75 % (P0, P1, P2, P5 faits ; restent P3, P4 et la vérification réelle). Ordre décidé par le propriétaire : P5 (fenêtre unique + moteurs Grok/Arena) avant la suite de P2.

Décision du propriétaire pour le contrôle qualité automatique (02/11/2026) : continuer seul
**uniquement si** transcription ≥ 85 % pour chaque clip, aucun défaut technique, revue visuelle
`pass` partout. Sinon « À vérifier ».

## 3. Reste à faire (prêt à spécifier)

- **P3 croissance** : séries/parties avec suite d'un épisode, dix idées d'histoires d'un coup, kit de publication (titre, description, hashtags, heure), veille de la niche, format 16:9 et durées, autres langues.
- **P4 montage/UX** : transitions ffmpeg (xfade, acrossfade, punch-in), sous-titres karaoké mot à mot (horodatage whisper déjà disponible), contrôle de hauteur de voix, coupe des silences de début et de fin, rapport de panne copiable sans secret, purge de `state.json`, suppression d'une production.
- **Vérification réelle** sur Windows avec vos comptes : Flow, ChatGPT, puis Grok et Arena en essai à blanc d'abord (connecteurs écrits sur fixtures).

## 4. Règles de travail (à respecter)

- Une exigence = code + tests + doc + entrée CHANGELOG + **mise à jour de `docs/MODE-EMPLOI.md`** (section concernée + ligne dans la section 12) + commit conventionnel. Ne passer au lot suivant qu'avec toute la suite verte.
- Jamais de contournement de CAPTCHA ni de licence (l'Atelier est décrit, jamais contourné).
- Aucune dépense automatique ambiguë : un clip Flow peut-être envoyé n'est jamais renvoyé sans confirmation.
- Pas de nouvelle dépendance sans justification. Pas de push sur `main` sans PR.

## 5. Lancer les vérifications

```bash
python3 -m unittest discover -s tests -p 'test_*.py'      # 230 tests à la 0.1.52
for f in tests/*.cjs; do node "$f" || echo "ÉCHEC $f"; done  # 26 suites JS (dont Chromium réel)
python3 -m py_compile server.py errors.py quality.py editorial.py
for f in extension/*.js web/app.js; do node --check "$f"; done
git diff --check
```

Les tests navigateur (`test_ui_browser.py`, `test_ui_interactions.cjs`) ont besoin de Chrome/Chromium et Node ≥ 22 ;
ils s'ignorent proprement sinon. Vérification par mutation : retirer le correctif, le test doit échouer.

## 6. Reste à vérifier en réel

Essai sur Windows avec l'extension chargée et les vrais comptes (ChatGPT, Flow) : les pages des fournisseurs
changent souvent, seuls les tests sur fixtures DOM existent. Commencer par un **essai à blanc** (P1-4).

## 7. Fichiers clés

| Fichier | Rôle |
|---|---|
| `server.py` | État, file de tâches, `schedule()`, `accept_task_result()`, routes HTTP |
| `engines.py` | Moteurs vidéo : durées, limite de mots, longueur au montage (P5-06) |
| `engine_accounts.py` | Comptes Grok/Arena, limites par compte, rotation (P5-07/08) |
| `extension/engine-video.js` | Connecteurs Grok Imagine et LMArena (P5-09/10) |
| `refusal.py`, `quotas.py`, `power.py` | Anti-refus, limites apprises, anti-veille (P2) |
| `maintenance.py` | Corbeille, purge, sauvegardes, rapport de panne (P4-1) |
| `errors.py` | Types d'échec (P2-01) |
| `quality.py` | Contrôle technique, transcription, revue visuelle |
| `editorial.py` | Validation éditoriale du scénario |
| `flow_accounts.py`, `flow_credits.py` | Comptes Flow, crédits, ouverture automatique |
| `extension/runner.js` | Exécution d'une tâche dans l'onglet |
| `extension/composer.js` | Éditeur, bouton d'envoi, défi, refus, délai de quota |
| `extension/workspace.js` | Fenêtre unique : création, recentrage, onglets dedans (P5-1) |
| `extension/background-worker.js` | Boucle de la passerelle (toutes les 30 s) |
| `web/app.js` | Interface du studio |
