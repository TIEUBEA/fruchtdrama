# FruchtDrama — édition locale à partager, 0.1.59

Cette archive contient uniquement le logiciel. Aucun compte, crédit, session Chrome, code d'appairage, historique ou production du fournisseur de la copie n'est inclus. Les captures et modèles de couverture provenant de son compte sont exclus ; les nouvelles couvertures utilisent les consignes de style du logiciel et vos propres scènes.

## Installer sur Windows 10/11 64 bits

1. Extraire entièrement le ZIP dans un dossier personnel, par exemple Documents/FruchtDrama. Ne pas lancer les fichiers directement dans le ZIP.
2. Installer Chrome et Python 3.11 ou 3.12 64 bits depuis leurs sites officiels. Pour Python, cocher **Add python.exe to PATH**.
3. Installer FFmpeg avec ffprobe et vérifier qu'ils sont dans le PATH. Une possibilité sous Windows : ouvrir un terminal et exécuter `winget install --id Gyan.FFmpeg --exact`. Fermer ensuite le terminal pour actualiser le PATH.
4. Double-cliquer sur **Installer.cmd**. Lire les conditions, puis saisir **ACCEPTER**. L'installateur crée `.venv`, installe les dépendances et télécharge le modèle vocal local. L'opération nécessite Internet et peut prendre plusieurs minutes. Les modèles peuvent occuper plusieurs centaines de Mo ; les productions nécessitent davantage d'espace.
5. Après « Installation terminée », double-cliquer sur **Lancer-Studio.cmd**. L'application ouvre http://127.0.0.1:8840.

L'installation n'achète aucun abonnement. Les générations consomment les quotas ou crédits de vos services. Aucun binaire Python, Chrome ou FFmpeg n'est fourni dans ce ZIP. Les paquets téléchargés conservent leurs licences respectives.

## Connecter vos comptes

1. Dans **Mes comptes**, créer votre propre profil Flow et renseigner le solde réel. Aucun profil ne doit déjà exister au premier démarrage.
2. Dans Chrome, ouvrir `chrome://extensions`, activer **Mode développeur / Entwicklermodus**, puis **Charger l'extension non empaquetée / Entpackte Erweiterung laden**. Choisir le dossier **extension** de CETTE copie, après examen des permissions.
3. Cliquer sur l'icône de l'extension : la **fenêtre FruchtDrama** s'ouvre. Tout s'y passe : studio, ChatGPT, Claude, TikTok, Flow et l'ouverture des comptes. Le premier onglet (épinglé) est la passerelle : y saisir le code d'appairage affiché par VOTRE studio, choisir le rôle « Recherche, IA et Flow » et cocher « Autoriser les tâches ». Un nouveau clic sur l'icône ramène la fenêtre au premier plan ; si elle est fermée, elle se rouvre d'elle-même à la tâche suivante.
4. Vous connecter vous-même à ChatGPT, TikTok et Flow dans les profils Chrome appropriés. Claude est une option pour le scénario ; les images passent par ChatGPT. Aucun mot de passe ne doit être saisi dans le studio.
5. Plusieurs comptes Flow dans la même fenêtre : ajouter tous les comptes Google au même profil Chrome (menu du compte Google → « Ajouter un compte »). Pour chacun, ouvrir son projet Flow dans la fenêtre FruchtDrama (adresse en `/u/0/`, `/u/1/`…), puis cliquer « Mémoriser le compte Flow de cet onglet » dans l'onglet passerelle. Quand les crédits d'un compte sont épuisés, le studio passe au compte suivant dans la même fenêtre. Vérifier l'identité affichée avant de l'enregistrer. L'ancienne méthode (un profil Chrome par compte) reste possible.
6. Pour autoriser durablement les téléchargements multiples, ouvrir `chrome://settings/content/automaticDownloads` dans chaque profil et ajouter `https://flow.google.com` aux sites autorisés. Les autorisations de sécurité et les connexions restent manuelles.
7. Créer une première production courte. Choisir Deutsch, Français ou English, et un modèle disponible sur votre compte. Les réglages actuels sont 720p, vertical 9:16, 8 secondes et x1. Omni, Veo Lite, Fast et Quality sont proposés ; le modèle et le coût visibles sont vérifiés avant l'envoi.

## Utilisation et dépannage

- Le serveur, Chrome et le PC doivent rester allumés. Fermer l'onglet du studio ne coupe pas le serveur ; l'application ne fonctionne pas avec le PC éteint.
- Les nouveaux chats IA se ferment après récupération, enregistrement et accusé de réception. Les discussions restent dans l'historique du fournisseur.
- **À vérifier / Contrôle qualité** peut demander une validation humaine avant couverture et montage. Vérifier les dialogues, la cohérence et les réserves ; le logiciel ne certifie pas la synchronisation des lèvres.
- Après une interruption Flow, vérifier les résultats et journaux avant toute reprise. Ne pas renvoyer une génération déjà soumise ou incertaine.
- Les fichiers et codes locaux sont dans **data/**. Sauvegarder ce dossier pour vos besoins, sans l'envoyer à d'autres personnes.
- Si le port 8840 est occupé par une autre installation, le lanceur refuse de réutiliser celle-ci. Fermer son serveur ; ne pas appairer l'extension à une installation tierce.
- Pour arrêter le serveur, fermer le processus Python correspondant à `server.py` dans le Gestionnaire des tâches, après la fin des générations et transferts. Ne pas arrêter tous les processus Python indistinctement.
- En cas d'échec de démarrage, consulter **data/server-errors.log**. Pour un problème de dépendances, relancer **Installer.cmd**.
- Une mise à jour d'extension se recharge manuellement dans `chrome://extensions`. Une modification d'interface de Flow/ChatGPT peut nécessiter une correction des connecteurs.

## Conditions et confidentialité

Lire **CONDITIONS-UTILISATION.txt** avant installation. L'acceptation est mémorisée sur votre poste. Ce contrôle accompagne l'édition partagée ; ce n'est pas une activation distante ni une protection contre une modification du code.

Le studio travaille en local pour le montage et la transcription. Les prompts et médias sont toutefois envoyés aux services IA choisis pour leur génération et leur analyse. Le logiciel ne publie pas automatiquement vos vidéos sur TikTok.

Pour partager à votre tour une copie vierge, utiliser l'archive d'origine. Ne jamais envoyer votre dossier installé : il contiendra vos propres données.
