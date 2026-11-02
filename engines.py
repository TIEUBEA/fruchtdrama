"""Video engines (P5-06). Flow keeps its credit logic; Grok and Arena run in the same FruchtDrama window."""

ENGINES = {
    # seconds: duration asked in the prompt; range: accepted clip duration (QC) and montage clamp.
    'flow': {'label': 'Google Flow', 'seconds': 8, 'range': (7.5, 8.5), 'home': 'https://labs.google/fx/tools/flow'},
    'grok': {'label': 'Grok Imagine', 'seconds': 6, 'range': (5.5, 10.5), 'home': 'https://grok.com/imagine'},
    'arena': {'label': 'LMArena (vidéo)', 'seconds': 8, 'range': (4.0, 10.5), 'home': 'https://lmarena.ai/'},
}
# Engines whose browser connector is available in this version.
AVAILABLE = ('flow',)


def validate(name):
    name = str(name or 'flow')
    if name not in ENGINES:
        raise ValueError('Moteur vidéo inconnu')
    return name


def of(j):
    return j.get('config', {}).get('video_engine', 'flow')


def spec(j):
    return ENGINES.get(of(j), ENGINES['flow'])


def clip_length(j, actual):
    """Montage length of one clip: Flow stays exactly 8 s; other engines keep their real duration, bounded."""
    if of(j) == 'flow':
        return float(spec(j)['seconds'])
    low, high = spec(j)['range']
    return round(min(max(float(actual or 0), low), high), 3)


def word_limit(j, base=20):
    """Spoken words per scene scale with the clip duration (20 words for 8 s)."""
    return max(8, int(base * spec(j)['seconds'] / 8))
