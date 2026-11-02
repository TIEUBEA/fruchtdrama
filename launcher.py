"""Visible console launcher; validates local ownership before reusing a server."""
import json
import os
import pathlib
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from distribution import accept_terms

ROOT = pathlib.Path(__file__).resolve().parent
ADDRESS = 'http://127.0.0.1:8840'


def server_matches():
    state_file = ROOT / 'data' / 'state.json'
    if not state_file.is_file():
        return False
    try:
        # Compare in memory only; never print or export pairing codes.
        local = json.loads(state_file.read_text('utf-8'))
        with urllib.request.urlopen(ADDRESS + '/api/state', timeout=1) as r:
            remote = json.load(r)
        return bool(local.get('pair_code')) and remote.get('pair_code') == local['pair_code']
    except (OSError, ValueError):
        return False


def main():
    accept_terms()
    if not server_matches():
        with socket.socket() as probe:
            occupied = probe.connect_ex(('127.0.0.1', 8840)) == 0
        if occupied:
            raise RuntimeError('Port 8840 utilise par une autre installation. Fermez son serveur avant de lancer cette copie. Aucun compte existant ne sera reutilise.')
        logs = ROOT / 'data'
        logs.mkdir(exist_ok=True)
        env = os.environ.copy()
        env['FRUCHT_DATA'] = str(logs)
        env['FRUCHT_PORT'] = '8840'
        with (logs / 'server.log').open('a', encoding='utf-8') as out, (logs / 'server-errors.log').open('a', encoding='utf-8') as err:
            subprocess.Popen([sys.executable, str(ROOT / 'server.py')], cwd=ROOT, env=env, stdout=out, stderr=err, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for _ in range(60):
            if server_matches():
                break
            time.sleep(.25)
    if not server_matches():
        raise RuntimeError('Demarrage impossible. Consultez data/server-errors.log.')
    if not os.environ.get('FRUCHT_NO_BROWSER'):webbrowser.open(ADDRESS)  # Linux script opens the dedicated Chrome instead
    print('Studio ouvert. Laissez le PC et Chrome en marche pendant la production.')


if __name__ == '__main__':
    main()
