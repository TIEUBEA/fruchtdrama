# Mise à jour locale — 6 novembre 2026

Version installée : FruchtDrama 0.1.96, extension 0.1.96.
Source : TIEUBEA/fruchtdrama, branche build/0.1.96-sur-dev, commit 93c6651 (même contenu que build/0.1.96).

L’installation d’origine a été actualisée sans désinstaller l’extension. La clé, les permissions et les domaines de l’extension sont identiques. Les comptes, sessions Chrome, profils, appairage, productions et médias sont conservés. Le dépôt de travail modifié fruchtdrama-github n’a pas été écrasé.

Lancer-Studio.cmd utilise désormais le Python privé .venv/Scripts/python.exe et le lanceur local existant launcher.pyw. Python 3.13.9 est conservé ; pip et Pillow sont actualisés dans cet environnement, sans modifier Anaconda. Les bibliothèques et modèles de transcription existants sont conservés et leur import a été vérifié.

Correctifs locaux supplémentaires : test de chemins compatible Windows ; scènes volontairement silencieuses acceptées par la comparaison de dialogues ; exclusion explicite des captures source dans la feuille de personnages ; montage arrêté proprement si l’épisode n’existe plus ; tests de distribution isolés des références privées et des installations sans dépôt Git.

Voir MISE-A-JOUR-0.1.96.json pour les vérifications, la liste des fichiers et la sauvegarde privée. Aucun achat ni nouvelle génération n’a été demandé pour cette mise à jour. Le redémarrage a attendu la fin des tâches actives.

Vérification finale : 497 tests Python réussis (10 ignorés selon environnement), 36 suites JavaScript sans échec ; les suites exigeant un navigateur de test disponible sont ignorées. HTTP 200 et version serveur/extension 0.1.96 vérifiés. Dernier redémarrage pour les correctifs locaux supplémentaires refusé par le contrôle automatique sans motif détaillé : service actuel maintenu, correctifs actifs au prochain démarrage.
