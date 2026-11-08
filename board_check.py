"""Board check before the clips (owner, 03/11/2026, like the Atelier "Planches de la boucle complète").

ChatGPT compares the boards with the character sheet before any clip is paid. Boards are grouped five
per contact sheet (one attachment for five boards). Failing boards are redrawn once (four at most), or
only reported, following the owner's setting."""
import json

PER_SHEET = 5
MAX_REDRAW = 4


def make_sheets(folder, images, prefix='board-check'):
    """Contact sheets of the boards, numbered; returns their file names."""
    from PIL import Image, ImageDraw
    names = []
    for k in range(0, len(images), PER_SHEET):
        group = images[k:k + PER_SHEET]
        tiles = []
        for name in group:
            with Image.open(folder / name) as im:
                im = im.convert('RGB'); im.thumbnail((360, 640))
                tiles.append(im.copy())
        w, h = max(t.width for t in tiles), max(t.height for t in tiles)
        sheet = Image.new('RGB', (w * len(tiles), h + 40), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * w, 40))
            draw.text((i * w + 10, 10), f'Planche {k + i + 1}', fill='black')
        name = f'{prefix}-{k // PER_SHEET + 1}.jpg'
        sheet.save(folder / name, quality=88)
        names.append(name)
    return names


def prompt(j):
    cast = [{'id': c['id'], 'name': c.get('name'), 'appearance': c.get('appearance')} for c in j.get('characters', [])]
    scenes = [{'index': i, 'characters': s.get('characters', []), 'meaning': s.get('meaning', '')} for i, s in enumerate(j['scenes'])]
    # « Au fil de l'histoire »: a planned change of look is expected from its scene on, never a defect.
    changes = (j.get('script') or {}).get('state_changes') or []
    for scene, script_scene in zip(scenes, j['scenes']):
        for key in ('montre', 'critical_mark'):
            if script_scene.get(key):
                scene[key] = script_scene[key]
        seen = [{'character': c['character'], 'change': c['change']} for c in changes if c['from_scene'] <= scene['index'] + 1 and c['character'] in scene['characters']]
        if seen:
            scene['changed_look'] = seen
    return ('Review the attached BOARDS (numbered "Planche N", N starting at 1) against the attached character reference sheet and the script. '
            'Do not generate an image. For each board say whether it is usable for animation: same identity and outfit as the reference, '
            'only the characters of that scene (no extra character, nobody missing), no deformed body, the scene meaning and opening gesture or object readable. '
            'Flag added lettering, except a critical_mark specified for that scene. When specified, verify its exact lettering, placement and legibility. '
            + ('A "changed_look" listed for a scene is planned by the story: it is expected on that board, not an error. ' if changes else '')
            + 'Output JSON only: {"production_id": "...", "generation_task_id": "...", "board_review": {"boards": [{"index": 0, "status": "pass|issue", "detail": "short reason"}]}} '
            'with one entry per board, index starting at 0, and the exact production_id and generation_task_id given here.\n'
            + json.dumps({'production_id': j['id'], 'cast': cast, 'scenes': scenes}, ensure_ascii=False))


def validate(value, j, task):
    if not isinstance(value, dict) or value.get('production_id') != j['id'] or value.get('generation_task_id') != task:
        raise ValueError('Contrôle des planches non associé à cette tâche')
    boards = (value.get('board_review') or {}).get('boards', [])
    if [b.get('index') for b in boards] != list(range(len(j['scenes']))):
        raise ValueError('Contrôle des planches incomplet ou désordonné')
    for b in boards:
        if b.get('status') not in ('pass', 'issue') or not isinstance(b.get('detail'), str) or not b['detail'].strip():
            raise ValueError('Conclusion du contrôle des planches invalide')
    return {'boards': [{'index': b['index'], 'status': b['status'], 'detail': ' '.join(b['detail'].split())[:300]} for b in boards]}


def failing(review):
    return [b['index'] for b in (review or {}).get('boards', []) if b['status'] == 'issue']
