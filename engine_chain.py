"""Bascule de moteur par clip (0.1.93). Pure functions on one scene; the server decides what is ready.

Owner, 06/11/2026, after an hour lost on a Flow clip that failed again and again: « Un essai par cas. Flow en
priorité ; ça ne marche pas → un essai sur Arena ; ça ne marche pas → un essai sur Vidogrid ; en dernier recours →
Grok lui-même. Si rien ne marche, modifier un peu la scène pour que le moteur l'accepte. »

Moteur V09 (owner, 09/11/2026): clip 1 is made by Grok; if Grok is not available (no ready account, limit, sign-in,
refusal, failure) clip 1 goes to Flow. Clips 2 to the end are made by Flow only: Grok NEVER makes clip 2 or later.
Flow uses Omni 1.2 Flash (engines.OMNI_12). When Flow refuses a scene, Vidogrid gets one or two tries. Arena was
removed and is never part of a chain again.

Round 0: one try per engine, in the chosen order, engines without a ready account skipped.
Round 1: the video prompt is softened (refusal.py vocabulary, video frame) and ONE more try is made on the first
ready engine (Flow when it can pay). After that the clip waits for the owner, with the reason given by each engine.
A try is recorded only when the engine itself was asked (or its page could not be used); an account change inside
Flow (another Google account) is not a new try.
"""
import re

import refusal

DEFAULT = ('flow', 'vidogrid', 'grok')
V09 = 'v09_grok_first'
VIDOGRID_TRIES = 2  # owner 09/11/2026: « essaye avec Vidogrid une ou deux fois »
LABELS = {'flow': 'Flow', 'grok': 'Grok', 'vidogrid': 'Vidogrid', 'arena': 'Arena'}  # Arena: logs of old clips
FINAL_ROUND = 1
VERBS = {'refusal': 'a refusé', 'quota': 'est à sa limite', 'timeout': 'n’a pas rendu le clip à temps',
         'login': 'demande une connexion', 'challenge': 'demande une vérification anti-robot',
         'credits': 'n’a plus de crédits', 'interface': 'a échoué', 'restart': 'a été interrompu', 'other': 'a échoué'}

VIDEO_FRAME = ('All-audiences family animation clip. Keep exactly the characters, place and visual style of the attached image. '
               'Nothing violent and nothing suggestive: tense moments are shown by looks, gestures and reactions, never by '
               'hitting, weapons or blood.\n')
VIDEO_LEAVE_OUT = ('\nIf a detail of this scene could be refused by your video rules, leave it out or show it differently, '
                   'and animate everything else. Generate the clip directly, no question.')
# Words that video filters refuse more often than image filters (fights, arrests, threats).
VIDEO_WORDS = (
    (r'\b(?:punch(?:es|ed|ing)?|hit(?:s|ting)?|slap(?:s|ped|ping)?|strik(?:e|es|ing)|beat(?:s|ing)? up)\b', 'confronts'),
    (r'\b(?:fight(?:s|ing)?|brawl(?:s|ing)?)\b', 'argument'), (r'\b(?:explod(?:e|es|ing)|explosion)\b', 'burst of light'),
    (r'\b(?:arrest(?:s|ed|ing)?|handcuff(?:s|ed)?)\b', 'stops'), (r'\b(?:threat(?:en|ens|ening)?)\b', 'warn'),
    (r'\b(?:cogne|frappe|gifle)\b', 'défie'), (r'\b(?:schlägt|Schlag)\b', 'stellt sich'),
)


def routing(settings, cfg=None):
    """Clip routing of an episode: its own setting, else the studio setting (V09 since the 09/11/2026 migration of
    server.read_state, and on every new episode), else the older chain."""
    return (cfg or {}).get('clip_routing') or (settings or {}).get('clip_routing') or 'chain'


def v09_policy(settings, cfg=None):
    return routing(settings, cfg) == V09


def v09_next(scene, index, grok_ready, vidogrid_ready=False):
    """Engine of the next try of clip `index` (0-based) under the V09 engine, or None when nothing is left to try.

    Clip 1: Grok first when it is ready, Flow when Grok is not available or failed. Every clip: Flow, with one adapted
    retry after a confirmed refusal. Owner 09/11/2026: when Flow still refuses the scene (« les vidéos dérangent »),
    Vidogrid is tried once or twice (VIDOGRID_TRIES). Grok is never returned for index >= 1. Arena is never used."""
    tries = scene.get('engine_tries') or []
    flow = [a for a in tries if a.get('engine') == 'flow']
    vido = [a for a in tries if a.get('engine') == 'vidogrid']
    if index == 0 and not tries and grok_ready:
        return 'grok'
    if not flow:
        return 'flow'
    if flow[-1].get('kind') == 'refusal' and len(flow) == 1 and not vido:
        return 'flow'
    # A technical failure before anything was sent (page not ready, new account dialog) gets one more Flow try
    # (real case 09/11/2026, clip 4: « Paramètres Flow indisponibles » on a newly detected account).
    if flow[-1].get('kind') == 'interface' and len(flow) == 1:
        return 'flow'
    refused = flow[-1].get('kind') == 'refusal' or (vido and vido[-1].get('kind') == 'refusal')
    if refused and vidogrid_ready and len(vido) < VIDOGRID_TRIES and (not vido or vido[-1].get('kind') not in ('quota', 'login', 'challenge', 'credits')):
        return 'vidogrid'
    return None


def order(settings, cfg=None):
    """Engines in the owner's order. An episode made for one engine (« Moteur des clips ») tries it first.
    Engines removed with the V09 engine (Arena, Vidogrid) found in old settings are ignored."""
    if v09_policy(settings,cfg):return ['flow','grok','vidogrid']
    if flow_grok_policy(settings,cfg):return ['flow','grok']
    raw = (cfg or {}).get('engine_chain') or (settings or {}).get('engine_chain') or DEFAULT
    out = [e for e in dict.fromkeys(raw if isinstance(raw, (list, tuple)) else DEFAULT) if e in DEFAULT] or list(DEFAULT)
    first = (cfg or {}).get('video_engine')
    if first in DEFAULT and first != 'flow' and first != out[0]:  # 'flow' is the default of every episode, not a choice
        out = [first] + [e for e in out if e != first]
    return out


def flow_grok_policy(settings, cfg=None):
    return routing(settings, cfg)=='flow_grok_per_clip'


def flow_grok_next(scene):
    """Each scene starts at Flow, with one adapted retry after a confirmed refusal."""
    attempts=scene.get('engine_tries') or []
    flow=[a for a in attempts if a.get('engine')=='flow']
    if not flow:return 'flow'
    if flow[-1].get('kind')=='refusal' and not any(a.get('engine')=='grok' for a in attempts):
        return 'flow' if len(flow)==1 else 'grok'
    return None


def validate(value):
    """Setting « ordre des moteurs »: a list of known engines, each at most once, at least one."""
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError('Ordre des moteurs : au moins un moteur attendu')
    out = []
    for e in value:
        if e not in DEFAULT:
            raise ValueError('Moteur vidéo inconnu : ' + str(e)[:20])
        if e not in out:
            out.append(e)
    return out


def round_of(scene):
    return int(scene.get('engine_round') or 0)


def tried(scene, round_=None):
    r = round_of(scene) if round_ is None else round_
    return [t['engine'] for t in scene.get('engine_tries') or [] if int(t.get('round') or 0) == r]


def pick(scene, chain, ready):
    """Engine for the next try of this clip in its current round, or None when the round is over."""
    r = round_of(scene)
    done = tried(scene, r)
    if r >= FINAL_ROUND and done:
        return None
    return next((e for e in chain if e not in done and ready(e)), None)


def short(reason, limit=110):
    """The provider's message, first sentence, without technical diagnostics."""
    text = ' '.join(str(reason or '').split())
    text = re.split(r' Diagnostic| Vu : |\{', text)[0]
    for prefix in ('Flow a refusé ce clip : ', 'Google Flow : ', 'Flow : ', 'Grok Imagine : ', 'LMArena vidéo : ', 'Vidogrid : '):
        if text.startswith(prefix):
            text = text[len(prefix):]
    first = re.split(r'(?<=[.!?])\s', text)[0].rstrip('.')
    return (first[:limit - 1] + '…') if len(first) > limit else first


def record(scene, engine, kind, reason, at):
    entry = {'engine': engine, 'round': round_of(scene), 'kind': kind, 'reason': short(reason), 'at': at}
    scene.setdefault('engine_tries', []).append(entry)
    return entry


def advance(scene, chain, ready):
    """Next engine after a failed try: the next one of this round, else the softened round, else None."""
    nxt = pick(scene, chain, ready)
    if nxt or round_of(scene) >= FINAL_ROUND:
        return nxt
    scene['engine_round'] = FINAL_ROUND
    return pick(scene, chain, ready)


def line(index, engine, kind, reason, nxt, softened=False):
    """« Clip 3 : Flow a refusé (raison) → essai sur Arena. »"""
    text = f'Clip {index + 1} : {LABELS.get(engine, engine)} {VERBS.get(kind, VERBS["other"])}'
    if reason:
        text += f' ({short(reason)})'
    if nxt:
        text += (' → prompt adouci, nouvel essai sur ' if softened else ' → essai sur ') + LABELS.get(nxt, nxt) + '.'
    else:
        text += '.'
    return text


def summary(scene):
    """Reason given by each engine, for « Action requise »."""
    return '; '.join(f"{LABELS.get(t['engine'], t['engine'])}{' (prompt adouci)' if t.get('round') else ''} : {t.get('reason') or VERBS.get(t.get('kind'), 'échec')}"
                     for t in scene.get('engine_tries') or [])


def soften(prompt):
    """Video prompt reworded once, like refusal.py does for images (level 2), with a video frame."""
    text = str(prompt)
    for pattern, repl in refusal.LEVEL1 + refusal.LEVEL2 + VIDEO_WORDS:
        text = re.sub(pattern, repl, text, flags=re.I)
    return VIDEO_FRAME + text + VIDEO_LEAVE_OUT


def reset(scene):
    """A clip received (or redone by the owner) starts again from the first engine."""
    for key in ('engine_tries', 'engine_round', 'engine_exhausted', 'flow_rewrite_pending'):
        scene.pop(key, None)
