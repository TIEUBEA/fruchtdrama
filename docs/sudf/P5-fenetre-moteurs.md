# P5 — Fenêtre unique et moteurs vidéo (Flow, Grok, Arena)

Demande du propriétaire (02/11/2026), sur le modèle de l'Atelier Gourmand :
- un clic sur l'icône de l'extension ouvre **une nouvelle fenêtre** et **tout se passe dedans** :
  interface du studio, ChatGPT, Claude, Grok, Google Flow, Arena, ouverture et changement des comptes ;
- Grok et Arena AI s'ajoutent à Google Flow comme moteurs de création vidéo ;
- même système de **changement de compte** quand les crédits ou quotas d'un compte sont épuisés.

Priorité : passe devant les lots 2 à 5 de P2 (qui restent valables, voir `REPRISE.md`).

## Exigences

| ID | Exigence | État |
|---|---|---|
| P5-01 | Clic sur l'icône : ouvre la fenêtre FruchtDrama (onglet passerelle épinglé + studio) ou la ramène au premier plan. Pas de doublon. | Fait (0.1.47) |
| P5-02 | Tout onglet de fournisseur est créé dans cette fenêtre ; un onglet réutilisé ailleurs (projet Flow mémorisé, recherche) y est déplacé avec sa session. | Fait (0.1.47) |
| P5-03 | Fenêtre fermée : oubliée, puis recréée à la tâche suivante. Identifiant effacé au redémarrage du navigateur. | Fait (0.1.47) |
| P5-04 | « Mémoriser le compte Flow » et « Récupérer la réponse » visent le dernier onglet consulté dans la fenêtre (l'onglet actif est désormais la passerelle). | Fait (0.1.47) |
| P5-05 | Plusieurs comptes Google dans la même fenêtre : comptes ajoutés au même profil Chrome, projets Flow en `/u/N/`, passage automatique au compte suivant quand les crédits manquent (mécanisme existant, désormais dans la fenêtre). | Fait (0.1.47, documenté dans INSTALLATION.md) |
| P5-06 | Moteur vidéo au choix par production : `flow`, `grok`, `arena`. Durée de clip propre au moteur (Flow 8 s, Grok 6 s, Arena 4 à 10 s), prise en compte par le prompt, la limite de mots, le contrôle qualité et le montage. Grok et Arena restent verrouillés tant que leur connecteur n'est pas livré. | Fait (0.1.48) |
| P5-07 | Comptes par moteur : chaque profil porte un `engine`. Flow : crédits (existant). Grok et Arena : pas de solde lisible, murs de quota appris par compte (P2 lot 3). | À faire |
| P5-08 | Changement de compte Grok/Arena : une seule session à la fois par site dans un profil Chrome, donc changement **guidé** dans la fenêtre : la production attend (`waiting_account`), le bandeau indique le compte suivant, le propriétaire se connecte lui-même dans l'onglet, l'extension vérifie l'identité affichée, puis reprend. Jamais de mot de passe stocké ni saisi par l'extension. | À faire |
| P5-09 | Adaptateur Grok (`extension/grok.js`, grok.com/imagine) : image de départ, prompt, mode vidéo, envoi unique avec intention d'envoi, détection de la nouvelle vidéo, téléchargement, erreurs typées (connexion, anti-robot, quota, modération). | À faire |
| P5-10 | Adaptateur Arena (`extension/arena.js`, lmarena.ai, arène vidéo image vers vidéo) : deux vidéos anonymes A/B, la première terminée est retenue, l'autre gardée comme variante ; erreurs typées. | À faire |
| P5-11 | Essai à blanc (P1-4) disponible pour Grok et Arena : tout préparé, rien envoyé. | À faire |

## Conception de la fenêtre (fait)

`extension/workspace.js` (`FruchtWorkspace`) : `open` (clic icône), `ensure` (crée la fenêtre à la demande),
`createTab` (toujours avec `windowId`), `adopt` (`chrome.tabs.move`, la session reste), `latest`
(dernier onglet consulté correspondant à un motif), `closed`/`reset`. `manifest.json` n'a plus de
`default_popup` (sinon `action.onClicked` ne se déclenche pas) ; `popup.html` devient l'onglet passerelle.
Aucune nouvelle permission.

## Limites connues

- Les adaptateurs Grok et Arena seront écrits sur des pages que nous ne pouvons pas ouvrir avec vos comptes
  ici : ils seront testés sur des fixtures DOM, puis à vérifier chez vous en essai à blanc d'abord.
- Changer de compte pour contourner les limites gratuites d'un service peut être contraire à ses
  conditions d'utilisation : à vous d'en juger. Le studio n'utilise que les comptes que vous enregistrez et
  auxquels vous vous connectez vous-même ; il ne contourne aucune vérification.
- Arena tire des modèles au hasard : voix et dialogues varient, le contrôle qualité (paroles ≥ 85 %) filtrera.

## Tests

- `tests/test_workspace.cjs` : logique de la fenêtre sous `vm` (ouverture, recentrage, création, déplacement,
  dernier onglet, fermeture, redémarrage) + contrôles statiques (plus de `chrome.tabs.create` direct ni de
  `currentWindow`). Vérifié par mutation.
- `tests/test_workspace_chrome.cjs` : **Chromium réel** avec l'extension chargée, piloté par le protocole
  DevTools depuis le service worker : fenêtre dédiée, onglet passerelle épinglé, studio, onglets créés et
  déplacés dedans, oubli à la fermeture.
