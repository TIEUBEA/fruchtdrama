"""Video engines (P5-06). Flow keeps its credit logic; Grok runs in the same FruchtDrama window.

0.1.93: each clip may come from another engine (bascule par clip, engine_chain.py); the montage and the quality
check then use the engine of the clip itself (scene['engine']), the scenario keeps the episode's engine.

Moteur V09 (owner, 09/11/2026, same rules as fruit-france/MOTEUR.md): Flow, Grok and Vidogrid (Arena removed,
never brought back). Flow makes its clips with Omni 1.2 Flash, 720p, 9:16, 10 s (30 credits); Grok makes
clip 1 only, in 10 s; Vidogrid gets one or two tries when Flow refuses a scene. Episodes made with an older Flow model keep their 8 s clips.
"""

ENGINES = {
    # seconds: duration asked in the prompt; range: accepted clip duration (QC) and montage clamp.
    'flow': {'label': 'Google Flow', 'seconds': 8, 'range': (7.5, 8.5), 'home': 'https://labs.google/fx/tools/flow'},
    # Grok Imagine: « Video duration » menu (6s / 10s / 15s); 10 s like the Flow clips of the V09 engine.
    'grok': {'label': 'Grok Imagine', 'seconds': 10, 'range': (5.5, 10.5), 'home': 'https://grok.com/imagine'},
    # vidogrid.ai, model « Grok Imagine Video 1.5 Lite », 10 s in 720p: third option when Flow refuses a scene (owner 09/11/2026).
    'vidogrid': {'label': 'Vidogrid (Grok Lite)', 'seconds': 10, 'range': (5.5, 10.5), 'home': 'https://vidogrid.ai/app/video-gen/grok'},
}
# Engines whose browser connector is available in this version.
AVAILABLE = ('flow', 'grok', 'vidogrid')
# Clips already made by an engine removed with the V09 engine: their real duration is kept, bounded, at the montage.
LEGACY_RANGES = {'arena': (4.0, 10.5)}

# Flow models: Omni 1.2 Flash is the V09 engine model (10 s, 30 credits for 10 s); the others make 8 s clips.
OMNI_12 = 'gemini_omni_flash_1_2'
FLOW_MODELS = {
    OMNI_12: {'label': 'Omni 1.2 Flash', 'seconds': 10, 'costs': (30,)},
    'gemini_omni_flash': {'label': 'Omni 1.1 Flash', 'seconds': 8, 'costs': (12,)},
    'veo_3_1_lite': {'label': 'Veo 3.1 Lite', 'seconds': 8, 'costs': (10, 5)},
    'veo_3_1_fast': {'label': 'Veo 3.1 Fast', 'seconds': 8, 'costs': (20, 10)},
    'veo_3_1_quality': {'label': 'Veo 3.1 Quality', 'seconds': 8, 'costs': (100,)},
}
DEFAULT_FLOW_MODEL = OMNI_12
# Models that generate in native 720p (a 1080p request is brought back to 720p before sending).
NATIVE_720 = (OMNI_12, 'gemini_omni_flash', 'veo_3_1_lite')


def validate(name):
    name = str(name or 'flow')
    if name not in ENGINES:
        raise ValueError('Moteur vidéo inconnu')
    return name


def of(j):
    return j.get('config', {}).get('video_engine', 'flow')


def flow_seconds(j):
    """Flow clip length of this episode: 10 s with Omni 1.2 Flash (V09 engine), 8 s with the older models."""
    model = (j.get('config') or {}).get('flow_model')
    return FLOW_MODELS.get(model, {}).get('seconds', ENGINES['flow']['seconds'])


def seconds(j, engine):
    """Clip length asked of this engine for this episode."""
    if engine == 'flow':
        return flow_seconds(j)
    return ENGINES.get(engine, ENGINES['grok'])['seconds']


def spec(j):
    engine = of(j) if of(j) in ENGINES else 'flow'
    return {**ENGINES[engine], 'seconds': seconds(j, engine)}


def clip_engine(j, scene=None):
    """Engine that made this clip (0.1.93); the episode's engine for older clips."""
    engine = (scene or {}).get('engine')
    return engine if engine in ENGINES or engine in LEGACY_RANGES else of(j)


def clip_range(j, scene=None):
    engine = clip_engine(j, scene)
    if engine in LEGACY_RANGES:
        return LEGACY_RANGES[engine]
    if engine == 'flow' or engine not in ENGINES:
        s = flow_seconds(j)
        return (s - 0.5, s + 0.5)
    return ENGINES[engine]['range']


def clip_length(j, actual, scene=None):
    """Montage length of one clip: Flow stays exactly its length (8 or 10 s); other engines keep their real duration, bounded."""
    engine = clip_engine(j, scene)
    if engine not in LEGACY_RANGES and (engine == 'flow' or engine not in ENGINES):
        return float(flow_seconds(j))
    low, high = clip_range(j, scene)
    return round(min(max(float(actual or 0), low), high), 3)


MAX_DIALOGUE_TURNS = 3


def words_in(secs, base=24):
    """Spoken words for a clip of this length (24 words for 8 s, 30 for 10 s: 3 words a second, V09 engine)."""
    return max(8, int(base * secs / 8))


def word_limit(j, base=24):
    """Spoken words per scene scale with the clip duration (24 words for 8 s)."""
    return words_in(spec(j)['seconds'], base)


def words_for(engine, base=24, j=None):
    """Same rule for one engine (a clip moved to another engine keeps the words written for the episode's clips)."""
    return words_in(seconds(j or {}, engine), base)
