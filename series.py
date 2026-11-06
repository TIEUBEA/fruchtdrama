"""P3: series continuation (same cast, character images reused: nothing paid twice) and publication kit.
Pure functions; suggestions only, no virality promise."""
import json
import shutil

HASHTAGS = {
    'Deutsch (de-DE)': ['#KI', '#Früchte', '#Drama', '#Geschichte', '#Familie', '#fürdich'],
    'Français (fr-FR)': ['#IA', '#fruits', '#drame', '#histoire', '#famille', '#pourtoi'],
    'English (en-US)': ['#AI', '#fruit', '#drama', '#story', '#family', '#fyp'],
    'Español (es-ES)': ['#IA', '#frutas', '#drama', '#historia', '#familia', '#parati'],
    'Português (pt-BR)': ['#IA', '#frutas', '#drama', '#historia', '#familia', '#fyp'],
}
PART = {'Deutsch (de-DE)': 'Teil', 'Français (fr-FR)': 'Partie', 'English (en-US)': 'Part', 'Español (es-ES)': 'Parte', 'Português (pt-BR)': 'Parte'}
# Common evening/lunch slots for each market, local time. Hypotheses to test with your own statistics.
SLOTS = {
    'Deutsch (de-DE)': {'zone': 'Europe/Berlin', 'times': ['12:00', '18:00', '20:30']},
    'Français (fr-FR)': {'zone': 'Europe/Paris', 'times': ['12:30', '19:00', '21:00']},
    'English (en-US)': {'zone': 'America/New_York', 'times': ['13:00', '19:00', '21:00']},
    'Español (es-ES)': {'zone': 'Europe/Madrid', 'times': ['14:00', '20:00', '22:00']},
    'Português (pt-BR)': {'zone': 'America/Sao_Paulo', 'times': ['12:00', '19:00', '21:00']},
}


def part_of(j):
    return int(j.get('series', {}).get('part', 1))


def brief(previous, owner_note=''):
    """Brief of the next part: same main characters, direct continuation, new twist."""
    s = previous.get('script', {})
    last = (previous.get('scenes') or [{}])[-1]
    cast = [{'id': c['id'], 'name': c.get('name'), 'appearance': c.get('appearance')} for c in previous.get('characters', [])]
    lines = ' / '.join(x.get('text', '') for x in last.get('dialogue', []))
    text = (f"SUITE DIRECTE, partie {part_of(previous) + 1}, de l'épisode « {s.get('title', previous.get('title'))} ». "
            f"Garde exactement les mêmes personnages principaux (mêmes id, noms et apparences) : {json.dumps(cast, ensure_ascii=False)}. "
            f"Fin de l'épisode précédent : {last.get('meaning', '')} — dernières répliques : {lines}. "
            "Rappelle l'enjeu en une réplique dès la première seconde, ajoute une nouvelle complication, termine sur un rebondissement qui appelle la partie suivante. "
            "Aucune scène ni réplique ne doit répéter l'épisode précédent.")
    return (text + (' Idée du propriétaire : ' + owner_note if owner_note else ''))[:4000]


def inherit(j, previous, source_dir, target_dir):
    """Reuse reference images of characters kept from the previous part; returns the reused ids."""
    files = {c['id']: c.get('file') for c in previous.get('characters', []) if c.get('file')}
    reused = []
    for c in j.get('characters', []):
        name = files.get(c['id'])
        if not name or c.get('file') or not (source_dir / name).is_file():
            continue
        target = f"ref_{c['id']}_p{part_of(previous)}{(source_dir / name).suffix}"
        if not (target_dir / target).exists():
            shutil.copyfile(source_dir / name, target_dir / target)
        c['file'] = target; reused.append(c['id'])
    return reused


def kit(j):
    """Publication kit: title, description, hashtags, first comment, suggested slots."""
    language = j.get('config', {}).get('language', 'Deutsch (de-DE)')
    s = j.get('script', {})
    tags = list(HASHTAGS.get(language, HASHTAGS['English (en-US)']))
    for c in j.get('characters', [])[:2]:
        tag = '#' + ''.join(ch for ch in str(c.get('name', '')).title() if ch.isalnum())
        if len(tag) > 2 and tag not in tags:
            tags.append(tag)
    title = s.get('title', j.get('title', ''))
    if j.get('series'):
        word = PART.get(language, 'Part')
        title = f"{title} ({word} {part_of(j)})"; tags.append(f"#{word}{part_of(j)}")
    first_comment = {'Deutsch (de-DE)': 'Wie geht es weiter? Schreib deine Idee in die Kommentare!',
                     'Français (fr-FR)': 'Et ensuite ? Écris ta suite en commentaire !',
                     'English (en-US)': 'What happens next? Tell us in the comments!',
                     'Español (es-ES)': '¿Y ahora qué? ¡Escribe tu continuación en los comentarios!',
                     'Português (pt-BR)': 'E agora? Escreve a continuação nos comentários!'}.get(language, '')
    return {'title': title, 'description': s.get('description', ''), 'hashtags': tags[:10], 'first_comment': first_comment,
            'slots': SLOTS.get(language), 'files': {'video': 'final.mp4', 'cover': j.get('cover_file') or 'cover.jpg'},
            'note': 'Créneaux et hashtags : hypothèses à tester avec vos statistiques, aucune garantie de vues.'}


def kit_text(k):
    return '\n'.join([k['title'], '', k['description'], '', ' '.join(k['hashtags']), '', 'Premier commentaire : ' + k['first_comment'],
                      'Créneaux suggérés (' + k['slots']['zone'] + ') : ' + ', '.join(k['slots']['times']) if k.get('slots') else '', '', k['note']])
