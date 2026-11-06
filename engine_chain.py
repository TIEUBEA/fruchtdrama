"""Bascule de moteur par clip. Pure functions on one scene; the server decides what is ready.

0.1.93 (owner, 06/11/2026): « Un essai par cas » — each clip tries the engines in order, one try each.
0.1.97 (owner, 06/11/2026 evening): « On n'a plus que Flow et Grok. Pour chaque scène : un premier essai sur Flow. Si le
clip n'est pas généré, bascule DIRECTEMENT sur Grok. Si après un essai Flow et un essai Grok il y a un problème,
rapporte directement l'erreur dans le studio et CONTINUE. » No softened round, no validation before Grok: after one try
on each engine the clip is set aside with the reason of each engine, and the other clips go on.

A try is recorded only when the engine itself was asked (or its page could not be used); an account change inside
Flow (another Google account) is not a new try. An uncertain Flow submission counts as Flow's try.
"""
import re

DEFAULT = ('flow', 'grok')
LABELS = {'flow': 'Flow', 'grok': 'Grok'}
VERBS = {'refusal': 'a refusé', 'quota': 'est à sa limite', 'timeout': 'n’a pas rendu le clip à temps',
         'login': 'demande une connexion', 'challenge': 'demande une vérification anti-robot',
         'credits': 'n’a plus de crédits', 'interface': 'a échoué', 'restart': 'a été interrompu',
         'uncertain': 'n’a pas confirmé l’envoi', 'unavailable': 'n’a aucun compte prêt', 'other': 'a échoué'}


def label(engine):
    return LABELS.get(engine, str(engine).capitalize())


def order(settings, cfg=None):
    """Engines in the owner's order. An episode made for Grok (« Moteur des clips ») tries it first.
    Engines removed in 0.1.97 (Arena, Vidogrid) found in old settings are ignored."""
    raw = (cfg or {}).get('engine_chain') or (settings or {}).get('engine_chain') or DEFAULT
    raw = list(dict.fromkeys(raw if isinstance(raw, (list, tuple)) else DEFAULT))
    out = [e for e in raw if e in DEFAULT]
    if len(out) < len(raw) or not out:
        # An order saved before 0.1.97 (with Arena or Vidogrid): Flow and Grok both stay in the chain.
        out += [e for e in DEFAULT if e not in out]
    first = (cfg or {}).get('video_engine')
    if first in DEFAULT and first != 'flow' and first != out[0]:  # 'flow' is the default of every episode, not a choice
        out = [first] + [e for e in out if e != first]
    return out


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


def tried(scene):
    return [t['engine'] for t in scene.get('engine_tries') or []]


def pick(scene, chain, ready):
    """Engine for the next try of this clip, or None when every engine was tried or none is ready."""
    done = tried(scene)
    return next((e for e in chain if e not in done and ready(e)), None)


def short(reason, limit=110):
    """The provider's message, first sentence, without technical diagnostics."""
    text = ' '.join(str(reason or '').split())
    text = re.split(r' Diagnostic| Vu : |\{', text)[0]
    for prefix in ('Flow a refusé ce clip : ', 'Google Flow : ', 'Flow : ', 'Grok Imagine : '):
        if text.startswith(prefix):
            text = text[len(prefix):]
    first = re.split(r'(?<=[.!?])\s', text)[0].rstrip('.')
    return (first[:limit - 1] + '…') if len(first) > limit else first


def record(scene, engine, kind, reason, at):
    entry = {'engine': engine, 'kind': kind, 'reason': short(reason), 'at': at}
    scene.setdefault('engine_tries', []).append(entry)
    return entry


def advance(scene, chain, ready):
    """Next engine after a failed try, or None: the clip is set aside."""
    return pick(scene, chain, ready)


def line(index, engine, kind, reason, nxt):
    """« Clip 3 : Flow a refusé (raison) → essai sur Grok. »"""
    text = f'Clip {index + 1} : {label(engine)} {VERBS.get(kind, VERBS["other"])}'
    if reason:
        text += f' ({short(reason)})'
    text += (' → essai sur ' + label(nxt) + '.') if nxt else '.'
    return text


def summary(scene):
    """« Flow (raison) puis Grok (raison) »: the reason given by each engine."""
    return ' puis '.join(f"{label(t['engine'])} ({t.get('reason') or VERBS.get(t.get('kind'), 'échec')})"
                         for t in scene.get('engine_tries') or [])


def failure(index, scene):
    """The alert of a clip set aside (owner wording)."""
    return f'Clip {index + 1} : {summary(scene) or "aucun moteur prêt"} — clip à refaire. Les autres clips continuent.'


def reset(scene):
    """A clip received (or redone by the owner) starts again from the first engine."""
    for key in ('engine_tries', 'engine_round', 'engine_exhausted'):
        scene.pop(key, None)
