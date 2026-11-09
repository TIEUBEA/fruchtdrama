"""Moteur V09 — the faithful-copy engine of fruit-france (MOTEUR.md §S, process frozen on V09 by the owner, 08/11/2026).

Owner, 09/11/2026: « quand on veut reproduire une vidéo avec notre studio, il produit carrément autre chose ».
The studio's « Recréer à l'identique » now follows the V09 engine, point by point:
- the story of the reference is reproduced IDENTICALLY (same scenes, same order, same actions, same twists, same lines
  translated into the episode language, same framing, same settings, same ending); ONLY the characters change: each
  becomes a fruit humanoid (body 100 % fruit, hands included) with a new name that evokes its fruit;
- the source is cut into consecutive windows of one clip length (10 s with Omni 1.2 Flash); each scene carries its
  `ref` (« 00:10-00:20 ») and reproduces that window second by second;
- one extra clip at the end: the call to action (« écris Amen » when the story carries prayer or strong emotion, as in
  V09; otherwise « écris SUITE »), said by a character looking at the camera;
- clip prompts in the V09 format: one continuous shot, timed beats « [00:00-00:05] », each speaker described with the
  line in « », then the fixed V09 closing block (lips, fruit bodies, no narrator, no music, no subtitles, language).
"""
from __future__ import annotations

import math
import re

# Closing block of every V09 clip prompt (videos/V09-la-bouteille/phase2.json, prompt_clip), language made generic.
CLIP_END = ('Only the character who speaks moves his or her lips; the others keep their mouths closed. '
            'Lines follow each other with no silence. High-end 3D animated feature-film render. '
            'Bodies 100 % fruit: hands, fingers, arms and neck covered with the same fruit skin, never human skin. '
            'Same faces, outfits, place and light as in the images. No brand logos. '
            'Characters speak on screen with lip sync, no narrator, no voice-over, no music, no subtitles, no added text. '
            'Language: {language} only, natural native accent.')

# MOTEUR §L, §D: full fruit body, French-film quality look (no studio or brand names: Flow refuses them, §R).
BODY = ('Every character is a fruit humanoid: the head IS the fruit (same size as a human head, face formed in the fruit '
        'skin), neck, arms, hands and fingers covered with the same fruit skin, never human skin, human proportions, '
        'real fabric clothes. High-end 3D animated feature-film render, expressive eyes, rich textures.')

BRANDS = re.compile(r'\b(pixar|disney|dreamworks|illumination|ghibli|marvel|minions|shrek)\b', re.I)


def clock(t: float) -> str:
    t = max(0, int(round(t)))
    return f'{t // 60:02d}:{t % 60:02d}'


def scene_count(source_seconds: float, clip_seconds: int, low: int = 3, high: int = 40) -> int:
    """One scene per window of the source (one clip length each) plus the call-to-action clip."""
    windows = max(1, math.ceil(float(source_seconds or 0) / max(1, clip_seconds) - 0.15))
    return max(low, min(high, windows + 1))


def windows(source_seconds: float, clip_seconds: int, scenes: int) -> list[tuple[float, float]]:
    """Source window of each story scene (the last scene is the call, it has no window)."""
    story = max(1, scenes - 1)
    total = float(source_seconds or story * clip_seconds)
    step = total / story
    return [(k * step, min(total, (k + 1) * step)) for k in range(story)]


def _lines(transcript: str) -> list[tuple[float, str]]:
    out = []
    for raw in str(transcript or '').splitlines():
        m = re.match(r'\[(\d+):(\d+(?:\.\d+)?)\]\s*(.+)', raw.strip())
        if m:
            out.append((int(m.group(1)) * 60 + float(m.group(2)), m.group(3).strip()))
    return out


def decoupage(transcript: str, source_seconds: float, clip_seconds: int, scenes: int) -> list[dict]:
    """Plan-by-plan breakdown handed to the writer: for each story scene its `ref` and the source lines said in it."""
    rows = [{'ref': f'{clock(a)}-{clock(b)}', 'start': a, 'end': b, 'lines': []}
            for a, b in windows(source_seconds, clip_seconds, scenes)]
    if not rows:
        return []
    for t, text in _lines(transcript):
        k = next((i for i, r in enumerate(rows) if r['start'] <= t < r['end']), len(rows) - 1)
        rows[k]['lines'].append(f'[{clock(t)}] {text}')
    return rows


def guidance(analysis: dict, scenes: int, clip_seconds: int, language: str) -> str:
    """What the writer is told in « Recréer à l'identique » (V09 engine, MOTEUR §S)."""
    analysis = analysis or {}
    if scenes < 2:
        scenes = scene_count(analysis.get('duration') or 0, clip_seconds)
    total = analysis.get('duration') or (scenes - 1) * clip_seconds
    rows = decoupage(analysis.get('transcript', ''), total, clip_seconds, scenes)
    plan = '\n'.join(f"Scène {k + 1} — ref {r['ref']} : " + (' / '.join(r['lines']) if r['lines'] else
                     '(pas de parole : reproduis l’action visible sur les images à ce moment)') for k, r in enumerate(rows))
    return f'''MOTEUR V09 — COPIE FIDÈLE (règle du propriétaire, priorité absolue sur toute autre consigne) :
On reproduit l’histoire de la vidéo d’origine À L’IDENTIQUE ; on ne change QUE les personnages.
1. Histoire identique : mêmes scènes, même ordre, mêmes actions, mêmes gestes, mêmes objets, mêmes retournements, mêmes répliques, même rythme, même cadrage, mêmes décors, même fin, même émotion. N’invente rien : aucun autre conflit, aucun personnage principal en plus, aucun secret, aucun objet, aucun lieu que la vidéo ne montre pas. Ne retire aucun événement. Toute différence avec l’original est une erreur, sauf les personnages.
2. Répliques : celles de l’original, dans le même ordre, dites par le même rôle, traduites fidèlement en {language} parlé naturel (même sens, même force, mêmes mots forts ; seulement adoucir un juron ou une insulte trop crue). Les noms propres de l’original sont remplacés par les nouveaux noms.
3. Personnages : chaque rôle de l’original garde son rôle, son âge, son métier, son lien avec les autres, sa tenue, sa coiffure et ses signes distinctifs, mais devient un humanoïde-fruit : la tête EST le fruit, corps 100 % fruit (cou, bras, mains et doigts à la peau du fruit, jamais de main humaine), vrais vêtements. Choisis le fruit selon le rôle (piquant, doux, abîmé, précieux…), jamais deux fois le même fruit. Nouveau prénom qui évoque le fruit (jeu de mots, son ou couleur : Prunelle pour une prune, Goyo pour une goyave). Dans appearance : âge ADULTE explicite pour tout adulte, le fruit de la tête décrit (couleur, matière, tige, feuille), la tenue de l’original.
4. Découpage plan par plan : la source est coupée en fenêtres consécutives de {clip_seconds} secondes, une scène par fenêtre, dans l’ordre ci-dessous. Chaque scène a le champ ref (temps de la source, recopié tel quel) et reproduit SA fenêtre seconde par seconde : lieu, qui est où, posture, geste, objet, cadrage, mouvement de caméra, répliques, émotion. Regarde les images jointes au même temps pour le décor, les places, les gestes et les cadrages.
{plan}
Scène {scenes} — APPEL À L’ACTION (pas de ref) : un personnage principal se tourne vers la caméra et parle au spectateur, une ou deux phrases. Si l’histoire porte une prière, une foi ou une émotion forte (trahison, injustice, larmes), il demande d’écrire « Amen » en commentaire s’il est d’accord (c’est ce qui a fait percer V09) ; sinon, un appel du même genre adapté à l’histoire (« Tu veux la suite ? Écris SUITE en commentaire »). Dans cette scène seulement, le regard caméra est voulu.
5. Accroche : la première réplique de la scène 1 est la première réplique de l’original, dite dans la première seconde, sans plan d’ambiance avant. Pas de titre incrusté.
6. Images : image_prompt = la PREMIÈRE image de la fenêtre (même cadrage que l’original : plan moyen, gros plan, plongée…), décrite pour un dessinateur, avec qui est où, le geste en cours, les objets lisibles, l’émotion de chaque visage. Si la fin de la fenêtre change l’histoire (un objet apparaît, un chiffre change, une révélation), décris aussi cet état final dans video_prompt.
7. video_prompt au format V09, en anglais pour la mise en scène et les répliques dans la langue demandée : « {clip_seconds} seconds, vertical 9:16, ONE continuous shot, NO hard cuts: <mouvement de caméra>. » puis un ou plusieurs temps « [00:00-00:05] NOM (description courte : fruit de la tête, tenue, place dans le cadre) <action> : « réplique exacte » » qui couvrent les {clip_seconds} secondes dans l’ordre de l’original. Jamais de nom de studio, d’œuvre ou de marque (Flow refuse). Les répliques du video_prompt sont exactement celles de dialogue, dans le même ordre.
8. Densité : environ 3 mots par seconde (au plus {3 * clip_seconds} mots par scène de {clip_seconds} s), comme l’original ; jamais de blanc. Si l’original parle moins dans une fenêtre, garde ses répliques et son action, n’ajoute pas de bavardage.
9. Décors : ceux de l’original (même pièce, même lumière, mêmes objets), sans enseigne ni logo.'''


def clip_prompt(j: dict, s: dict, seconds: int, cast: str, dialog: str, language: str) -> str:
    """V09 clip prompt: the writer's timed beats, the cast lock, the exact lines, then the V09 closing block."""
    video = BRANDS.sub('3D animated', str(s.get('video_prompt') or ''))
    if not re.search(r'\bseconds?\b', video[:200], re.I):
        video = f'{seconds} seconds, vertical 9:16, ONE continuous shot, NO hard cuts. ' + video
    else:
        video = re.sub(r'\b(?:6|8|10|15)\s+seconds\b', f'{seconds} seconds', video, count=1)
    return (f"Animate this exact image (first frame). {video}\n\n"
            f"Cast (identity lock, keep exactly as in the image):\n{cast}\n{BODY}\n\n"
            f"Exact dialogue in this order; only the named speaker moves their lips:\n{dialog}\n\n"
            + CLIP_END.format(language=language))
