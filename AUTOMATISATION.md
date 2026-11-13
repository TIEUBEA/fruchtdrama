# Utilisation automatique

Pour les nouvelles productions (passerelle 0.1.34), le scénario compare cinq concepts et tient compte des épisodes précédents. Les références déjà utilisées sont évitées et les compteurs TikTok inconnus ne sont plus traités comme une preuve de popularité. Si quatre recherches ne donnent pas trois métriques identifiées et comparables, la production attend une sélection explicite. Un scénario trop proche d’un précédent peut être réécrit jusqu’à deux fois avant toute création d’image. Les anciens épisodes, scénarios et médias ne sont pas régénérés par cette mise à jour.

La version 0.1.33 ajoute l’ouverture de Flow à la demande et le passage automatique entre les comptes explicitement mémorisés.

## Configuration initiale

1. Gardez votre compte ChatGPT Pro dans sa passerelle Recherche et IA. Il reste indépendant de Google Flow.
2. Dans Connexions, ajoutez chaque compte Flow avec son adresse et son solde réellement vérifié.
3. Une fois par compte, connectez-le vous-même à Google, ouvrez un projet Flow et cliquez « Mémoriser le compte Flow de cet onglet » dans l’extension appairée autorisée pour Flow.
4. Vérifiez l’option « Ouvrir Flow et passer au compte suivant automatiquement » dans le studio. Si plusieurs profils Chrome sont utilisés, indiquez leur dossier Chrome dans la fiche correspondante.

## Pendant une production

Le serveur ouvre le navigateur appairé à la demande s’il est hors ligne. Le connecteur vérifie l’adresse Google réellement affichée, ouvre l’accueil Flow du compte, clique Nouveau projet, configure vidéo 9:16 et x1 et vérifie le coût. Le projet créé reste associé à cette production et à ce compte ; il est réutilisé pour les clips suivants. L’extension réutilise son onglet entre les comptes au lieu d’ouvrir tous les comptes en parallèle.

Les clips reçus sont conservés. Le changement de compte se fait seulement entre les clips, après récupération du résultat. Un crédit insuffisant signalé explicitement avant l’envoi permet de choisir un autre compte mémorisé. Une génération envoyée ou incertaine n’est jamais relancée sur un autre compte automatiquement. Le studio crée ensuite le montage, les sous-titres, la couverture et le MP4 final. Il ne publie pas sur TikTok.

## Ce qui peut encore demander votre intervention

La première connexion, une session Google expirée, un CAPTCHA, une extension inactive, un mauvais profil Chrome ou une nouvelle traduction non reconnue peuvent interrompre la production. Fermer un onglet ou une fenêtre n’efface normalement pas la session, mais le code ne restaure pas une session supprimée ou révoquée. Il ne saisit pas de mots de passe et ne résout pas les contrôles. Les soldes sont déclarés ; ils ne sont pas synchronisés automatiquement avec Google et ne sont jamais réinitialisés par supposition.

Le serveur et l’ordinateur doivent rester actifs. Le navigateur IA doit être disponible pour ses tâches. Chrome peut être activé par le connecteur pendant les commandes Flow. N’effacez pas un téléchargement en cours : sa présence et sa validité sont vérifiées avant import. Les voix, les dialogues et les lèvres restent à contrôler avant publication.

## Validation

Les productions antérieures ont validé la chaîne de génération et d’export, dont une vidéo de 32 secondes terminée le 31 octobre à 04:19:28 (Europe/Berlin). Les nouveaux contrôles locaux couvrent le routage, l’absence de changement pendant un clip actif, la conservation des médias, le cas d’un envoi incertain, une liste de 100 comptes simulés sans ouvrir 100 fenêtres, l’identité Google, les boutons français/allemands/anglais, la création d’un projet unique et la réutilisation de l’onglet. Une rotation réelle de bout en bout entre plusieurs comptes après fermeture complète de Chrome reste à valider sur les sessions mémorisées.
