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
import native_setup

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


def start_server(detached=False):
    """Start this copy's studio unless it already answers. detached=True: the server outlives its caller
    (the Chrome native host is killed when the extension disconnects)."""
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
            spawn([sys.executable, str(ROOT / 'server.py')], cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, detached=detached)
        for _ in range(80):
            if server_matches():
                break
            time.sleep(.25)
    if not server_matches():
        raise RuntimeError('Demarrage impossible. Consultez data/server-errors.log.')


def spawn(cmd, detached=False, **kw):
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    if os.name == 'nt' and detached:
        flags |= subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            # Chrome runs native hosts in a job object: break away so closing Chrome does not stop the studio.
            return subprocess.Popen(cmd, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kw)
        except OSError:
            pass
        return subprocess.Popen(cmd, creationflags=flags, **kw)
    return subprocess.Popen(cmd, creationflags=flags, start_new_session=detached, **kw)


def main():
    accept_terms()
    try:
        native_setup.register()  # follows the folder if it was moved; never blocks the launch
    except OSError:
        pass
    start_server()
    if not os.environ.get('FRUCHT_NO_BROWSER'):webbrowser.open(ADDRESS)  # Linux script opens the dedicated Chrome instead
    print('Studio ouvert. Laissez le PC et Chrome en marche pendant la production.')


if __name__ == '__main__':
    main()
