"""Video engines (P5-06). Flow keeps its credit logic; Grok, Arena and Vidogrid run in the same FruchtDrama window.

0.1.93: each clip may come from another engine (bascule par clip, engine_chain.py); the montage and the quality
check then use the engine of the clip itself (scene['engine']), the scenario keeps the episode's engine."""

ENGINES = {
    # seconds: duration asked in the prompt; range: accepted clip duration (QC) and montage clamp.
    'flow': {'label': 'Google Flow', 'seconds': 8, 'range': (7.5, 8.5), 'home': 'https://labs.google/fx/tools/flow'},
    'grok': {'label': 'Grok Imagine', 'seconds': 6, 'range': (5.5, 10.5), 'home': 'https://grok.com/imagine'},
    'arena': {'label': 'LMArena (vidéo)', 'seconds': 8, 'range': (4.0, 10.5), 'home': 'https://arena.ai/video'},
    # vidogrid.ai, model « Grok Imagine Video 1.5 Lite », 10 s clips in 720p (parcours vérifié dans fruit-france, V57).
    'vidogrid': {'label': 'Vidogrid (Grok Lite)', 'seconds': 10, 'range': (5.5, 10.5), 'home': 'https://vidogrid.ai/app/video-gen/grok'},
}
# Engines whose browser connector is available in this version.
AVAILABLE = ('flow', 'grok', 'arena', 'vidogrid')


def validate(name):
    name = str(name or 'flow')
    if name not in ENGINES:
        raise ValueError('Moteur vidéo inconnu')
    return name


def of(j):
    return j.get('config', {}).get('video_engine', 'flow')


def spec(j):
    return ENGINES.get(of(j), ENGINES['flow'])


def clip_engine(j, scene=None):
    """Engine that made this clip (0.1.93); the episode's engine for older clips."""
    engine = (scene or {}).get('engine')
    return engine if engine in ENGINES else of(j)


def clip_range(j, scene=None):
    return ENGINES.get(clip_engine(j, scene), ENGINES['flow'])['range']


def clip_length(j, actual, scene=None):
    """Montage length of one clip: Flow stays exactly 8 s; other engines keep their real duration, bounded."""
    engine = clip_engine(j, scene)
    if engine == 'flow' or engine not in ENGINES:
        return float(ENGINES['flow']['seconds'])
    low, high = ENGINES[engine]['range']
    return round(min(max(float(actual or 0), low), high), 3)


def word_limit(j, base=20):
    """Spoken words per scene scale with the clip duration (20 words for 8 s)."""
    return max(8, int(base * spec(j)['seconds'] / 8))


def words_for(engine, base=20):
    """Same rule for one engine (a clip moved to Grok has 6 s for words written for 8 s)."""
    return max(8, int(base * ENGINES[engine]['seconds'] / 8))
