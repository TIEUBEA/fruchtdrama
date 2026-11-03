"""Atelier-like story start: ten proposed stories, then a decision sheet the owner validates.

Nothing is paid before the sheet is validated: both steps only use the owner's ChatGPT/Claude text
quota. Pure functions (prompts, validation, brief); the server schedules the tasks.
"""
import json

IDEA_COUNT = 10
SHEET_FIELDS = ('logline', 'engine', 'obstacle', 'twist', 'image', 'question')
SHEET_LABELS = {'logline': "L'histoire en une phrase", 'engine': 'Moteur', 'obstacle': 'Obstacle',
                'twist': 'Twist', 'image': "Ce qu'on voit en une image", 'question': 'La question du spectateur'}


def _text(value, limit):
    return ' '.join(str(value or '').split())[:limit]


def trends(jobs, limit=12):
    """Titles of the most viewed Filon videos: inspiration only, never copied."""
    rows = [c for j in jobs if j.get('filon_only') for c in j.get('candidates', [])]
    rows.sort(key=lambda c: c.get('views') or 0, reverse=True)
    seen, out = set(), []
    for c in rows:
        title = _text(c.get('title'), 120)
        if title and title not in seen:
            seen.add(title)
            out.append(title)
        if len(out) >= limit:
            break
    return out


def ideas_prompt(language, niche, trend_titles, extra='', avoid=()):
    schema = {'ideas': [{'title': 'Titre court', 'pitch': 'Une phrase : qui, quoi, quel danger, quelle échéance',
                         'why': 'Pourquoi ça accroche (une phrase)'}]}
    return f"""Propose exactement {IDEA_COUNT} histoires ORIGINALES et très différentes pour une vidéo verticale courte de la niche « {niche} » (fruits anthropomorphes en animation 3D).
Langue de tous les textes : {language}. Réponds UNIQUEMENT avec du JSON valide, sans explication, clés techniques en anglais.
Chaque histoire : un enfant ou un personnage attachant, une injustice ou un danger visible dès la première image, une échéance, un secret ou un retournement, une suite possible.
Titres viraux observés aujourd'hui (tendance seulement, ne jamais les copier) : {json.dumps(list(trend_titles), ensure_ascii=False)}.
Histoires déjà faites à éviter : {json.dumps(list(avoid), ensure_ascii=False)}.
{('Consigne du propriétaire : ' + extra) if extra else ''}
Schéma : {json.dumps(schema, ensure_ascii=False)}"""


def validate_ideas(data):
    rows = data.get('ideas') if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError('Liste d’histoires absente')
    ideas = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        idea = {'title': _text(r.get('title'), 80), 'pitch': _text(r.get('pitch'), 600), 'why': _text(r.get('why'), 300)}
        if idea['title'] and idea['pitch']:
            ideas.append(idea)
    if len(ideas) < 6:
        raise ValueError('Moins de six histoires exploitables dans la réponse')
    return ideas[:IDEA_COUNT]


def sheet_prompt(language, idea, scene_count, seconds, note='', previous=None):
    schema = {'logline': 'Une phrase', 'engine': 'Ce que veut le héros', 'obstacle': 'Ce qui l’en empêche',
              'twist': 'Le retournement', 'image': "Ce qu'on voit en une image (la vignette)",
              'question': 'La question que se pose le spectateur', 'titles': ['Titre 1', 'Titre 2', 'Titre 3'],
              'hooks': ['Première réplique 1', 'Première réplique 2', 'Première réplique 3'],
              'end_call': 'Appel de fin : abonnement et commentaire (choix 1 ou 2)',
              'cast': [{'name': 'Prénom', 'role': 'protagoniste | témoin | antagoniste', 'appearance': 'Fruit, âge, tenue'}]}
    revision = ''
    if previous:
        revision = f"\nFiche précédente : {json.dumps(previous, ensure_ascii=False)}\nRemarques du propriétaire à appliquer : {note}"
    elif note:
        revision = '\nConsigne du propriétaire : ' + note
    return f"""Écris la fiche de décision d'une mini-fiction ORIGINALE de fruits anthropomorphes, avant tout dessin.
Idée : {idea}
Vidéo verticale de {scene_count} plans de {seconds} secondes, 2 à 5 personnages, plusieurs lieux. Langue de tous les textes : {language}.
Titres en 2 à 4 mots, en majuscules. Premières répliques : une phrase choc de 10 mots au plus, dite dans les 2 premières secondes par un personnage à l'écran (c'est le hook : danger, injustice ou secret, jamais une présentation).
Réponds UNIQUEMENT avec du JSON valide, sans explication, clés techniques en anglais.{revision}
Schéma : {json.dumps(schema, ensure_ascii=False)}"""


def validate_sheet(data):
    if not isinstance(data, dict):
        raise ValueError('Fiche de décision absente')
    sheet = {k: _text(data.get(k), 500) for k in SHEET_FIELDS}
    missing = [SHEET_LABELS[k] for k in SHEET_FIELDS if not sheet[k]]
    if missing:
        raise ValueError('Fiche incomplète : ' + ', '.join(missing))
    for key, label in (('titles', 'titres'), ('hooks', 'premières répliques')):
        values = [_text(v, 160) for v in data.get(key) or [] if _text(v, 160)]
        if not values:
            raise ValueError('Fiche sans ' + label)
        sheet[key] = values[:3]
    sheet['end_call'] = _text(data.get('end_call'), 300)
    cast = []
    for c in data.get('cast') or []:
        if isinstance(c, dict) and _text(c.get('name'), 40):
            cast.append({'name': _text(c.get('name'), 40), 'role': _text(c.get('role'), 40), 'appearance': _text(c.get('appearance'), 200)})
    if not cast:
        raise ValueError('Fiche sans casting')
    sheet['cast'] = cast[:5]
    return sheet


def apply_edits(sheet, edits):
    """Owner corrections from the page; only known text fields, same limits."""
    out = dict(sheet)
    for k in SHEET_FIELDS + ('end_call',):
        if k in (edits or {}):
            out[k] = _text(edits[k], 500) or sheet.get(k, '')
    if isinstance((edits or {}).get('cast'), list):
        names = [_text(c.get('name'), 40) for c in edits['cast'] if isinstance(c, dict)]
        out['cast'] = [{**c, 'name': n or c['name']} for c, n in zip(sheet['cast'], names + [''] * len(sheet['cast']))]
    return out


def brief(sheet, title_index=0, hook_index=0):
    """The validated sheet becomes the brief of the script step."""
    title = sheet['titles'][min(max(int(title_index), 0), len(sheet['titles']) - 1)]
    hook = sheet['hooks'][min(max(int(hook_index), 0), len(sheet['hooks']) - 1)]
    cast = '; '.join(f"{c['name']} ({c['role']}) : {c['appearance']}" for c in sheet['cast'])
    return (f"Fiche validée par le propriétaire. Titre : {title}. Histoire : {sheet['logline']} Moteur : {sheet['engine']} "
            f"Obstacle : {sheet['obstacle']} Twist : {sheet['twist']} Image d'ouverture : {sheet['image']} "
            f"Question du spectateur : {sheet['question']} La toute première réplique de la scène 1 est exactement : « {hook} ». "
            f"Casting : {cast}." + (f" La dernière scène se termine par cet appel : « {sheet['end_call']} »." if sheet.get('end_call') else ''))
