"""Motion direction and short dissolves that preserve dialogue and caption timing."""


def direction(scenes, index):
    scene = scenes[index]
    previous = scenes[index - 1].get('meaning', '') if index else ''
    following = scenes[index + 1].get('meaning', '') if index + 1 < len(scenes) else ''
    return (
        '\nPHYSICAL ACTION: Start the action within the first half-second, from the supplied pose. '
        'Carry out the concrete action described below: visible steps towards a person or object, '
        'turning, reaching, carrying or handing over an object as appropriate to the story. '
        'Show a clear change in body position, not just blinking, moving lips or a camera zoom. '
        'Start the exact dialogue promptly and sustain it at a natural pace. Keep faces readable while speaking; do not force walking in a tight close-up. '
        'Use one simple, achievable movement rather than many simultaneous actions. '
        'The camera follows the physical action; a camera move never replaces character movement. '
        'Finish with a natural gesture or eyeline that leads into the next scene. '
        'Preserve screen direction, prop ownership and spatial relationships; no teleporting, '
        'crossing through furniture or new invented dialogue. '
        f'Current action: {scene.get("meaning", "")}. '
        f'Previous scene context (do not reenact): {previous or "Opening scene"}. '
        f'Next scene context (prepare the handoff, do not enact yet): {following or "Final resolution"}.\n'
    )


def dissolve_graph(lengths, duration=0.2):
    """Hold outgoing last frame over the incoming opening; never overlap speech.

    The next clip starts at its original timeline offset. Padding outgoing video
    supplies the overlap, so the total duration and every caption offset stay intact.
    Audio is concatenated at its original boundaries, without losing syllables.
    """
    if len(lengths) < 2 or any(x <= 0 for x in lengths):
        raise ValueError('At least two positive clip lengths required')
    duration = min(duration, min(lengths) / 4)
    parts = []
    for i in range(len(lengths)):
        padding = f',tpad=stop_mode=clone:stop_duration={duration:.6f}' if i < len(lengths) - 1 else ''
        parts.append(f'[{i}:v]settb=AVTB,setpts=PTS-STARTPTS{padding}[v{i}]')
    elapsed = 0
    current = 'v0'
    for i in range(1, len(lengths)):
        elapsed += lengths[i - 1]
        parts.append(f'[{current}][v{i}]xfade=transition=fade:duration={duration:.6f}:offset={elapsed:.6f}[x{i}]')
        current = f'x{i}'
    parts.append(f'[{current}]ass=subtitles.ass[vout]')
    parts.append(''.join(f'[{i}:a]' for i in range(len(lengths))) + f'concat=n={len(lengths)}:v=0:a=1,loudnorm=I=-14:TP=-1.5:LRA=11[aout]')
    return ';'.join(parts)
