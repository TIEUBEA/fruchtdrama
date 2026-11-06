"""Temps passé par étape d'un épisode, à comparer à l'Atelier (docs/sudf/TEMPS-ATELIER.md).

Usage : python tools/temps_etapes.py <id d'épisode (début suffit)>
"""
import datetime as dt, json, re, sys
from pathlib import Path

ATELIER = {'source': 120, 'script': 560, 'characters': 80, 'images': 1500}
ATELIER_PER_IMAGE = 1500 / 17
LABEL = {'source': 'Récupération de la vidéo', 'script': 'Scénario (fiche + plans + corrections)',
         'characters': 'Feuille de personnages', 'images': 'Planches', 'clips': 'Clips',
         'edit': 'Montage', 'cover': 'Miniature'}


def step_of(text):
    m = re.match(r'Tâche préparée : (\w+)', text)
    if m:
        return {'image': 'images', 'clip': 'clips'}.get(m.group(1), m.group(1))
    if text.startswith('Montage local démarré'):
        return 'edit'
    return None


def durations(job):
    out, cur, start = {}, None, None
    events = job.get('events') or []
    if events:
        cur, start = 'source', events[0]['at']
    for e in events:
        step = step_of(e['text'])
        if step and step != cur:
            if cur:
                out[cur] = out.get(cur, 0) + (stamp(e['at']) - stamp(start))
            cur, start = step, e['at']
    if cur and events:
        out[cur] = out.get(cur, 0) + (stamp(events[-1]['at']) - stamp(start))
    return out


def stamp(at):
    return dt.datetime.fromisoformat(at).timestamp()


def mmss(s):
    return f'{int(s // 60)} min {int(s % 60):02d}' if s is not None else '—'


def main():
    state = json.loads((Path(__file__).resolve().parent.parent / 'data' / 'state.json').read_text())
    job = next(j for j in state['jobs'] if j['id'].startswith(sys.argv[1]))
    got = durations(job)
    print(f"{'Étape':40} {'FruchtDrama':>12} {'Atelier':>12}  écart")
    for k, v in got.items():
        ref = ATELIER.get(k)
        gap = f'{(v - ref) / ref:+.0%}' if ref else ''
        print(f'{LABEL.get(k, k):40} {mmss(v):>12} {mmss(ref):>12}  {gap}')
    n = sum(1 for e in job.get('events') or [] if e['text'].startswith('Média reçu : image_'))
    if n and got.get('images'):
        per = got['images'] / n
        print(f"{'  par planche':40} {mmss(per):>12} {mmss(ATELIER_PER_IMAGE):>12}  {(per - ATELIER_PER_IMAGE) / ATELIER_PER_IMAGE:+.0%}")


if __name__ == '__main__':
    main()
