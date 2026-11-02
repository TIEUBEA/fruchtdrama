# P4 — Montage et entretien

| ID | Exigence | État |
|---|---|---|
| P4-01 | Supprimer une production : dossier déplacé dans `data/corbeille` (récupérable), copie de l'état avant, refus si tâche en cours, montage en cours ou clip Flow incertain ; retrait de la file de nuit. | Fait (0.1.51) |
| P4-02 | Purge de `state.json` : tâches terminées de plus de 30 jours et tâches de productions supprimées, journal de 300 événements par production ; un envoi Flow peut-être facturé est conservé comme preuve. Copie de sauvegarde avant (10 dernières gardées). Au démarrage et à la demande. | Fait (0.1.51) |
| P4-03 | Rapport de panne copiable : système, passerelles, productions, dernières erreurs ; sans jeton, code d'appairage ni adresse e-mail. | Fait (0.1.51) |
| P4-04 | Sous-titres karaoké : chaque mot s'allume en jaune quand il est prononcé, calé sur les horodatages de la transcription ; accolades du texte neutralisées ; par défaut pour les nouvelles productions, désactivable. | Fait (0.1.51) |
| P4-05 | Alignement des sous-titres selon la durée réelle du clip (Arena jusqu'à 10 s). | Fait (0.1.51) |
| P4-06 | Transitions (fondu enchaîné court, zoom léger) en option. | À faire |
| P4-07 | Coupe des silences de début et de fin des clips (avec garde-fou pour la synchronisation labiale). | À faire |
| P4-08 | Contrôle de hauteur de voix (personnage enfant/adulte, inversion). | À faire |

Tests : `tests/test_p4_maintenance.py`, `tests/test_p4_karaoke.py` (dont montage ffmpeg réel).
