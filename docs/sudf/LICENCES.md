# Clés d'accès FruchtDrama (formation payante)

Décisions du propriétaire (03/11/2026) :

| Sujet | Décision |
|---|---|
| Durée | 3 mois, comptés à partir de la **1ʳᵉ activation** (pas de la création de la clé) |
| Ordinateurs | **2** par clé en même temps ; le propriétaire peut libérer une place |
| Fin d'accès | **Consultation seule** : voir et télécharger les vidéos faites ; plus de création ni de fabrication ; rien n'est supprimé |
| Testeurs (collègues) | Zip libre, sans clé ; les clés arrivent dans une version suivante |
| Modèle | Vérification en ligne (option B) : révocation, prolongation, limite d'ordinateurs |

## Parcours

Propriétaire : page d'administration privée → « Nouvelle clé » (nom, e-mail, durée, ordinateurs) → clé `FD-XXXX-XXXX-XXXX-XXXX` envoyée avec le zip. Même page : activations, prolonger, annuler, libérer un ordinateur.

Élève : au premier lancement, « Entre ta clé ». Vérification au démarrage puis toutes les 24 h ; 3 jours de marge sans internet ; bandeau 7 jours avant la fin.

## Architecture

- Serveur : projet séparé `~/Projets/Dev/fruchtdrama-licences` (Next.js App Router, TypeScript strict, Prisma, PostgreSQL Neon, Vercel, shadcn/ui pour l'administration).
- Une route publique `POST /api/v1/licence` `{key, machine, label, version}` : active si besoin, met à jour `lastSeen`, renvoie un **jeton signé** (RSA-SHA256, PKCS#1 v1.5) : `{licence, machine, holder, expiresAt, checkedAt}`. Refus typés : `unknown`, `revoked`, `machines_full`, `expired`.
- La clé n'est jamais stockée en clair (empreinte SHA-256) ; 80 bits d'aléa, alphabet sans caractères ambigus.
- Studio : `licence.py`, sans dépendance (vérification RSA en Python standard). Jeton dans `data/licence.json`. Empreinte d'ordinateur anonyme (SHA-256 de l'identifiant machine). Le blocage est fait **côté serveur du studio** (création et tâches), pas seulement dans l'interface.
- Données envoyées : clé, empreinte d'ordinateur, nom d'ordinateur choisi, version. Rien d'autre.
- Interrupteur `LICENCE_REQUIRED` : désactivé tant que le serveur de clés n'est pas en ligne (zip des testeurs).

## Lots

1. Serveur de clés + administration (tests vitest).
2. Studio : « Entrer ma clé », bandeau, consultation seule, blocage (tests Python + navigateur).
3. Installeur Windows unique `Setup-FruchtDrama.exe` (Python et FFmpeg inclus).

Limite assumée : un logiciel installé chez l'élève peut être modifié par quelqu'un de technique ; la vérification en ligne et la compilation (lot 3) relèvent fortement le niveau, sans garantie absolue.

## État au 03/11/2026 (soir)

- Lot 1 fait : `~/Projets/Dev/fruchtdrama-licences` (branche `dev`), 18 tests vitest, essai réel sur PostgreSQL local (Docker `fd-licences-test`, port 55432) et administration essayée dans un vrai navigateur. **Pas encore en ligne** : il faut `vercel login` (jeton expiré), une base Neon, et la paire de clés RSA de production (clé privée dans Vercel uniquement, module public dans `licence.py` `PUBLIC_MODULUS_HEX`).
- Lot 2 fait (0.1.70) : `licence.py`, verrous dans `server.py` (`schedule`, `start_render`, distribution des tâches, création, suite de série), écran de clé et bandeaux dans `web/atelier.js`. `REQUIRED = False` tant que le service n'est pas en ligne.
- Attention : la session de travail a une variable `DATABASE_URL` globale vers une base Neon d'un autre projet ; elle passe avant `.env`. Toujours charger `.env` explicitement (`set -a; . ./.env`) pour les essais locaux.
- Pour activer les clés : déployer, mettre `PUBLIC_MODULUS_HEX` et `URL`, passer `REQUIRED = True`, refaire le zip.
- Lot 3 à faire : installeur Windows unique.
