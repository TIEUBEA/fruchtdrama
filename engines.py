"""Video engines (P5-06). Flow keeps its credit logic; Grok runs in the same FruchtDrama window.

0.1.93: each clip may come from another engine (bascule par clip, engine_chain.py); the montage and the quality
check then use the engine of the clip itself (scene['engine']), the scenario keeps the episode's engine.
0.1.97 (owner, 06/11/2026): only Flow and Grok are left (Arena and Vidogrid removed). New episodes use 10 s Flow
clips (« Courte · 1 min » = 7 plans de 10 s for TikTok Creator Rewards); existing episodes keep their 8 s."""

ENGINES = {
    # seconds: duration asked in the prompt; range: accepted clip duration (QC) and montage clamp.
    # Flow: 10 s for new episodes (Flow offers 4/6/8/10 s); an episode made before 0.1.97 keeps 8 s (flow_seconds).
    'flow': {'label': 'Google Flow', 'seconds': 10, 'range': (9.5, 10.5), 'home': 'https://labs.google/fx/tools/flow'},
    # Grok Imagine: its connector has no duration setting, the site makes 6 s clips.
    'grok': {'label': 'Grok Imagine', 'seconds': 10, 'range': (5.5, 15.5), 'home': 'https://grok.com/imagine'},
}
# Engines whose browser connector is available in this version.
AVAILABLE = ('flow', 'grok')
FLOW_SECONDS = (4, 6, 8, 10)  # durations offered by Flow
LEGACY_FLOW_SECONDS = 8  # episodes made before 0.1.97
# Clips already made by an engine removed in 0.1.97: their real duration is kept, bounded, at the montage.
LEGACY_RANGES = {'arena': (4.0, 10.5), 'vidogrid': (5.5, 10.5)}


def validate(name):
    name = str(name or 'flow')
    if name not in ENGINES:
        raise ValueError('Moteur vidéo inconnu')
    return name


def of(j):
    return j.get('config', {}).get('video_engine', 'flow')


def flow_seconds(j):
    """Flow clip length of this episode: 10 s since 0.1.97 (cfg flow_seconds), 8 s for older episodes."""
    cfg = j.get('config') or {}
    for value in (cfg.get('flow_seconds'), cfg.get('clip_seconds') if of(j) == 'flow' else None):
        try:
            if int(value) in FLOW_SECONDS:
                return int(value)
        except (TypeError, ValueError):
            pass
    return LEGACY_FLOW_SECONDS


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
        s = float(flow_seconds(j))
        # A longer clip replaced by hand (10 s instead of 8 s) keeps its real duration (0.1.99); shorter ones are padded.
        if actual and float(actual) > s + 0.5:
            return round(min(max(float(actual), 2.0), 16.0), 3)
        return s
    low, high = clip_range(j, scene)
    return round(min(max(float(actual or 0), low), high), 3)


def words_in(secs, base=20):
    """Spoken words for a clip of this length: 20 words for 8 s (older rule); 3 words a second from 10 s
    (owner 06/11/2026: 30 words for a 10 s plan)."""
    if secs >= 10:
        return int(3 * secs)
    return max(8, int(base * secs / 8))


def word_limit(j, base=20):
    """Spoken words per scene scale with the clip duration of the episode."""
    return words_in(spec(j)['seconds'], base)


def words_for(engine, base=20, j=None):
    """Same rule for one engine (a clip moved to Grok has 6 s for words written for 10 s)."""
    return words_in(seconds(j or {}, engine), base)
