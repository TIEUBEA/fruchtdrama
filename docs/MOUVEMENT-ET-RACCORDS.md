# Mouvement des personnages et raccords

Correction locale du 3 novembre 2026, après la version 0.1.62.

Le scénario décrit désormais une action physique avec position initiale, déplacement ou manipulation et position finale. Les cadrages et changements de lieu suivent l'action, au lieu d'imposer un nouveau cadrage et deux lieux à chaque épisode. Les images doivent laisser de l'espace pour le geste. Le prompt envoyé à Flow et aux autres moteurs rappelle l'action de la scène et le contexte des scènes voisines, la direction des regards et la continuité des objets. Un travelling seul ne remplace pas un déplacement du personnage.

Les nouveaux montages utilisent un fondu visuel de 0,2 seconde à chaque raccord. La dernière image sortante est prolongée uniquement pendant le début du plan suivant : aucune syllabe n'est coupée ou superposée, la durée totale et les repères des sous-titres restent inchangés. L'audio conserve ses coupes originales. Le paramètre technique `smooth_transitions=false` permet de conserver les coupes franches. Ces fondus atténuent un raccord ; ils ne réparent pas un décor ou une pose incompatibles.

Les productions déjà exportées ne sont pas modifiées. Les prompts des tâches déjà préparées ne sont pas réécrits. Pour appliquer la nouvelle direction à une scène existante, il faut demander explicitement sa régénération ; cela peut consommer des crédits. Aucun rendu fournisseur n'est lancé par cette correction. La génération vidéo reste probabiliste : le déplacement et la continuité devront être vérifiés sur les prochains résultats.


Activation : fichiers installes, redemarrage differe car une tache chat_image/image:0 etait en cours. Le processus serveur actuel execute encore les anciennes consignes. Attendre la fin des taches avant redemarrage. Tests : 280 passes, dont fondu reel et durees audio/video, 5 ignores. Comptes inchanges. Aucun rendu Flow lance pour cette correction.
