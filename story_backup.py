"""Story backups (owner, 03/11/2026, like the Atelier "Mes sauvegardes").

After each fabrication the story is copied outside the studio folder: text, characters, boards, cover.
Clips and the final video are left out (heavy, and remade from the boards). "Remettre des histoires"
brings back the stories missing from the studio, paused, so nothing is spent before the owner resumes."""
import json, pathlib, re, shutil, unicodedata

VOLATILE = ('final', 'qc', 'quality_report', 'publication', 'uncertain_clips', 'last_error')
TEXTS = ('scenario.json', 'description.txt', 'publication.txt', 'cover.jpg')
AFTER_BOARDS = ('clips', 'quality', 'render', 'done')


def folder_name(j):
    plain = unicodedata.normalize('NFKD', str(j.get('title') or 'histoire')).encode('ascii', 'ignore').decode()  # « Été » → « Ete »
    slug = re.sub(r'[^a-z0-9]+', '-', plain.lower()).strip('-')[:40] or 'histoire'
    return f"{slug}-{j['id']}"


def files_of(j):
    names = [j.get('character_sheet_file'), j.get('cover_file')]
    names += [c.get('file') for c in j.get('characters', [])] + [s.get('image') for s in j.get('scenes', [])]
    return [n for n in dict.fromkeys(list(names) + list(TEXTS)) if n and pathlib.PurePath(n).name == n]


def save(j, source, root):
    """Copy one story into root/<title>-<id>/; returns the folder, or None if there is nothing to keep."""
    if not j.get('script') and not j.get('sheet') and not j.get('characters'):
        return None
    target = pathlib.Path(root) / folder_name(j)
    # One folder per story: a renamed story moves its folder instead of leaving a second copy.
    earlier = [p for p in pathlib.Path(root).glob(f"*-{j['id']}") if p != target and p.is_dir()]
    if earlier and not target.exists():
        earlier[0].rename(target)
    target.mkdir(parents=True, exist_ok=True)
    for name in files_of(j):
        if (pathlib.Path(source) / name).is_file():
            shutil.copyfile(pathlib.Path(source) / name, target / name)
    story = {k: v for k, v in j.items() if k not in VOLATILE}
    (target / 'histoire.json').write_text(json.dumps(story, ensure_ascii=False, indent=2), 'utf-8')
    return target


def listing(root):
    root = pathlib.Path(root)
    return sorted(p for p in root.glob('*/histoire.json')) if root.is_dir() else []


def restore(root, known_ids, job_dir, stamp):
    """Stories of root whose id is not in the studio, ready to insert; files copied with job_dir(job)."""
    out = []
    for path in listing(root):
        try:
            j = json.loads(path.read_text('utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(j, dict) or not re.fullmatch(r'[0-9a-f]{16}', str(j.get('id', ''))) or j['id'] in known_ids:
            continue
        j['scenes'] = [{k: v for k, v in s.items() if k != 'clip'} for s in j.get('scenes', [])]
        if j.get('stage') in AFTER_BOARDS:
            j['stage'] = 'clips'
        j['status'] = 'paused'
        j['updated'] = stamp
        j.setdefault('events', []).append({'at': stamp, 'text': 'Histoire remise depuis la sauvegarde : en pause, rien n’est envoyé avant « Reprendre ».'})
        target = job_dir(j)
        for name in files_of(j):
            if (path.parent / name).is_file():
                shutil.copyfile(path.parent / name, target / name)
        out.append(j)
        known_ids = set(known_ids) | {j['id']}
    return out
