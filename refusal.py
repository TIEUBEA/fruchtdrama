"""Graduated rewording of an image prompt refused by ChatGPT (P2-05). Pure functions.

Level 1: softer vocabulary (EN/DE/FR) and an all-audiences frame that KEEPS the described visual style
(the Atelier forced a cartoon style on every niche). Level 2: also neutral ages and an instruction to
leave out or show differently the refused detail. Beyond level 2 the owner decides.
"""
import re

MAX_LEVEL = 2

LEVEL1 = (
    (r'\bblood(?:y|ied)?\b', 'red juice'), (r'\bbleeding\b', 'dripping red juice'), (r'\bknives\b', 'kitchen utensils'),
    (r'\bknife\b', 'kitchen utensil'), (r'\b(?:guns?|pistols?|revolvers?|rifles?|weapons?)\b', 'object'),
    (r'\b(?:corpses?|dead bod(?:y|ies))\b', 'motionless figure'), (r'\b(?:murder(?:ed|er)?|kill(?:ed|ing|er)?)\b', 'mystery'),
    (r'\bkidnapp?(?:ed|er|ing)?\b', 'disappearance'), (r'\b(?:naked|nude|undressed)\b', 'simply dressed'),
    (r'\b(?:underwear|lingerie)\b', 'outfit'), (r'\b(?:tied up|gagged)\b', 'held back'), (r'\b(?:drunk|wasted)\b', 'dizzy'),
    (r'\bBlut(?:ig)?\b', 'roter Saft'), (r'\bMesser\b', 'Küchenutensil'), (r'\b(?:Waffe|Pistole|Gewehr)n?\b', 'Gegenstand'),
    (r'\bLeiche\b', 'reglose Figur'), (r'\b(?:Mord|ermordet)\b', 'Rätsel'), (r'\bentführt\b', 'verschwunden'),
    (r'\bsang(?:lant|lante)?\b', 'jus rouge'), (r'\bcouteaux?\b', 'ustensile'), (r'\b(?:armes?|pistolets?|fusils?)\b', 'objet'),
    (r'\bcadavres?\b', 'corps immobile'), (r'\b(?:meurtre|tué)\b', 'mystère'), (r'\b(?:enlevée?|kidnappée?)\b', 'disparue'),
)
LEVEL2 = ((r'\byoung (wom[ae]n|girls?)\b', r'\1'), (r'\bjunge (Frau|Mädchen)\b', r'\1'), (r'\bjeunes? (femmes?|filles?)\b', r'\1'))

FRAME = ('All-audiences family animation image, keep exactly the visual style described below. Characters fully clothed, '
         'eye-level framing, ordinary shot; nothing violent, nothing suggestive, nobody is secretly watched.\n')
LEAVE_OUT = ('\nIf a detail of this scene could be refused by your image rules, leave it out or show it differently, '
             'and draw everything else. Do not ask questions: generate the image directly.')


def soften(prompt, level):
    """Return the prompt for a rewording level (0 = unchanged)."""
    if level <= 0:
        return prompt
    text = prompt
    for pattern, repl in LEVEL1 + (LEVEL2 if level >= 2 else ()):
        text = re.sub(pattern, repl, text, flags=re.I)
    return FRAME + text + (LEAVE_OUT if level >= 2 else '')


IMAGE_SLOTS = re.compile(r'(?:characters|character:[a-z][a-z0-9_]{0,24}|image:\d+|cover)')


def applies(task):
    return task.get('kind') == 'chat_image' and bool(IMAGE_SLOTS.fullmatch(str(task.get('slot', ''))))
