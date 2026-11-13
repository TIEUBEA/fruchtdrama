"""Montage settings (owner, 03/11/2026, like the Atelier "Le montage de mes vidéos").

Chosen once in Mes comptes, copied into each new episode: transitions, quick reframes inside a clip,
silences trimmed at the edges of each clip, karaoke subtitles. Pure functions, ffmpeg arguments only."""

import math

# « Rendu film » (owner 11/11/2026: « pas de saut d'image, pas de zoom excessif, comme un film »): no digital zoom or
# reframing added at the montage, light fade, natural pauses kept, and each clip starts from the last image of the
# previous clip when both happen in the same place (raccord).
DEFAULT = {'transition': 'fade_short', 'fast_cuts': False, 'cut_silences': False, 'karaoke': True, 'zoom': False, 'raccord': True, 'upscale': False}
# Episodes made before these settings keep their old look: slow zoom, straight cuts, nothing trimmed, no raccord.
LEGACY = {'transition': 'cut', 'fast_cuts': False, 'cut_silences': False, 'zoom': True, 'raccord': False, 'upscale': True}
FADES = {'cut': 0.0, 'fade_short': 0.25, 'fade_long': 0.6}
LABELS = {'cut': 'coupes franches', 'fade_short': 'fondu léger', 'fade_long': 'fondu long'}


def validate(value, current=None):
    """Merge a partial update into the current settings; refuse unknown keys or values."""
    if not isinstance(value, dict):
        raise ValueError('Réglages de montage invalides')
    out = {**DEFAULT, **(current or {})}
    for key, v in value.items():
        if key == 'transition':
            if v not in FADES:
                raise ValueError('Transition inconnue')
            out[key] = v
        elif key in ('fast_cuts', 'cut_silences', 'karaoke', 'zoom', 'raccord', 'upscale'):
            out[key] = bool(v)
        else:
            raise ValueError('Réglage de montage inconnu')
    return out


def of(config):
    """Settings of one episode; an episode without them keeps the legacy montage."""
    return {**DEFAULT, **LEGACY, **(config.get('montage') or {})}


def summary(settings):
    s = {**DEFAULT, **(settings or {})}
    return ' · '.join([LABELS[s['transition']], 'coupes rapides' if s['fast_cuts'] else 'plans continus',
                       'zoom de montage' if s.get('zoom') else 'sans zoom ajouté',
                       'raccord entre clips' if s.get('raccord') else 'clips indépendants',
                       'agrandi en 1080p' if s.get('upscale', True) else '720p natif',
                       'silences coupés' if s['cut_silences'] else 'silences gardés',
                       'sous-titres karaoké' if s['karaoke'] else 'sous-titres simples'])


def zoom(index, length, fast_cuts, fps=30):
    """zoompan expression: two or three framings inside one clip (fast cuts) or the slow push/pull."""
    if fast_cuts:
        a, b = round(length * fps / 3), round(length * fps * 2 / 3)
        near, mid = ('1.14', '1.06') if index % 2 == 0 else ('1.06', '1.14')
        return f'if(lt(on,{a}),1,if(lt(on,{b}),{near},{mid}))'
    return 'min(1+0.0012*on,1.08)' if index % 2 == 0 else 'max(1.08-0.0012*on,1)'


def trim(speech, length, lead=0.2, tail=0.35, minimum=2.0):
    """(start, new length) that shortens the blanks before the first and after the last spoken word.

    Without reliable word timings nothing is cut: a clip is never shortened on a guess."""
    words = (speech or {}).get('words') or []
    if not words or (speech or {}).get('match', 0) < .8:
        return 0.0, length
    first, last = float(words[0]['start']), float(words[-1]['end'])
    if not 0 <= first < last <= length:
        return 0.0, length
    start = max(0.0, first - lead)
    end = min(length, last + tail)
    if end - start < minimum or length - (end - start) < 0.3:
        return 0.0, length
    return round(start, 3), round(end - start, 3)


def target(duration):
    """Final length the episode must reach. TikTok pays only videos of more than one minute: 1 s of margin."""
    if not duration:
        return None
    return float(duration) + (1.0 if duration >= 60 else 0.0)


def scenes_for(duration, seconds, fade=0.0, low=3, high=40):
    """Plans needed so the untrimmed clips, fades included, reach the target length."""
    goal = target(duration) or 0.0
    n = max(low, -(-int(goal) // int(seconds)) if goal else low)
    while n < high and n * seconds - fade * (n - 1) < goal:
        n += 1
    return min(n, high)


def fit(full, cuts, goal, fade=0.0):
    """Give back trimmed silence, evenly, until the episode reaches its target length.

    full: real clip lengths; cuts: (start, length) from trim(). The kept part of each clip only grows,
    so every spoken word stays inside. Returns the (start, length) to use and the final duration."""
    overlap = fade * max(len(full) - 1, 0)
    trimmed = sum(length for _, length in cuts) - overlap
    removed = sum(f - length for f, (_, length) in zip(full, cuts))
    if not goal or trimmed >= goal or removed <= 0:
        return list(cuts), round(trimmed, 3)
    keep = min(1.0, max(0.0, (sum(full) - overlap - goal) / removed))  # share of the cut still removed
    out = []
    for f, (start, length) in zip(full, cuts):
        s = round(start * keep, 3)
        kept = f - keep * (f - length) if start or length < f else f
        out.append((s, min(f - s, math.ceil(kept * 1000 - 1e-6) / 1000)))  # rounded up: never under the target
    return out, round(sum(length for _, length in out) - overlap, 3)


def shift(speech, start):
    """Word timings of a trimmed clip, relative to its new start."""
    if not speech or not start:
        return speech
    return {**speech, 'words': [{**w, 'start': round(float(w['start']) - start, 3), 'end': round(float(w['end']) - start, 3)}
                                for w in speech.get('words', [])]}


def crossfade(lengths, fade):
    """filter_complex chaining xfade/acrossfade over the normalized clips, output labels [v] and [ao]."""
    if len(lengths) < 2 or not fade:
        return None
    parts, v, a, total = [], '[0:v]', '[0:a]', lengths[0]
    for k in range(1, len(lengths)):
        last = k == len(lengths) - 1
        nv, na = ('[vx]', '[a]') if last else (f'[v{k}]', f'[a{k}]')
        parts.append(f'{v}[{k}:v]xfade=transition=fade:duration={fade:g}:offset={total - fade:.3f}{nv}')
        parts.append(f'{a}[{k}:a]acrossfade=d={fade:g}{na}')
        v, a, total = nv, na, total + lengths[k] - fade
    parts.append('[vx]ass=subtitles.ass[v]')
    parts.append('[a]loudnorm=I=-14:TP=-1.5:LRA=11[ao]')
    return ';'.join(parts)
