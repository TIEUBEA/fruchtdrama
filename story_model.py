"""Reusable original-story model learned from the owner's selected fruit video."""

MODEL_ID = 'humanlike_fruit_cinema_v1'
LABEL = 'Fruits humanoïdes — récit cinématographique'
REFERENCE_URL = 'https://www.tiktok.com/@bikinifruit/video/7688352616987938081'

INSTRUCTIONS = '''MODÈLE FRUITS HUMANOÏDES — RÉCIT CINÉMATOGRAPHIQUE.
La référence donne un langage visuel et une manière de raconter, jamais des dialogues ou un scénario à recopier.
Structure souple dans la durée demandée : rencontre ou conflit concret dès le début ; enjeu émotionnel compréhensible ; décision qui entraîne une action ; conséquence visible ; retournement motivé ; réaction finale ou choix moral. N'impose pas un enfant pauvre, un couple riche, une caisse d'argent ou une adoption à chaque histoire.
Un plan technique de six ou huit secondes n'est pas une scène dramatique entière. Une même conversation peut continuer sur deux ou trois clips, dans le même lieu, avec le même accessoire et le même axe. Change de lieu seulement lorsque l'action l'exige ; montre un départ, une arrivée ou un indice de transition clair.
Les répliques se répondent : demande, réponse, objection ou décision. Chaque réplique doit modifier ce que sait ou veut un personnage. Alterne une réplique courte et une réponse développée ; n'impose ni deux phrases symétriques ni un nouveau choc à chaque clip. Jusqu'à trois tours de parole et deux locuteurs par clip, sans chevauchement et dans le plafond total de mots. Une accroche brève n'oblige pas tout l'épisode à parler par slogans.
La parole occupe naturellement l'essentiel du plan ; gestes et marche peuvent accompagner le dialogue. N'ajoute pas de narration pour expliquer ce que l'image montre. Une pause doit correspondre à une réaction, pas à du temps vide.
Pour chaque clip, précise dans video_prompt l'action au début, le geste central, la position finale et le raccord vers le clip suivant. Dans image_prompt, place les pieds, les mains et les objets pour permettre l'action. Évite de recadrer arbitrairement à chaque clip. Ne fais pas parler un personnage absent de l'image.
Continuité stricte : un visage, une silhouette, une tenue et une voix par personnage ; même main pour l'objet, mêmes côtés de l'écran, déplacements réalisables. La référence change parfois de costume : notre version conserve la tenue tant que l'histoire ne montre pas explicitement un changement.
Jusqu'à dix personnages utiles dans l'épisode, mais seulement ceux nécessaires dans chaque plan. Rendu de fruits humanoïdes avec corps humains crédibles, visages expressifs intégrés à la tête du fruit, vêtements réalistes et décors de cinéma. Pas de masque humain collé sur un fruit, pas de corps de jouet.
La langue choisie dans l'application s'applique à tous les dialogues et textes. Une référence française ne change pas une production allemande.
'''


def instructions(job):
    config = job.get('config', {})
    return INSTRUCTIONS if config.get('narrative_model') == MODEL_ID or config.get('niche', 'Fruits') == 'Fruits' else ''
