# FruchtDrama Local

Studio Windows local pour produire des histoires originales en allemand, français ou anglais : scénario, images, clips Flow, contrôle qualité, couverture et montage.

Cette version commence avec un espace vide. Chaque utilisateur connecte ses propres comptes. Aucun compte, session, cookie, crédit, production ou identifiant du fournisseur de cette copie n'est livré.

## Mode d'emploi

Guide détaillé, pas à pas, de l'installation à la vidéo finale : **docs/MODE-EMPLOI.md** (mis à jour à chaque version).

## Installation

Lire **INSTALLATION.md**, puis **CONDITIONS-UTILISATION.txt**. Installer Python 3.11 ou 3.12 64 bits, Chrome et FFmpeg/ffprobe. Extraire ou cloner le dépôt, lancer **Installer.cmd**, puis **Lancer-Studio.cmd**.

Le studio fonctionne sur http://127.0.0.1:8840. Les dépendances et le modèle vocal sont téléchargés à l'installation. Les générations utilisent les quotas ou crédits des comptes connectés ; aucun abonnement n'est fourni.

## Confidentialité

Le dossier `data/`, les environnements Python, les modèles vocaux et les médias de production sont exclus de Git. Ne jamais ajouter des cookies, profils Chrome, clés, mots de passe ou exports de sessions au dépôt. Ne pas exposer le serveur local sur Internet.

Le montage et la transcription se font en local. La création par les services tiers leur transmet les prompts et médias nécessaires. Les conditions de ces services restent applicables.

## Vérifications

Depuis la racine du dépôt :

```text
python -m unittest discover -s tests -p "test_*.py"
```

Les suites JavaScript dans `tests/*.cjs` utilisent Node.js pour les tests ; Node.js n'est pas requis pour utiliser le studio. Les tests ne soumettent pas de génération payante.

Les connecteurs sont expérimentaux. Une connexion, un CAPTCHA, une autorisation Chrome ou une réserve du contrôle qualité peut demander une intervention. Aucun résultat viral ou revenu n'est garanti.

## GitHub

Cette copie peut être versionnée indépendamment de toute installation personnelle. Les conditions d'utilisation se trouvent dans **CONDITIONS-UTILISATION.txt** ; aucune licence open source standard n'est revendiquée.
