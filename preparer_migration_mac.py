"""Migration vers Mac (propriétaire, 11/11/2026) : prépare deux archives à copier sur le MacBook.

  FruchtDrama-Mac-code.zip     le studio et l'extension (sans .venv, modèles ni fichiers propres à Windows)
  FruchtDrama-Mac-donnees.zip  le dossier data : épisodes, vidéos, comptes, réglages, sauvegardes

L'état du studio est adapté au Mac, sans toucher à l'original de ce PC :
  - les fenêtres Chrome de ce PC (passerelles appairées) sont oubliées : celles du Mac s'appaireront seules ;
  - chaque compte Flow garde son adresse, son solde et son historique, mais plus sa place dans les profils Chrome
    de ce PC : la détection des comptes sur le Mac la retrouve ;
  - les tâches en attente sont annulées et les productions en cours mises en pause : rien ne part tant que
    les comptes du Mac ne sont pas connectés.
Aucun mot de passe ni cookie n'est copié (les sessions Google, ChatGPT et Grok se refont sur le Mac).

Usage :  .venv\\Scripts\\python.exe preparer_migration_mac.py [dossier de sortie] [--sans-sauvegardes]
"""
import datetime as dt
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
SKIP_DIRS = {'.venv', '.qc-runtime', '.qc-models', '__pycache__', '.git', 'data', 'work', 'node_modules', '.pytest_cache'}
SKIP_SUFFIXES = {'.pyc', '.zip', '.bak'}
STORED = {'.mp4', '.webm', '.mov', '.png', '.jpg', '.jpeg', '.webp', '.zip', '.mp3', '.m4a', '.wav'}
DATA_SKIP = {'state.tmp', 'server.log', 'server-errors.log', 'server.stderr.log', 'server.stdout.log',
             'server-0.1.96.log', 'server-0.1.96-errors.log', 'com.fruchtdrama.studio.json'}
RUNNING = ('running', 'waiting_quota', 'waiting_credit', 'waiting_account', 'waiting_night', 'waiting_review', 'waiting_source', 'rendering')


def for_mac(state):
    """Copy of the studio state with this PC's browser bindings removed (pure: the original is not modified)."""
    s = json.loads(json.dumps(state))
    s['clients'] = {}
    for key in ('bridge_requests', 'bridge_notice', 'refill_requested'):
        s.pop(key, None)
    s['bridge_requests'] = []
    for p in s.get('profiles', []):
        for key in ('flow_client', 'chrome_profile', 'readiness', 'credit_probe', 'credit_error', 'credit_next_check'):
            p.pop(key, None)
        p['slot'] = None
        p['auto_enabled'] = False  # back in rotation when the Mac's account detection finds it
    for a in s.get('engine_accounts', []):
        for key in ('client', 'readiness'):
            a.pop(key, None)
    for t in s.get('tasks', []):
        if t.get('status') in ('queued', 'claimed'):
            t['status'] = 'cancelled'
            t['error'] = 'Annulée pour la migration vers le Mac (aucun envoi en cours repris).'
    moved = dt.datetime.now(dt.timezone.utc).isoformat()
    for j in s.get('jobs', []):
        if j.get('status') in RUNNING:
            j['status'] = 'paused'
            j.setdefault('events', []).append({'at': moved, 'text': 'Migration vers le Mac : production mise en pause. Connecte tes comptes sur le Mac, puis clique sur Reprendre.'})
    night = s.get('night')
    if isinstance(night, dict):
        night['active'] = False
    s['migrated_from'] = {'platform': sys.platform, 'at': moved}
    return s


def zip_code(target):
    count = 0
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for path in sorted(ROOT.rglob('*')):
            rel = path.relative_to(ROOT)
            if any(part in SKIP_DIRS for part in rel.parts) or not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
                continue
            info = zipfile.ZipInfo.from_file(path, 'fruchtdrama-studio/' + rel.as_posix())
            if path.suffix in ('.sh', '.command'):
                info.external_attr = (0o100755 << 16)  # executable on the Mac
            info.compress_type = zipfile.ZIP_STORED if path.suffix.lower() in STORED else zipfile.ZIP_DEFLATED
            z.writestr(info, path.read_bytes())
            count += 1
    return count


def zip_data(target, backups=True, data=None):
    data = pathlib.Path(data or ROOT / 'data')
    state = json.loads((data / 'state.json').read_text('utf-8'))
    count = size = 0
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        z.writestr('fruchtdrama-studio/data/state.json', json.dumps(for_mac(state), ensure_ascii=False, indent=1))
        for path in sorted(data.rglob('*')):
            rel = path.relative_to(data)
            if not path.is_file() or rel.as_posix() == 'state.json' or rel.name in DATA_SKIP:
                continue
            if not backups and rel.parts[0] in ('backups',):
                continue
            kind = zipfile.ZIP_STORED if path.suffix.lower() in STORED else zipfile.ZIP_DEFLATED
            z.write(path, 'fruchtdrama-studio/data/' + rel.as_posix(), compress_type=kind)
            count += 1
            size += path.stat().st_size
    return count, size


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    out = pathlib.Path(args[0]) if args else ROOT.parent / 'FruchtDrama-pour-Mac'
    out.mkdir(parents=True, exist_ok=True)
    code = out / 'FruchtDrama-Mac-code.zip'
    files = zip_code(code)
    print(f'Code : {files} fichiers -> {code}')
    data = out / 'FruchtDrama-Mac-donnees.zip'
    count, size = zip_data(data, backups='--sans-sauvegardes' not in argv)
    print(f'Données : {count} fichiers ({size / 1e9:.1f} Go) -> {data}')
    print('Copie ces deux fichiers sur le Mac, puis suis MIGRATION-MAC.md.')


if __name__ == '__main__':
    main(sys.argv[1:])
