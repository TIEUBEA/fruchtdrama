# Guide de reprise — branche `sudf`

Ce document permet de reprendre le travail à tout moment, par n'importe qui (humain ou IA),
sans relire tout l'historique. Mis à jour le 02/11/2026.

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
| P2 lot 2 | Reformulation anti-refus graduée (P2-05) | À faire | | `P2-automatisation.md` |
| P2 lot 3 | Quotas appris, `waiting_quota`, réveil auto, oubli de mur (P2-06..08) | À faire | | `P2-automatisation.md` |
| P2 lot 4 | Seuil paroles 0,85 + décision auto dans le rapport (P2-09) | À faire | | `P2-automatisation.md` |
| P2 lot 5 | File de nuit + anti-veille Windows (P2-10..12) | À faire | | `P2-automatisation.md` |
| P3 | Séries/parties, dix idées, kit publication, veille, 16:9 | À faire | | rapport `00-SYNTHESE.md` |
| P4 | Transitions ffmpeg, sous-titres karaoké, contrôle hauteur de voix, rapport de panne, purge `state.json`, suppression de production | À faire | | rapport `00-SYNTHESE.md` |

Avancement global estimé : environ 55 % (le périmètre a grandi avec P5). Ordre décidé par le propriétaire : P5 (fenêtre unique + moteurs Grok/Arena) avant la suite de P2.

Décision du propriétaire pour le contrôle qualité automatique (02/11/2026) : continuer seul
**uniquement si** transcription ≥ 85 % pour chaque clip, aucun défaut technique, revue visuelle
`pass` partout. Sinon « À vérifier ».

## 3. Détail des lots P2 restants (prêts à coder)

**Lot 2 — anti-refus (`refusal.py`)**
- Sur échec `refusal` d'une tâche `chat_image` (slots `characters`, `character:x`, `image:i`, `cover`) :
  niveau 1 puis 2 dans `j['refusal_levels'][slot]`, statut `running`, nouvelle tâche.
- Niveau 1 : substitutions EN/DE/FR (blood → red juice, knife → kitchen utensil, gun/weapon → object,
  corpse → motionless figure, kidnap → disappear, underwear → outfit…) + préfixe tout public
  qui **garde le style visuel décrit** (défaut de l'Atelier : il forçait le cartoon).
- Niveau 2 : + « young woman » → « woman »… + consigne « laisse de côté le détail refusé, ne pose pas de question ».
- Après niveau 2 : `attention` avec message clair. Remise à zéro quand l'image arrive (`accept_task_result`) ou dans `redo()`.
- Brancher dans `schedule()` aux 4 endroits où le prompt d'image est construit.

**Lot 3 — quotas (`quotas.py`)**
- `STATE['quotas']={'passes':[[ts,service]],'walls':[[ts,service,msg,retry_at]]}`, bornés à 3000/200.
- Services : `chatgpt_image`, `chatgpt_text`, `claude_text`, `flow_video`. Passage = succès d'une tâche génératrice.
- Fenêtre 6 h ; capacité = passages dans les 6 h avant le dernier mur ; reprise = `retry_after` du fournisseur,
  sinon plus vieux passage de la fenêtre + 6 h, sinon mur + 30 min.
- Échec `quota` : statut `waiting_quota` (sauf clip Flow peut-être envoyé : reste incertain, P0).
- `schedule()` : ne pas créer de tâche pour un service au mur. Ajouter `waiting_quota` aux statuts d'arrêt.
- `dispatch_once()` : réveiller les productions dont la reprise est passée. Route `POST /api/quota/forget {service}`.
- Interface : pastilles par service (« ≈ n restants », « au mur, reprise HH:MM »).

**Lot 4 — seuil QC**
- `quality.compare` : seuil 0,8 → constante `MIN_MATCH=0.85` ; écrire `report['decision']` et `report['thresholds']` dans `schedule_quality`.

**Lot 5 — file de nuit (`night.py`, `power.py`)**
- `STATE['night']={'active','ids','failures','retry_at','log'}` ; statut `waiting_night` pour les productions qui attendent leur tour.
- Une seule production active. Échec réessayable (`errors.RETRYABLE`, et `last_error` présent) : 3 essais max, délai croissant, passage en fin de file.
- Retrait avec raison : `login`, `challenge`, refus épuisé, clip incertain, réserves QC, relecture en attente, pause du propriétaire.
- Interdite en essai à blanc. Anti-veille : `SetThreadExecutionState` appelé **depuis le thread de la boucle de dispatch** (l'état est par thread).

## 4. Règles de travail (à respecter)

- Une exigence = code + tests + doc + entrée CHANGELOG + **mise à jour de `docs/MODE-EMPLOI.md`** (section concernée + ligne dans la section 12) + commit conventionnel. Ne passer au lot suivant qu'avec toute la suite verte.
- Jamais de contournement de CAPTCHA ni de licence (l'Atelier est décrit, jamais contourné).
- Aucune dépense automatique ambiguë : un clip Flow peut-être envoyé n'est jamais renvoyé sans confirmation.
- Pas de nouvelle dépendance sans justification. Pas de push sur `main` sans PR.

## 5. Lancer les vérifications

```bash
python3 -m unittest discover -s tests -p 'test_*.py'      # 184 tests à la 0.1.49
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
| `errors.py` | Types d'échec (P2-01) |
| `quality.py` | Contrôle technique, transcription, revue visuelle |
| `editorial.py` | Validation éditoriale du scénario |
| `flow_accounts.py`, `flow_credits.py` | Comptes Flow, crédits, ouverture automatique |
| `extension/runner.js` | Exécution d'une tâche dans l'onglet |
| `extension/composer.js` | Éditeur, bouton d'envoi, défi, refus, délai de quota |
| `extension/workspace.js` | Fenêtre unique : création, recentrage, onglets dedans (P5-1) |
| `extension/background-worker.js` | Boucle de la passerelle (toutes les 30 s) |
| `web/app.js` | Interface du studio |
