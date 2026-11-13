# Vérification de la version 0.1

### Conversations et onglets IA regroupés — extension 0.1.35

Un onglet de travail est enregistré par fournisseur IA et réutilisé entre productions ; les URL des conversations restent distinctes par production et fournisseur. Les demandes de scénario et d’images d’un même épisode partagent sa conversation. Si l’onglet est fermé, sa conversation enregistrée peut être rouverte. Les onglets réutilisés pour une conversation personnelle ne sont pas repris automatiquement. La recherche TikTok réutilise son propre onglet.

La récupération du scénario vérifie aussi generation_task_id pour distinguer une réécriture d’une ancienne réponse du même épisode. La récupération d’image est limitée à l’intervalle après la dernière demande exacte et avant le message utilisateur suivant, en excluant pièces jointes et aperçus modaux.

Le bouton « Ranger les onglets IA du studio » vérifie les prompts des tâches terminées de cette passerelle, sauvegarde les URL puis ferme seulement les onglets surnuméraires reconnus. Les brouillons, générations en cours, scénarios suivis et conversations ambiguës ou non reconnues sont conservés. Il ne supprime pas les conversations ni les fichiers. Le bouton a été exécuté réellement après chargement de la version 0.1.35 ; aucun onglet surnuméraire reconnu n’a été fermé à cet instant. Les conversations n’ont pas été modifiées et aucune génération n’a été lancée pour cette vérification.

Les suites JavaScript passent, y compris conversation par production, réutilisation du même onglet entre épisodes, réouverture d’une conversation fermée, séparation Claude/ChatGPT, protection d’un onglet personnel, sauvegarde des liens avant fermeture, protection des brouillons et rejet d’une attribution ambiguë. Les tests média et scénario vérifient les réponses anciennes et les images d’une autre demande. Une génération réelle complète dans la conversation partagée reste à valider ; les tests ne garantissent pas les changements futurs de l’interface des fournisseurs.

### Variété et sélection éditoriale — extension 0.1.34

Seules les productions nouvellement créées reçoivent editorial_version=2. Aucun ancien projet ne reçoit cette migration et aucun média existant n’est relancé. Le nouveau parcours utilise l’historique récent, des directions variées, cinq concepts distincts avec score éditorial explicite, un titre et une première réplique correspondant au concept gagnant, une signature narrative et une vérification des reprises textuelles avant toute création d’image. Jusqu’à deux réécritures sont autorisées, puis vérification requise.

La recherche relève séparément vues, mentions J’aime et compteurs inconnus, conserve les dates absentes comme inconnues et ne déduit pas le pays de l’audience. Jusqu’à quatre requêtes sont essayées ; les références récentes déjà utilisées sont exclues de la sélection automatique. Il faut au moins trois valeurs comparables et identifiées. Un compteur inconnu ne constitue plus une preuve de popularité dans le nouveau parcours.

61 tests Python et les suites JavaScript passent. Les nouveaux contrôles couvrent le rejet d’une intrigue recyclée, la signature identique malgré une traduction, le choix du meilleur concept annoncé, l’historique sans mutation des anciens projets ou fichiers, les réécritures bornées sans génération d’images, les références répétées, les métriques hétérogènes et la lecture explicite des compteurs TikTok. Les scénarios des anciens projets gardent leur compatibilité. Une nouvelle production réelle devra encore valider le résultat créatif ; les tests ne mesurent ni la rétention ni la viralité sur TikTok.

### Suppression d’un profil Flow

Les fiches de Connexions proposent « Supprimer ce profil », avec confirmation. Le serveur refuse la suppression pendant un clip actif ou lorsqu’un envoi non remboursé n’a pas encore de résultat reçu. Les tâches non envoyées sont annulées, les productions concernées mises en pause et les associations locales retirées. Les médias et les productions terminées restent conservés ; les rôles IA et l’appairage du navigateur ne sont pas supprimés. Un profil retiré ne peut plus recevoir de tâche routée ni être repris par sa route historique.

50 tests Python passent, dont suppression avec conservation d’un fichier, tâche en attente annulée, blocage atomique pendant un clip, envoi incertain, production terminée conservée et identifiant inconnu. Le JavaScript de l’interface est valide. Le serveur a été redémarré sans tâche active. Aucun profil réel de l’utilisateur n’a été supprimé pendant la vérification.

### Trois langues de création

Le menu des nouvelles productions est limité à Deutsch (de-DE), Français (fr-FR) et English (en-US), allemand par défaut. Le serveur valide les mêmes trois valeurs et la recherche s’adapte à la sélection. Le schéma du scénario ne contient plus de réplique ou d’exemple imposant l’allemand ; les instructions demandent la langue sélectionnée pour les dialogues, les voix, la couverture et la description. Les sous-titres sont toujours construits depuis les dialogues du scénario. Les anciennes productions et leurs médias sont conservés.

46 tests Python passent, notamment la transmission des trois langues au scénario et au prompt vidéo, et le rejet d’un choix hors liste. Le JavaScript de l’interface est valide. Ce contrôle vérifie les instructions envoyées ; la qualité des voix et le respect effectif de la langue par le générateur restent à vérifier sur le résultat.

### Comptes Flow à la demande — version 0.1.33

Ouverture automatique de Chrome pour un compte mémorisé hors ligne, routage de la prochaine scène vers un compte enregistré disposant d’un solde déclaré suffisant, réutilisation de l’onglet appartenant au connecteur, et vérification de l’adresse Google affichée avant toute génération. Le compte IA et son rôle ne sont pas modifiés par le routage Flow. Le navigateur est réveillé une seule fois pour la tâche ; une passerelle absente après trois minutes provoque une pause au lieu d’une ouverture répétée de fenêtres.

La première scène d’une production sur un compte ouvre l’accueil de cette session et clique Nouveau projet / Neues Projekt / New project. L’association du projet est persistée pour les scènes suivantes, avec une préparation récupérable sans réservation supplémentaire. Les réglages vidéo, 9:16 et x1 sont automatisés, puis le coût est vérifié. Les commandes principales françaises, allemandes et anglaises sont couvertes ; une traduction inconnue ou ambiguë bloque l’envoi. Une insuffisance de crédits explicite avant envoi permet un transfert ; un envoi effectué ou incertain impose une vérification sans nouvelle génération. Une pause et les clips reçus restent conservés.

45 tests Python et les suites JavaScript passent, dont les nouveaux contrôles de routage, de liste de 100 comptes simulés sans 100 lancements, d’identité du compte, de rôles IA/Flow séparés, de désactivation de l’automatisation, de création du projet et de reprise, ainsi que la configuration FR/DE/EN. Le serveur a été redémarré sans tâche active et l’extension 0.1.33 rechargée. La mémorisation du compte Flow actuellement connecté a été validée réellement par le nouveau bouton de l’extension : identité détectée dans l’interface française, URL de session enregistrée, mode automatique activé. Aucun mot de passe ou cookie n’a été extrait ; aucun crédit de génération dépensé pour cette vérification.

Limite restante : une rotation réelle entre plusieurs comptes après fermeture complète de Chrome n’a pas encore été validée. Un seul compte est mémorisé à cet instant ; les autres doivent être connectés et mémorisés une première fois. Les soldes restent déclarés manuellement ; aucune disponibilité de 100 connexions Google ni aucun renouvellement de crédits ne sont garantis. Les nouvelles fonctions sont documentées dans AUTOMATISATION.md.

### Téléchargement Flow en français — version 0.1.32

Le bouton réel est « Télécharger le contenu multimédia », distinct de la traduction déjà prise en charge « Télécharger le média ». Le lecteur et la commande de téléchargement reconnaissent désormais les deux libellés. Le test utilise le libellé français observé et l’option 720p originale. Les suites de téléchargement et média passent.

À 04:16:54 (Europe/Berlin), le code a téléchargé et importé le troisième clip de 2e698c032e0243ca sous clip_2_0a26112165f448aa.mp4, puis préparé le quatrième. Aucune recréation ni import manuel du troisième clip : récupération du média déjà généré après correspondance du prompt.

Le quatrième clip a été pris en charge à 04:17:42, puis téléchargé et importé automatiquement à 04:19:12 sous clip_3_5038d4f445cd4329.mp4. Le montage a démarré immédiatement et l’export final s’est terminé à 04:19:28. Ce nouveau projet a donc parcouru recherche, scénario, personnages, images, quatre clips et rendu final par le code. Il a nécessité un changement de profil par l’utilisateur et les corrections de reconnaissance décrites ci-dessus : ce résultat ne constitue pas une exécution sans intervention. Aucun clip de ce nouveau projet n’a été créé, téléchargé ou importé manuellement par l’agent. Les dialogues et leur synchronisation restent à contrôler à l’écoute avant publication.

### Reprise avec un profil Flow en français — version 0.1.31

Le 31 octobre, la reprise attendait un connecteur car le projet et la passerelle étaient associés à deux profils Flow différents. La passerelle existante a été réassociée au profil choisi par l’utilisateur, sans changer les identifiants de connexion des fournisseurs. Le compte affiché dans Flow correspond au profil sélectionné.

La première tentative en français a importé la référence puis s’est arrêtée avant génération : le bouton « Déclencheur des paramètres » n’était pas reconnu. La réservation locale a été annulée. Le connecteur reconnaît maintenant ce bouton et lit la sortie x1 effectivement sélectionnée dans le menu lorsque son nombre n’est pas présent dans le bouton. Une sortie inconnue, ambiguë ou multiple bloque l’envoi. Les six contrôles français et la suite Flow passent. La version 0.1.31 a été rechargée et la reprise demandée par le studio ; À 04:08:22 (Europe/Berlin), le troisième clip a été pris en charge. Le navigateur Flow en français a ensuite affiché une génération à 9 %, confirmant que le code a passé l’import, la lecture du coût et de x1, puis envoyé la génération. Le fichier final de ce clip reste en attente à cet instant.

### Nouveau projet — version 0.1.30, 31 octobre 2026

La production 2e698c032e0243ca (« Die letzte Nachricht », quatre scènes) a récupéré son scénario, ses deux personnages, ses quatre images et ses deux premiers clips par le code. Aucun téléchargement, import ou lancement de génération manuel de l’agent pendant cette vérification. Les deux MP4 reçus sont H.264 720 × 1280 avec audio AAC, 7,93 secondes chacun. Le projet attend maintenant des crédits : les deux dernières scènes n’ont pas été générées. Au réglage actuel de 10 crédits par clip, il reste 20 crédits nécessaires, à vérifier dans Flow avant de reprendre.

Un téléchargement retardé a révélé une incohérence : le suivi attendait cinq minutes, mais l’association rejetait les fichiers commencés après deux minutes. La fenêtre d’association est désormais alignée sur les cinq minutes. Un fichier terminé et correctement associé est traité avant de déclarer le délai dépassé, même si le service worker se réveille tard. Les contrôles d’origine Flow, de type vidéo, d’ambiguïté et de protection Chrome restent appliqués. Les tests couvrent une préparation de 124 secondes, une date invalide et un téléchargement terminé au réveil du worker ; un téléchargement toujours inachevé après le délai échoue sans nouvelle génération.

### Validation réelle finale — version 0.1.29

Le 30 octobre 2026 à 22:27:59 UTC, le code a importé le dernier clip clip_2_be23032cb9ec4094.mp4, puis démarré le montage. L’export automatique s’est terminé à 22:28:13 UTC. Les commandes de création, de téléchargement et d’import de ce dernier clip n’ont pas été effectuées manuellement par l’agent. Le deuxième clip avait déjà été téléchargé et importé par le code.

Le MP4 final est lisible de bout en bout avec ffmpeg : H.264 720 × 1280, audio AAC, durée 24,022666 secondes, taille 8 780 603 octets. Contrôle visuel d’images aux secondes 2, 10 et 18 : les trois scènes se suivent et les sous-titres allemands sont présents, sans débordement observé. La couverture JPEG 720 × 1280 est générée avec le titre allemand. La présence d’audio est vérifiée ; les paroles et la synchronisation labiale restent à contrôler à l’écoute.

La sélection Flow gère une référence déjà attachée, le remplacement d’une ancienne référence, les menus différés et les contrôles masqués. Elle utilise une séquence de pointeur et vérifie le bon fichier avant confirmation. L’application active sa fenêtre Chrome pour les commandes Flow. Les contrôles locaux comprennent 34 tests Python et la suite JavaScript, notamment reprise avant envoi, conservation des originaux, association des téléchargements et absence de réenvoi après intention enregistrée.

Limite de validation : ce projet ancien comporte un premier clip importé manuellement pendant le dépannage. Un nouveau projet intégral, de la recherche au rendu final en une seule exécution, n’a pas encore été testé. Les récupérations et la fin de chaîne sont désormais validées réellement par le code, sans import manuel pour les deux derniers clips.

### Version 0.1.26 : téléchargement natif et reprise de préparation

Le deuxième clip a été téléchargé et importé réellement par la version 0.1.24, sans clic de téléchargement/import de l’agent : lancement à 21:48:34 UTC et média reçu à 21:48:42 UTC le 30 octobre 2026. Le fichier clip_1_acf68be8bad64808.mp4 contient une vidéo H.264 720 × 1280, du son AAC et dure 7,93 secondes. L’image à six secondes montre bien la révélation de la miniature d’appartement.

La permission Chrome downloads permet de suivre uniquement le téléchargement récent associé au prompt Flow vérifié, puis de choisir le 720p original. Le serveur restreint l’import au dossier Téléchargements, vérifie le fichier avec ffprobe et rend l’import idempotent. Les alertes Chrome et correspondances ambiguës ne sont pas contournées.

L’éditeur est désormais vérifié même lorsque Chrome indique complete. L’intention d’envoi est persistée avant le clic de génération. Une préparation perdue peut être reconnectée jusqu’à trois fois sous la même réservation ; les envois incertains ne sont pas répétés. La tentative suivante avait échoué sur un faux positif du mot reCAPTCHA dans les mentions de confidentialité du menu Google : le détecteur distingue maintenant ce pied de page des widgets visibles et des demandes explicites de vérification. Le menu de compte est fermé sans action de déconnexion avant la préparation.

34 tests Python et la suite JavaScript passent, avec contrôles d’origine et association des téléchargements, chemin local, MP4 vertical avec audio, idempotence, reprise réseau, référence exacte, préparation et détection de véritable contrôle. Le troisième clip et le montage final sont encore en cours de validation réelle.

### Mises à jour 0.1.24 et 0.1.25

Le connecteur choisit automatiquement « Medien herunterladen », puis « 720p Originalgröße », après correspondance exacte du prompt. La permission Chrome downloads suit le fichier réellement enregistré. Son association exige une origine Flow, une fenêtre temporelle et un type vidéo ; les correspondances multiples et alertes de sécurité sont rejetées. Le serveur accepte uniquement un MP4/WebM récent sous Téléchargements, limité à 100 Mo, vertical, avec audio et durée de 4 à 12 secondes. Il le copie dans le projet sans supprimer l’original. L’import est idempotent par identifiant de téléchargement.

Validation réelle sans téléchargement/import manuel : le 30 octobre 2026 à 21:48:34 UTC, le code a lancé le téléchargement du deuxième clip et l’a importé à 21:48:42 UTC sous clip_1_acf68be8bad64808.mp4. ffprobe : H.264 720 × 1280, audio AAC, 7,93 secondes. Une image à six secondes confirme la scène de la miniature d’appartement.

La préparation vérifie désormais l’éditeur et l’URL réelle même lorsque Chrome annonce complete. Un point de reprise est persisté avant tout envoi ; une préparation perdue peut être reconnectée jusqu’à trois fois sous la même réservation. Un envoi incertain n’est pas répété. Le solde local a été réconcilié avec les 30 crédits réellement affichés dans Flow après les anciennes réservations de dépannage.

34 tests Python passent, ainsi que la suite JavaScript : association et import des téléchargements, choix du 720p original sans achat, reprise réseau, sécurité du chemin local, vérification vidéo, sélection de la référence exacte et point de reprise avant envoi. La validation réelle du troisième clip et du montage automatique est encore en cours.

### Mise à jour 0.1.23

La récupération en lecture seule peut rattacher un clip Flow déjà généré à une tâche échouée, avec vérification du navigateur propriétaire, du profil, de l’emplacement manquant et de la correspondance exacte du prompt sur la page d’aperçu. Elle ne crée aucune nouvelle réservation de crédits. Les pauses sont respectées. La lecture des médias HTTPS ou blob renvoie directement leurs octets plutôt que de transmettre une URL susceptible d’être rejetée par le téléchargement du worker. Les types génériques sont acceptés uniquement après vérification de signature MP4/WebM.

Le navigateur revient au projet avant une nouvelle génération s’il se trouve dans la page d’édition d’un ancien clip. Les sondes de préparation vérifient l’URL du document pour éviter de confondre l’ancien éditeur avec la page en cours de navigation. 31 tests Python réussissent, ainsi que la suite JavaScript. La deuxième vidéo réelle a terminé sa génération ; les dialogues de son aperçu correspondent à la scène du cadeau d’anniversaire. Récupération automatique à valider après chargement de la version.

### Mise à jour 0.1.22

Premier clip réellement téléchargé depuis Flow en 720p original et importé dans le studio sous clip_0_aff4cb5141834cb8.mp4. ffprobe confirme H.264 720 × 1280, audio AAC, durée 7,93 secondes. Le second clip a d’abord été refusé parce que l’ancien lecteur de l’onglet restait « running » : la transition peut désormais recharger l’onglet si la tâche précédente est confirmée terminée, ou échouée avant envoi. Les envois incertains restent bloqués sans nouveau prompt. Quatre tests de transition passent.

Le lecteur vidéo peut récupérer un MP4/WebM affiché par une adresse blob, dans les limites d’accès du navigateur. Le worker peut récupérer en lecture seule un aperçu Flow dont le texte correspond exactement au prompt de la tâche et dont l’URL est une page edit du projet. Une nouvelle vignette explicitement identifiée comme vidéo générée peut ouvrir automatiquement l’aperçu ; les anciennes vignettes et les correspondances multiples sont ignorées. Tests de lecture blob, correspondance du prompt, sélection d’aperçu et syntaxe réussis. La récupération automatique des clips suivants reste à valider après chargement de cette version.

### Mise à jour 0.1.21

Le choix du bouton d’envoi Flow est limité au bouton de génération du compositeur, identifié par l’icône d’envoi ou le libellé exact « Generierung starten ». Le repli générique qui pouvait accepter « Sammlung erstellen » ou « Tool erstellen » est supprimé pour Flow. Tests du choix exact et rejet des autres actions réussis. Cette protection complémentaire n’a pas été rechargée pendant la tâche vidéo active afin de préserver son suivi.

### Mise à jour 0.1.20

Validation réelle : version 0.1.20 chargée dans Chrome, production relancée une seule fois ; référence sélectionnée et import dépassé. Un premier clip avec bouton de lecture est ensuite apparu dans Flow. Son téléchargement et la suite de l’épisode restent à vérifier.

Le connecteur peut sélectionner dans le sélecteur Flow le fichier déjà présent dont le nom correspond exactement à la référence de la tâche, puis confirmer son ajout sans nouveau téléversement. Les fichiers en cours d’import, les noms différents et les correspondances multiples sont rejetés. Après le clic sur Start, le sélecteur est attendu jusqu’à vingt secondes, sans clic répété. Les icônes textuelles drive_folder_upload/upload sont reconnues devant le libellé d’import. Cinq tests de réutilisation et les tests d’import, confirmation et cycle de vie passent ; syntaxe vérifiée. Ce changement demande un rechargement de l’extension. Le parcours réel après cette version reste à valider.

### Mise à jour 0.1.19

Test réel dans Chrome, projet Flow 81b7abf0-cbdc-4cc6-99b0-aa7a26e44900 : le PNG original de 2 270 500 octets reste initialement en téléversement lors d’un import natif, puis finit par charger. Une copie JPEG RGB de 198 108 octets, limitée à 1280 pixels de côté, termine son import et son aperçu apparaît avec « Zum Prompt hinzufügen » actif. Les erreurs ERR_BLOCKED_BY_CLIENT observées concernent play.google.com/log ; elles ne suffisent pas à attribuer le blocage de l’import aux bloqueurs.

Les tâches Flow utilisent désormais une copie JPEG légère mise en cache par empreinte du fichier. Les PNG originaux ne sont pas modifiés. L’attente de confirmation passe à cinq minutes maximum, avec progression transmise au journal du studio via une route authentifiée et associée au propriétaire de la tâche. Tests de conversion, conservation des originaux, limite de dimensions et progression réussis : 29 tests Python ; suite JavaScript et syntaxe vérifiées. La génération vidéo et son téléchargement ne font pas partie de ce test d’import.

### Mise à jour 0.1.18

L’attente du navigateur accepte une zone de saisie visible sur le domaine attendu lorsque document.readyState est interactive ou complete, même si chrome.tabs indique encore loading. La lecture ne remplit ni n’envoie de prompt. Le délai maximal passe de 30 à 90 secondes ; une page appartenant à un autre domaine n’est jamais inspectée ou utilisée. Quatre contrôles dédiés et les six scénarios du worker passent ; syntaxe vérifiée. L’échec réel de image:1 à 15:54:42 UTC a eu lieu avant l’injection et avant tout envoi de prompt.

### Mise à jour 0.1.17

Validation réelle : version 0.1.17 chargée dans Chrome. Le studio a reçu image_0_b3efe5d1781a40c6.png à 15:53:42 UTC le 30 octobre 2026 et a préparé image:1. Inspection visuelle du fichier : fraise et mangue devant le placard, conforme à la première scène, distinct des références personnages. Aucun nouveau prompt de première scène envoyé pendant la récupération. Le lecteur de média est réenregistré lors de son injection pour remplacer un écouteur dont le contexte d’extension a expiré.

Le collecteur reconnaît les cartes explicitement nommées « Generiertes Bild 1 » / « Generated image » lorsque l’image est hors du bloc de texte assistant. Les cartes de pièces jointes restent rejetées. Le worker peut actualiser le lecteur et récupérer une image existante pendant une tâche chat_image sans renvoyer de prompt ; une tâche image déjà échouée est libérée pour la récupération dédiée. Tests média et six scénarios du worker réussis, syntaxe vérifiée. Validation réelle après chargement de la version dans Chrome.

### Mise à jour 0.1.15

Diagnostic local : les cinq fichiers PNG de la production s’ouvrent et passent Pillow.verify. Le serveur renvoie bien image/png et les octets PNG attendus. Les trois fichiers de scène ont le même SHA-256 et montrent la référence mangue ; ce sont des médias incorrects pour les scènes. Le collecteur exige désormais une image dans un message assistant et rejette les pièces jointes utilisateur ainsi que les aperçus sans message assistant. Tests de cette sélection réussis.

L’import déclenche désormais un seul événement change après affectation de FileList, au lieu de input puis change. Le temps d’attente de confirmation passe de 30 à 90 secondes ; le message distingue un bouton désactivé d’un bouton absent. Un bouton de confirmation désactivé reste considéré présent pendant l’attente de fermeture. Tests Flow, média, cycle de vie et syntaxe réussis. Le double événement est une cause possible du blocage, pas une cause confirmée. Un import manuel du même fichier dans Flow reste nécessaire pour distinguer un problème du connecteur d’un traitement bloqué côté Flow. Aucune correction rétroactive des trois scènes ni génération externe effectuée pendant ce diagnostic.

### Mise à jour 0.1.14

Le signal result-ready protège désormais les exceptions synchrones et les rejets asynchrones de chrome.runtime.sendMessage. Une notification échouée ne transforme plus un résultat terminé en échec. Le lecteur et les contrôles avant envoi détectent un contexte d’extension invalidé. Trois tests de cycle de vie et cinq scénarios du worker passent ; syntaxe vérifiée. Après rechargement de l’extension, les onglets précédemment pilotés doivent être actualisés : le correctif ne peut modifier les anciens scripts déjà injectés.

### Mise à jour 0.1.13

Lorsque Start est remplacé par une miniature, le connecteur peut rechercher l’unique bouton contenant une image directement à gauche de Ende. Les candidats désactivés, éloignés ou ambigus sont rejetés. Quatre tests de miniature passent, ainsi que les contrôles Flow existants. Les erreurs d’import incluent désormais les libellés des boutons visibles même si le sélecteur ne possède pas le rôle dialog. Cette reconnaissance géométrique reste à valider dans le DOM réel de Flow.

### Mise à jour 0.1.12

Reconnaissance complémentaire du bouton Flow portant une icône textuelle arrow_forward, arrow_upward ou send. Elle exige le domaine Flow, un bouton actif près du champ de saisie et un candidat unique. Cinq tests simulés passent, ainsi que les contrôles de coût, d’import, de confirmation et du composeur. Syntaxe du runner vérifiée. La capture ne permet pas de vérifier le DOM réel du bouton ni de confirmer que cette reconnaissance résout le blocage sur le compte.

### Mise à jour 0.1.11

Après le téléversement dans Flow, le connecteur attend le bouton « Zum Prompt hinzufügen », clique une seule fois et attend sa disparition avant de remplir le prompt et de vérifier le coût. En cas de confirmation absente ou persistante, il s’arrête avant toute génération. Quatre scénarios de confirmation simulés réussissent, ainsi que les neuf contrôles de réglages et sept parcours d’import existants ; syntaxe du runner vérifiée. Le parcours complet réel reste à valider sur le compte.

### Mise à jour 0.1.10

Le bouton observé sur la capture allemande « Medien hoch… » est reconnu, ainsi que son libellé complet, une icône textuelle avant le libellé et un aria-label différent du texte visible. Un sélecteur déjà ouvert est utilisé directement sans recliquer sur Start. Neuf contrôles de réglages et sept parcours d’import simulés passent. L’import réel, sa confirmation éventuelle après téléversement et la récupération du clip restent à valider dans Flow.

Contrôles réalisés localement le 30 octobre 2026 :

- 16 tests Python réussis : références et classement, compteurs non confondus avec les vues, validation des scénarios, locuteurs, langue transmise au scénario et aux clips, pause d'une tâche en cours, file idempotente, sauvegarde, changement manuel de profil sans perte de clip, origine des requêtes, appairage et réservation des crédits sans double débit.
- Vérification de syntaxe des scripts JavaScript de l'interface et de l'extension.
- Interface ouverte dans le navigateur : tableau de bord, formulaire de création, projet de six scènes en attente de recherche, champ multilingue.
- Export réel sur trois clips synthétiques de test : MP4 720 × 1280, piste audio, durée 24,02 secondes, sous-titres et couverture générés. Ce test n'est pas un épisode animé par IA et n'a consommé aucun crédit externe.

Non vérifié : installation de l'extension dans le navigateur personnel, session ChatGPT, session Claude, extraction réelle TikTok par l'extension, génération d'images, import d'images dans Flow, coût visible Flow et récupération d'un clip généré dans Flow. Ces connecteurs sont expérimentaux et doivent être testés sur les comptes de l'utilisateur avant de considérer le processus comme entièrement automatique.

Les soldes de profils Flow sont déclarés manuellement. L'identité Google du navigateur doit être vérifiée par l'utilisateur. Les sous-titres sont alignés approximativement à partir du texte ; aucune transcription ni vérification des lèvres n'est implémentée dans cette version.

### Mise à jour 0.1.5

22 tests Python passent, y compris réception idempotente et respect de la pause. Tests JavaScript : six vérifications d'éditeur, neuf de JSON, dix de politique de récupération et cinq scénarios simulés du worker (fin de réponse, perte de canal, panne réseau, onglet incorrect, redémarrage serveur). Ces tests utilisent des fixtures et ne remplacent pas la validation sur les sites réels.

### Mise à jour 0.1.9

24 tests Python réussis, dont annulation unique de réservation locale avant envoi et conservation en cas d’envoi incertain. Neuf contrôles de coût/réglages Flow et trois parcours simulés d’import réussis : champ existant, Start, Start puis Hochladen. Cinq scénarios du worker réussis ; syntaxe du runner vérifiée. Aucun crédit externe consommé par ces tests. Le sélecteur réel après Start et le téléchargement du clip Flow restent à valider.


## 0.1.37 — retour aux conversations indépendantes
Suppression de la réutilisation des conversations et du correctif de reprise avant envoi de 0.1.36. Une nouvelle conversation par tâche. Tests du cycle : fermeture après ACK serveur, pas de fermeture sur transfert échoué ou résultat refusé, file persistante et réessai de fermeture avant la tâche suivante, conservation des onglets réaffectés et brouillons. Les médias existants ne sont pas modifiés. Validation de production réelle à effectuer après rechargement.


## Correction du lecteur de scénario — 31 octobre 2026
Le rendu ChatGPT ne fournissait pas les enveloppes habituelles et le texte affiché ne permettait pas de parser le JSON. Lecture de secours via textContent, analyse indépendante des débuts d’objets pour tolérer un exemple de prompt mal formé, et sonde de récupération liée aux identifiants exacts. Deux observations identiques avant transfert. Réponse réelle cca129fa51224461 récupérée sans nouveau prompt : six scènes validées, étape personnages atteinte à 15:42 Europe/Berlin, tâche character:fruit_a prise en charge. Comportement un nouveau chat par tâche et fermeture après ACK conservé. Tests response, worker et chat_session réussis.


## Correction du lecteur d’images — 31 octobre 2026
Adaptation aux pages ChatGPT sans enveloppes de tours utilisateur : recherche d’un bloc contenant exactement la demande, lecture textContent en plus de innerText, image générée explicitement identifiée et située après ce bloc. Tests : rendu altéré, bloc absent et image antérieure refusés. Récupération réelle de character:fruit_a confirmée à 15:48 Europe/Berlin (character_fruit_a_f09c939103a04f46.png), sans régénération ; tâche character:fruit_b préparée.


## Import des références ChatGPT — 31 octobre 2026
Erreur de la première scène avant envoi : aucun input file au chargement. Ajout de Composer.openImport : ouvre le menu de pièces jointes FR/DE/EN, attend son input, peut activer l’entrée upload en empêchant l’ouverture du sélecteur natif, puis utilise DataTransfer existant. Tests de champ initial, champ créé par menu, champ créé par upload et échec sans envoi réussis. Toutes les suites JavaScript passent. Reprise de cca129fa51224461 à image:0 avec les trois personnages existants.

Validation réelle de la reprise image:0 : les trois fichiers ont été joints par le runner, le compositeur a été vidé après envoi et le bouton Stoppen est visible pendant la génération. Aucune soumission manuelle. Délai d’attente du bouton d’envoi porté à 180 secondes pour les futures tâches avec pièces jointes.


## Erreur réseau ChatGPT locale — surveillance 31 octobre 2026
Une alerte Network error a interrompu image:0 dans une URL locale local-chatgpt. Ajout d’une reprise unique du même envoi via le bouton du fournisseur, uniquement pour une conversation locale, demande exacte associée, alerte réseau explicite, aucune image déjà générée et aucune génération active. Intention de reprise persistée avant clic. Les conversations serveur restent exclues car leur résultat serait incertain. Tests média et worker réussis.

La reprise locale du fournisseur a ramené la demande dans le compositeur sans conversation serveur. Aucun résultat présent. Une nouvelle reprise de la première scène a été planifiée à 16:01 Europe/Berlin, en conservant les personnages. Ajout de conservation du suivi après navigation pour les demandes d’images déjà soumises (lecture seule, sans nouvel envoi, maximum 15 minutes). Ce dernier garde-fou nécessite le prochain rechargement du worker pour être actif. Éviter des reprises illimitées si la même panne réseau revient.


## Passage à Flow — surveillance du 31 octobre 2026
Les six images sont enregistrées. Nouveau projet Flow initialement en mode agent, sans Start. Correction : désactivation du mode agent s’il est actif puis configuration vidéo/9:16/x1/Frames avant import, prise en charge du libellé allemand Zu den Einstellungen. Avis de droits du premier import accepté par l’adaptateur uniquement pour le dialogue spécifique des images originales. L’image est maintenant attachée au frame de début. Le premier collecteur ancien attend encore son délai de confirmation (démarré 15:27 UTC, limite cinq minutes) : après son éventuel échec avant envoi, reprendre la même scène avec l’image existante. Nouvelle reconnaissance du groupe de galerie par nom exact + source identique au frame pour éviter de réimporter. Aucun clip n’a encore été envoyé à Flow à 15:30 UTC. Les réservations des échecs avant envoi ont été annulées.

Validation réelle après reprise du collecteur : premier clip Flow généré, aperçu vertical de huit secondes ouvert automatiquement par le runner à 15:33 UTC, modèle Veo 3.1 Lite. Aucun clic manuel de génération ou import. Téléchargement encore à confirmer par le studio.


Surveillance 18:33 UTC : quatre clips enregistrés. La route kenneanaelle /u/2/ redirige vers /u/0/ connecté à Euloge ; aucune génération sur cette identité différente. Reprise ciblée avec le profil déjà enregistré borismoussa53 (619d789303c1402b). Nouveau projet 14774a5a-5cd7-4cca-ba97-14b36cdcfce2 créé et identité confirmée. Premier import sur ce compte auto-attache le frame après consentement ; ancien collecteur encore en attente jusqu’à environ 18:38 UTC. Après échec avant envoi, reprendre clip:4 avec le frame existant, sans régénérer les quatre clips acquis. Élargissement de referenceKey aux éléments aria-label/title au nom exact du fichier. Tests Flow réussis.

19:44 Europe/Berlin : extension de borismoussa53 actualisée de 0.1.33 à 0.1.37, lecteur réinitialisé, reprise effectuée par le connecteur. Cinquième clip téléchargé et enregistré à 18:44 UTC ; sixième pris en charge à 18:44:51 UTC.


## Téléchargements couverture et description
Liens avec download=1 et en-tête Content-Disposition attachment. Description servie en UTF-8. Ajout de Copier la description avec sélection du texte comme secours, aperçu de couverture et zone de description. Requêtes HTTP réelles : 200, fichiers de 304393 et 437 octets, types JPEG et texte UTF-8, noms de téléchargement confirmés. Aucun média existant modifié. Couverture alternative cover-proposal-v2.png créée avec image_gen, séparée de la couverture actuelle.


## Modèle de couverture approuvé
Nouvelles productions : cover_style dramatic_v2, étape Couverture après les clips puis montage. Référence scène + modèle approuvé séparé pour le style. Texte demandé dans la langue configurée, 3–5 mots, gros plans et contraste blanc/jaune. Conservation du fichier généré au montage ; rejet de copie exacte du modèle ou des scènes. Import et récupération des tâches cover pris en charge. 64 tests Python réussis, dont tâche unique, conservation des clips et compatibilité des anciens projets. Pas de génération complète de production supplémentaire pour ce contrôle.


## Finalisation de la synchronisation au repos
Cause du cas borismoussa5 : l’ancienne condition attendait une production waiting_credit. Cette condition a été retirée pour les comptes épuisés et les comptes déjà synchronisés dont la prochaine vérification est échue. Le solde reste inchangé tant que Flow ne l’a pas confirmé. 74 tests Python réussis, dont solde nul au repos et nouvelle lecture à échéance même sans production. Activation par redémarrage du serveur sans tâches de production actives. Rechargement des extensions laissé à l’utilisateur.

Validation réelle finale : euloge.moussa est passé de 0 à 50 par lecture Flow, puis borismoussa5 de 0 à 50, credit_source=flow, aucune erreur et heure quotidienne française 10:59 mémorisée. Correction complémentaire du parseur pour les espaces insécables dans « crédits Google Flow ». Le lecteur ne dépend plus de temporisations dans l’onglet en arrière-plan : il renvoie pending immédiatement et le worker refait la lecture. Tests JavaScript dédiés réussis. Aucune extension rechargée par l’agent pendant cette finalisation.


## 0.1.39 — recherche TikTok après navigation
Nouvelle production 0cb382b67f9244c7 : suivi du lecteur perdu après navigation TikTok. Reprise bornée de la lecture sur le même onglet et la même tâche, sans prompt ni média. Après rechargement manuel de l’extension, reprise automatique des recherches attention dont la dernière tâche de cette passerelle a échoué uniquement pour Suivi interrompu. Endpoint authentifié, propriétaire validé, trois reprises maximum, file idempotente. 75 tests Python et toutes les suites JavaScript passent. Surveillance toutes les trois minutes créée pour cette nouvelle production ; ne pas recharger les extensions à la place de l’utilisateur.

Surveillance 20:04 UTC, production 0cb382b67f9244c7 : ChatGPT avait terminé le scénario mais sa réponse était hors du premier élément main. Extension du lecteur à body.innerText puis textContent, uniquement avec correspondance stricte des deux identifiants de production et de tâche. Test de disposition scindée et rejet d’un autre identifiant réussis. Réponse réelle récupérée et scénario six scènes validé à 20:07:10 UTC ; création du premier personnage lancée. Aucune nouvelle génération de scénario, aucun rechargement d’extension.

Validation complète du parcours automatique 0cb382b67f9244c7 : six scènes et six clips reçus ; couverture dramatique originale cover_d3d97166e3e644d1.png créée et reçue automatiquement à 20:44:25 UTC, 941×1672. Montage terminé 20:44:55 UTC. Vérification technique finale : H264 720×1280, audio AAC, 48.022666 secondes, 19 845 539 octets ; description présente. Couverture inspectée : personnages cohérents, gros plans expressifs et accroche allemande blanc/jaune. Pas de validation complète du son ou de la synchronisation labiale. Surveillance supprimée à la fin.


## Rétention des prochaines productions — 2026-10-31
- Nouvelle production uniquement : `retention_version=1`, sans migration des projets existants.
- Prompts : première réplique <=8 mots, gros plan initial cohérent entre image et animation, action dès la première seconde, progression sans répétition et conclusion complète. Deux répliques / 20 mots maximum par scène, validation avant les images et réécriture bornée existante.
- Sous-titres : 48 px au lieu de 38, groupes de quatre mots / 30 caractères, mot long conservé entier ; anciens projets conservent leur rendu. Timing toujours estimé depuis le scénario, pas aligné automatiquement sur l'audio.
- 32 secondes proposé comme test, durée sélectionnable conservée. Aucune promesse de vues.
- Validation : 79 tests Python réussis ; syntaxe JS app.js valide.
- Déploiement : fichiers mis à jour, serveur non redémarré car production 29d168516e094d00 en cours. Redémarrer le serveur après la fin de la production pour activer les nouvelles règles. Aucun rechargement d'extension requis.


## Affiches familiales v3 — 2026-10-31
Nouveaux projets : family_poster_v3, titre doré à empattements en haut, expressions fortes et objet du mystère. Capture utilisateur jointe comme référence de style uniquement ; aucune reproduction de grille, interface, personnages ou titres. Ancien style et médias conservés. 80 tests Python réussis. Activation après redémarrage du serveur ; ne pas interrompre une tâche en cours. Extension inchangée.


## Contrôle qualité v1 — extension 0.1.40
- Étape quality uniquement pour les nouvelles productions, après clips et avant couverture. Préserve résultats et anciens projets.
- ffprobe : durée, format vertical, audio présent, durée audio et décalage des débuts ; décodage et silence via ffmpeg.
- Faster Whisper 1.2.1 local CPU int8, modèle base téléchargé ; PyAV 16.1.0 épinglé après incompatibilité constatée avec av 19 (`metadata_errors`). Installations --target isolées, aucun paquet global remplacé.
- Test réel sur copie du premier clip de 0cb382b67f9244c7 : transcription allemande correspondant au texte attendu (ratio 1.0), horodatages des mots et rapport pass local. Aucun média existant modifié.
- Revue ChatGPT via chat_text/quality_review, lecteurs JSON liés au job et à la tâche, vrais photogrammes de clips et références personnages. Revue de cohérence uniquement, pas de fausse validation audio ou lèvres depuis des images. Essai navigateur de bout en bout encore à effectuer après activation.
- Rapports mis en attente si défaut technique, dialogue incertain ou incohérence visuelle ; accord explicite possible uniquement sur les réserves non techniques. Pas de régénération Flow automatique. Empreinte des médias/scénario empêche l'utilisation d'un ancien rapport après remplacement.
- Sous-titres ancrés aux mots reconnus avec interpolation des mots manquants lorsque couverture >=80%, sinon timing estimé.
- Tests : 88 Python et les 19 suites JS réussis.
- Serveur non redémarré, production active 01f38543818e4929 au scénario lors du dernier contrôle. Extension non rechargée, conformément à la demande utilisateur.

Validation finale : 90 tests Python réussis, 19 suites JS réussies. Montage réel sur copie de test : export 8 s H264/AAC, 1/1 scène avec sous-titres calés sur reconnaissance vocale. Revue navigateur IA encore non testée en conditions réelles ; activation différée tant que la production active continue.


## Accroches émotionnelles pour les prochaines productions — 2026-11-01
- Nouveaux projets uniquement : hook_version=1. Directions familiales variées, brief utilisateur prioritaire, accroches sous forme de découverte/reproche/interdiction/question sans formule répétée.
- Objectif 6–10 mots, plafond 12, langue native ; ancienne limite 8 conservée pour les anciens projets retention_version=1 sans nouveau marqueur.
- opening_plan obligatoire : objet/geste explicitement présent dans les prompts image et animation initiaux, question et résolution prévue dans une scène existante. Validation structurelle, sans prétendre prouver la pertinence sémantique du récit.
- 93 tests Python réussis. Serveur redémarré après vérification : aucune tâche queued/claimed ni production running/rendering. HTTP 200 vérifié. Extension non rechargée par l’agent ; version 0.1.40 requise pour la revue qualité ajoutée précédemment.


## Omni Flash — 2026-11-01, extension 0.1.41
- Nouveaux projets : Gemini Omni Flash 720p, 8 s, x1, 12 crédits. Sélecteur de modèle dans le formulaire ; choix Lite conservé. Profils, soldes et anciens projets non migrés.
- Payload vidéo inclut modèle/résolution. Sélection explicite indépendante du coût, aucun repli silencieux vers Lite/Fast, vérification de résolution/durée/portrait avant envoi, x1 et prix réel conservés. Interface absente ou ambiguë => arrêt sans génération.
- Tests : 95 Python et 20 suites JS réussis, dont sélection Omni FR/DE/EN, passage 360p/10 s vers 720p/8 s, modèle absent/ambigu, absence de resélection, ancien projet conservé et solde 11 insuffisant. Aucun crédit dépensé pour un test. Sélecteur réel Flow à valider au premier essai après rechargement manuel de l’extension.
- Serveur redémarré hors production active ; HTTP 200 et defaults Omni/12 vérifiés. Extension non rechargée par l’agent.


## Import Flow français / Omni — extension 0.1.42, 2026-11-01
Diagnostic réel sur projet Flow de la production 3974d92f61f249c0 : mode Ingrédients sélectionné, le mode Frames s’appelle Images dans l’interface française. Choisir Images fait apparaître Début / Fin. Bouton de téléversement observé : Importer l’élément multimédia. Aucun fichier ni prompt soumis manuellement pendant le diagnostic.
Correctif : reconnaissance Images (pas Image, qui crée des images), confirmation aria-checked obligatoire, Agent reconnu seulement si activé, import français avec apostrophes droites/courbes, résumé compact 8 sx1 correctement interprété. Adaptateur modifié, aucun rechargement d’extension par l’agent. Tests unitaires supplémentaires sur les libellés observés ; 95 tests Python locaux et 20 suites JS réussis.
Production reprise via API après preuve que la réservation précédente a été annulée avant soumission ; résultats existants conservés. Vérification de progression réelle à effectuer avant de déclarer le blocage résolu.

Validation réelle du correctif français : reprise par le code depuis Ingrédients (état de diagnostic restauré), image importée et clip 0 généré puis téléchargé automatiquement à 09:20:26 UTC ; clip 1 pris en charge ensuite. Aucun rechargement d’extension, aucun import ou prompt manuel. Fichier reçu contrôlé par ffprobe. La production reste en cours, pas déclarée terminée.


2026-11-01 — Extension 0.1.43: choix Omni Flash / Veo 3.1 Lite / Fast / Quality, 720p, 8 s, vertical x1. Coûts standard 12/10/20/100 ; Ultra Lite 5 et Fast 10 acceptés sans déduction automatique de l’abonnement. Vérification du modèle avant envoi ; aucun repli silencieux. 96 tests Python et toutes les suites JavaScript locaux réussis. Tests DOM/API isolés, pas de génération payante de validation. Productions existantes inchangées. Autorisation Chrome de téléchargements multiples à régler manuellement par site/profil ; aucune modification des permissions Chrome. Modes 360p, priorité réduite et upscale exclus de cette version du pipeline 720p.
