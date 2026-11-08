"""Routing of explicitly registered, already authenticated Flow sessions."""
import datetime as dt
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.parse

import flow_refill


def project_url(value):
    u = urllib.parse.urlsplit(str(value))
    if u.scheme != 'https' or u.hostname not in ('flow.google.com', 'labs.google') or u.username or u.password or u.port or u.query or u.fragment:
        raise ValueError('Adresse de projet Flow invalide')
    match = re.fullmatch(r'((?:/u/\d+)?/project/[a-zA-Z0-9_-]+)(?:/edit/[a-zA-Z0-9_-]+)?/?', u.path)
    if not match:
        raise ValueError('Ouvrez un projet Flow avant de mémoriser ce compte')
    return urllib.parse.urlunsplit(('https', u.hostname, match[1], '', ''))


def route(profile):
    if not profile or not profile.get('auto_enabled') or profile.get('blocked'):
        return None
    if not profile.get('flow_client') or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', profile.get('flow_email', '')):
        return None
    try:
        url = project_url(profile.get('flow_url', ''))
    except ValueError:
        return None
    return {'url': url, 'email': profile['flow_email'], 'client': profile['flow_client']}


def account_home(value):
    u=urllib.parse.urlsplit(project_url(value))
    prefix=u.path.split('/project/')[0]
    return urllib.parse.urlunsplit(('https',u.hostname,prefix+'/', '', ''))


def at_slot(value,slot):
    u=urllib.parse.urlsplit(project_url(value))
    path=re.sub(r'^(?:/u/\d+)?/project/',f'/u/{int(slot)}/project/',u.path)
    return urllib.parse.urlunsplit(('https',u.hostname,path,'',''))


def seen_ago(client, now):
    try:return now-dt.datetime.fromisoformat(client.get('seen') or '').timestamp()
    except (TypeError,ValueError):return None


def follow_active_browser(state, now=None, quiet=180):
    """Flow accounts tied to a browser that is gone, switched off or silent follow the one working browser.

    The accounts live in the FruchtDrama window's Chrome profile, not in a pairing: after the extension is
    reinstalled or reloaded (new pairing) they must not stay bound to the old one (real case 03/11/2026).
    Only when exactly one automatic browser works, so a multi-browser setup is never rewired by guess.
    Real case 06/11/2026: the old pairing was never switched off (it held a task when the new one paired),
    two « working » browsers were counted and the accounts stayed on the old one, silent since: when several
    are switched on, only the ones heard from in the last `quiet` seconds count, and a silent automatic
    pairing is treated as gone.
    """
    now=time.time() if now is None else now
    clients = state.get('clients', {})
    active = [c for c in clients.values() if c.get('auto') and not c.get('disabled') and c.get('role') in ('all', 'flow')]
    if len(active) > 1:
        active = [c for c in active if (seen_ago(c, now) if seen_ago(c, now) is not None else 1e9) < quiet]
    if len(active) != 1 or active[0].get('role') != 'all':
        return 0
    def gone(bound):
        if bound and bound.get('role') == 'flow':
            return False
        if not bound or bound.get('disabled'):return True
        ago=seen_ago(bound, now)
        return bool(bound.get('auto')) and bound is not active[0] and (ago is None or ago >= quiet)
    moved = 0
    for p in state.get('profiles', []):
        if p.get('flow_client') and p['flow_client'] != active[0]['id'] and gone(clients.get(p.get('flow_client'))):
            p['flow_client'] = active[0]['id']
            moved += 1
    return moved


def eligible(state, p):
    """Accounts detected in the window carry their slot; older registrations stay usable only if routed."""
    client = state.get('clients', {}).get(p.get('flow_client'), {})
    return bool(route(p)) and client.get('role') in ('all', 'flow') and not client.get('disabled') and not offline_route(state,p)


def offline_route(state,p,now=None):
    """Old silent pairings must not occupy parallel slots when a working window is available.
    Never transfer another Chrome's accounts without detecting their identity there."""
    now=time.time() if now is None else now
    clients=state.get('clients',{});bound=clients.get(p.get('flow_client'),{})
    ago=seen_ago(bound,now)
    if not bound.get('seen') or (not bound.get('disabled') and ago is not None and ago<180):return False
    return any(c is not bound and not c.get('disabled') and c.get('role') in ('all','flow')
        and seen_ago(c,now) is not None and seen_ago(c,now)<180 for c in clients.values())


def usable(p):
    """Not marked « À régler » or « Pas d'accès » by « Préparer mes comptes » or by a page that did not open (0.1.91)."""
    return (p.get('readiness') or {}).get('state') not in ('fix', 'no_access')


def choose(state, current, cost, exclude=()):
    """Never reset balances, switch an active task, or use unregistered accounts.

    exclude: accounts already working on another clip (parallel clips, 0.1.91): never twice the same account at once."""
    profiles = state['profiles']
    selected = next((p for p in profiles if p['id'] == current), None)
    automatic=state.get('settings', {}).get('flow_auto', False)
    ok = lambda p: eligible(state, p) and usable(p) and p['id'] not in exclude
    if selected and not selected.get('blocked') and selected.get('balance', 0) >= cost and selected['id'] not in exclude and (not automatic or ok(selected)):
        return selected
    if not automatic:
        return None
    return next((p for p in flow_refill.order(profiles) if ok(p) and not p.get('blocked') and p.get('balance', 0) >= cost), None)


def chrome_profile(value):
    value = str(value or '').strip()
    if value and not re.fullmatch(r'Default|Profile [0-9]+', value):
        raise ValueError('Dossier Chrome attendu : Default ou Profile suivi d’un numéro')
    return value


CHROME_PATHS = {
    'win32': [('PROGRAMFILES', 'Google/Chrome/Application/chrome.exe'), ('PROGRAMFILES(X86)', 'Google/Chrome/Application/chrome.exe'),
              ('LOCALAPPDATA', 'Google/Chrome/Application/chrome.exe')],
    'darwin': [(None, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'), ('HOME', 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
               (None, '/Applications/Chromium.app/Contents/MacOS/Chromium')],
    'linux': [(None, '/opt/google/chrome/chrome')],
}
CHROME_COMMANDS = ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome')


def chrome_executable(platform=None, environ=None, which=shutil.which):
    """Chrome on Windows, macOS and Linux (real case 06/11/2026: Linux was never searched)."""
    platform = platform or sys.platform; environ = os.environ if environ is None else environ
    key = 'win32' if platform.startswith('win') else 'darwin' if platform == 'darwin' else 'linux'
    for var, rest in CHROME_PATHS[key]:
        root = environ.get(var) if var else ''
        if var and not root:continue
        path = pathlib.Path(root) / rest if root else pathlib.Path(rest)
        if path.is_file():return path
    if key == 'win32':return None
    found = next((which(name) for name in CHROME_COMMANDS if which(name)), None)
    return pathlib.Path(found) if found else None


def launch(profile):
    """Start Chrome in the background (no window, nothing brought to the front) for one saved account.

    The FruchtDrama extension starts with Chrome and takes the task in its own window, without focus
    (0.1.89). No credential or cookie access. Only used when no FruchtDrama window answers at all.
    """
    project_url(profile['flow_url'])
    folder = chrome_profile(profile.get('chrome_profile'))
    executable = chrome_executable()
    if not executable:
        raise ValueError('Chrome introuvable sur cet ordinateur. Ouvrez la fenêtre FruchtDrama (icône épinglée) : la tâche repart seule.')
    args = [str(executable), '--no-startup-window']
    if folder:
        args.append('--profile-directory=' + folder)
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), start_new_session=not sys.platform.startswith('win'))
