# Ouvertures répétées de Flow — 4 novembre 2026

## Cause vérifiée dans le code

La surveillance des crédits pouvait préparer une nouvelle lecture de compte même au repos et ouvrir le profil Chrome correspondant lorsque sa passerelle était hors ligne. Les échecs de lecture et les comptes multiples pouvaient répéter ce cycle. L'ouverture d'une nouvelle fenêtre du studio créait également un onglet Flow et déclenchait un scan complet.

## Correction

- `flow_background_checks` est désactivé par défaut et dans cette installation. Les anciens contrôles automatiques encore en attente sont annulés, sans supprimer de compte ni changer de solde.
- La surveillance des recharges ne demande plus de scan automatique dans ce mode.
- L'ouverture du studio ne crée plus d'onglet Flow pour lire des soldes et ne déclenche plus de détection complète des comptes. La lecture passive observe seulement les onglets déjà présents.
- « Détecter mes comptes », une vérification de solde demandée par le propriétaire et les générations de clips peuvent toujours ouvrir leur onglet nécessaire.
- Le réglage antérieur de génération/rotation automatique est conservé ; il est distinct de la surveillance en arrière-plan.

## Vérification

35 tests Python Flow réussis. Tests du lecteur de sites et 11 scénarios du connecteur réussis. Un test répète 50 passages du répartiteur avec des comptes vides et un navigateur hors ligne : aucun lancement de navigateur. Autres cas : vérification manuelle conservée, ancien contrôle automatique annulé, solde intact, scan non déclenché à l'échéance par défaut, lecture passive sans ouvrir d'onglet manquant.

Serveur relancé et vérifié : huit comptes Flow et un autre compte conservés, zéro contrôle automatique de crédits actif et zéro scan en attente. Aucun crédit dépensé pour ce correctif.

## Dernière activation nécessaire

Les fichiers de l'extension ont été mis à jour dans leur dossier existant. Il reste à recharger cette extension dans Chrome. La tentative automatique s'est arrêtée : Computer Use ne pouvait pas déterminer l'URL courante avec une confiance suffisante pour appliquer sa politique. Aucun contournement ni rechargement effectué lors de cette tentative. Le comportement réel du navigateur après rechargement reste donc à vérifier.

Dans Chrome : `chrome://extensions`, carte FruchtDrama, bouton de rechargement. Ne pas supprimer l'extension et ne pas effacer ses données. Les onglets Flow déjà ouverts ne sont pas fermés automatiquement par le correctif.
