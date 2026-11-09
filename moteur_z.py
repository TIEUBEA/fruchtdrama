"""Moteur FRUIT-Z (owner, 09/11/2026): the one video engine of Arnaud, ~/Projets/Dev/fruit-france, MOTEUR.md §Z.

« Mécanique + concept neuf » (d'après le live de SAGA DES FRUITS): videos copied at ~90 % (story and lines) were banned
for « contenu non original » on 08/11/2026. From a viral video only its STRUCTURE is kept:
1. the source is studied (transcription = its script, key frames);
2. its mechanics in 7 points (situation one recognises, secret or problem, a start that goes well, rising tension,
   incidents that make the masks fall, revelations, an ending that calls for part 2); no character, no line, no
   signature object of the source is kept;
3. a NEW concept on the same mechanics: story, characters, situations and dialogues 100 % new, a better version, in a
   realistic everyday setting of the country of the episode language (France métropolitaine for French), no magic nor
   spectacular scenes unless the mechanics need it, gestures, looks and moves all the time;
4. 7 sequences of 10 s + 1 call clip (« Amen » when the story carries prayer or strong emotion, otherwise adapted), a
   mini-series: part 2 starts exactly where part 1 stops;
5. characters locked (full appearance in every prompt);
6. each sequence = an OPENING image + a CLOSING image + a 10 s video prompt (timed lines, camera and actions in sync);
7. Flow only, Omni 1.2 Flash, 720p, 9:16, 10 s, Début + Fin; Flow refusals: minors → clearly adult characters,
   violence → softer action, third-party content → new images and new prompt for that sequence.
"""
from __future__ import annotations

SEQUENCES = 7
SCENES = SEQUENCES + 1  # + the call clip
SECONDS = 10
ROUTING = 'fruit_z'

# Realistic everyday settings per episode language (§Z: « cadre français métropolitain » for the French account).
SETTINGS = {
    'fr': 'la France métropolitaine d’aujourd’hui (appartement parisien, brasserie, restaurant, rue de Paris, bureau, '
          'cuisine de famille), dialogues en français de France avec des expressions actuelles',
    'de': 'l’Allemagne d’aujourd’hui (Altbauwohnung à Berlin, Kneipe, Bäckerei, rue de Munich, bureau, cuisine de famille), '
          'dialogues en allemand parlé actuel',
    'en': 'today’s United States (apartment, diner, office, suburban kitchen, city street), dialogues in current spoken American English',
    'es': 'la España de hoy (piso en Madrid, bar, terraza, calle, oficina, cocina familiar), diálogos en español de España actual',
    'pt': 'o Brasil de hoje (apartamento, padaria, escritório, rua de São Paulo, cozinha de família), diálogos em português do Brasil atual',
}


def setting(language: str) -> str:
    code = str(language or '').split('(')[-1][:2].lower() if '(' in str(language or '') else str(language or '')[:2].lower()
    return SETTINGS.get(code, SETTINGS['fr'])


def schema_extras(schema: dict) -> dict:
    """Fields the writer fills in FRUIT-Z: the 7-point mechanics and the closing image of each sequence."""
    schema['mecanique'] = {
        'situation': 'la situation où le spectateur se reconnaît (une phrase)',
        'secret': 'le secret ou le problème',
        'debut': 'le début qui va bien',
        'montee': 'la montée de tension',
        'incidents': 'les incidents qui font tomber les masques',
        'revelations': 'les révélations',
        'fin': 'la fin qui donne envie de la partie 2',
        'repris_de_la_source': 'ce qui est repris de la vidéo d’origine : la STRUCTURE seulement',
    }
    scene = schema['scenes'][0]
    keys = list(scene)
    at = keys.index('image_prompt') + 1 if 'image_prompt' in keys else len(keys)
    schema['scenes'][0] = {**{k: scene[k] for k in keys[:at]},
                           'end_image_prompt': 'IMAGE DE FERMETURE : la dernière image des 10 s (mêmes personnages, même lieu, l’état à la fin de la séquence), pour un dessinateur, 9:16',
                           **{k: scene[k] for k in keys[at:]}}
    return schema


def guidance(analysis: dict | None, language: str, style: dict | None = None, has_source: bool = True,
             transcript_given: bool = False) -> str:
    """What the writer is told (MOTEUR §Z). With a source: its transcription is the script whose mechanics are taken."""
    analysis = analysis or {}
    style = style or {}
    body = style.get('writer') or 'humanoïde-fruit : la tête EST le fruit, corps 100 % fruit, vrais vêtements'
    source = ''
    if has_source:
        transcript = str(analysis.get('transcript') or '').strip()
        source = ('' if transcript_given else '\nVIDÉO VIRALE D’ORIGINE (sa transcription = son script ; ses images sont jointes) :\n'
                  + (transcript[:6000] if transcript else '(pas de transcription : lis la structure sur les images jointes)')) + (
                  '\nDe cette vidéo, tu n’en gardes QUE la mécanique. Interdit : ses personnages, ses prénoms, ses répliques (aucune suite de 4 mots '
                    'identique), ses objets signature, ses lieux, son métier central. Toute ressemblance de contenu est une faute.')
    return f'''MOTEUR FRUIT-Z — MÉCANIQUE + CONCEPT NEUF (règle du propriétaire, priorité absolue sur toute autre consigne) :
On ne recopie JAMAIS une vidéo : les copies à 90 % ont été bannies pour « contenu non original ». On garde seulement la STRUCTURE d’une virale.{source}
1. MÉCANIQUE (champ mecanique) : la structure en 7 points — situation où l’on se reconnaît ; secret ou problème ; début qui va bien ; montée ; incidents qui font tomber les masques ; révélations ; fin qui donne envie de la partie 2.
2. CONCEPT NEUF : histoire, personnages, situations et dialogues 100 % nouveaux sur cette mécanique, en version améliorée (accroche plus forte, émotion plus nette). Cadre réaliste : {setting(language)}. Réalisme : pas de magie ni de scènes spectaculaires, sauf si la mécanique l’exige. Gestes, regards et déplacements permanents ; aucun personnage immobile sans raison, aucune longue pause.
3. PERSONNAGES : style imposé pour cette vidéo — {body} — inspirés de ce qui marche en ce moment sur TikTok, pour sortir de la monotonie. Tous clairement ADULTES (âge adulte écrit dans appearance), sauf si l’histoire a besoin d’un enfant, alors jamais en danger. Apparence complète et tenue identiques dans chaque prompt.
4. DÉCOUPAGE : exactement {SEQUENCES} séquences d’histoire de {SECONDS} secondes, puis la scène {SCENES} = APPEL : un personnage principal se tourne vers la caméra et parle au spectateur (une ou deux phrases). Si l’histoire porte une prière, une foi ou une émotion forte (trahison, injustice, larmes), il demande d’écrire « Amen » en commentaire ; sinon un appel du même genre adapté à l’émotion (« Écris SUITE si tu veux la partie 2 »). Pensé comme une mini-série : la partie 2 reprendra exactement là où la séquence {SEQUENCES} s’arrête.
5. CHAQUE SÉQUENCE = image_prompt (IMAGE D’OUVERTURE : la première image des {SECONDS} s) + end_image_prompt (IMAGE DE FERMETURE : la dernière image des {SECONDS} s, mêmes personnages, même lieu, l’état atteint à la fin) + video_prompt de {SECONDS} s qui va de l’une à l’autre : « {SECONDS} seconds, vertical 9:16, ONE continuous shot: <caméra>. » puis des temps « [00:00-00:04] NOM (fruit, tenue, place) action : « réplique » », caméra et gestes synchronisés avec les paroles, couvrant les {SECONDS} s.
6. RYTHME : accroche dans la première seconde (première réplique de moins de 12 mots, dite à l’écran) ; environ 3 mots par seconde, au plus {3 * SECONDS} mots par séquence ; jamais de blanc.
7. FLOW : jamais de violence montrée (on la suggère par les regards et les réactions), jamais de nom de studio, d’œuvre ni de marque, aucune enseigne ni logo.'''
