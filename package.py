"""Build the zip sent to testers and trainees: only what they need, nothing private.

Allowlist of git-tracked files (never data/, accounts, sessions, internal notes or tests), one top folder
"FruchtDrama/" so unzipping gives a ready folder. Refuses to build if a real e-mail address slipped in.
Usage: python3 package.py [destination.zip]
"""
import pathlib
import re
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
TOP = 'FruchtDrama'
INCLUDE = re.compile(r'^(?:[a-z_]+\.py|requirements(?:-quality)?\.txt|[A-Za-z-]+\.(?:cmd|sh)|README\.md|INSTALLATION\.md|CHANGELOG\.md|CONDITIONS-UTILISATION\.txt'
                     r'|extension/.+|web/.+|docs/MODE-EMPLOI\.md|docs/GUIDE-UTILISATEUR\.pdf)$')
# The illustrated guide sits at the top of the folder, where a trainee looks first.
RENAME = {'docs/GUIDE-UTILISATEUR.pdf': 'GUIDE-UTILISATEUR.pdf'}
EXCLUDE = re.compile(r'(?:^|/)(?:tests?|data|__pycache__)/|^package\.py$')
# Placeholder addresses used in help texts are fine; anything else looks like a real account.
PLACEHOLDERS = {'adresse@gmail.com', 'moi@gmail.com', 'x@gmail.com', 'nom@gmail.com', 'exemple@gmail.com'}
EMAIL = re.compile(rb'[A-Za-z0-9._%+-]+@(?:gmail|googlemail|outlook|hotmail|yahoo|icloud)\.[a-z]{2,}', re.I)


def files():
    tracked = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    return sorted(f for f in tracked if INCLUDE.match(f) and not EXCLUDE.search(f))


def private_addresses(names):
    found = {}
    for name in names:
        if name.endswith('.pdf'):
            continue  # checked as text by the test (pdftotext); screenshots are redacted by hand
        for m in EMAIL.findall((ROOT / name).read_bytes()):
            if m.decode().lower() not in PLACEHOLDERS:
                found.setdefault(name, set()).add(m.decode())
    return found


def build(dest):
    names = files()
    leaks = private_addresses(names)
    if leaks:
        raise SystemExit('Adresse(s) réelle(s) trouvée(s), zip non créé : ' + '; '.join(f'{k}: {", ".join(sorted(v))}' for k, v in leaks.items()))
    dest = pathlib.Path(dest)
    tmp = dest.with_suffix('.tmp')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in names:
            info = zipfile.ZipInfo.from_file(ROOT / name, f'{TOP}/{RENAME.get(name, name)}')
            if name.endswith('.sh'):
                info.external_attr = 0o100755 << 16  # Linux/macOS: scripts stay executable
            z.writestr(info, (ROOT / name).read_bytes(), zipfile.ZIP_DEFLATED)
    tmp.replace(dest)
    return names


if __name__ == '__main__':
    version = re.search(r"VERSION='([^']+)'", (ROOT / 'server.py').read_text('utf-8')).group(1)
    out = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / f'FruchtDrama-{version}.zip')
    names = build(out)
    print(f'{out} : {len(names)} fichiers')
