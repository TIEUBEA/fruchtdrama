"""Routing of explicitly registered, already authenticated Flow sessions."""
import os
import pathlib
import re
import subprocess
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


def choose(state, current, cost):
    """Never reset balances, switch an active task, or use unregistered accounts."""
    profiles = state['profiles']
    selected = next((p for p in profiles if p['id'] == current), None)
    automatic=state.get('settings', {}).get('flow_auto', False)
    def eligible(p):
        # Accounts detected in the window carry their slot; older registrations stay usable only if routed.
        return route(p) and state['clients'].get(p.get('flow_client'),{}).get('role') in ('all','flow') and not state['clients'].get(p.get('flow_client'),{}).get('disabled')
    if selected and not selected.get('blocked') and selected.get('balance', 0) >= cost and (not automatic or eligible(selected)):
        return selected
    if not automatic:
        return None
    return next((p for p in flow_refill.order(profiles) if eligible(p) and p.get('balance', 0) >= cost), None)


def chrome_profile(value):
    value = str(value or '').strip()
    if value and not re.fullmatch(r'Default|Profile [0-9]+', value):
        raise ValueError('Dossier Chrome attendu : Default ou Profile suivi d’un numéro')
    return value


def launch(profile):
    """Open one saved account on demand; no credential or cookie access."""
    url = project_url(profile['flow_url'])
    folder = chrome_profile(profile.get('chrome_profile'))
    roots = [os.environ.get(name) for name in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA')]
    executable = next((pathlib.Path(root) / 'Google/Chrome/Application/chrome.exe' for root in roots if root and (pathlib.Path(root) / 'Google/Chrome/Application/chrome.exe').is_file()), None)
    if not executable:
        raise ValueError('Chrome introuvable. Installez-le ou ouvrez le navigateur appairé.')
    args = [str(executable)]
    if folder:
        args.append('--profile-directory=' + folder)
    args.append(url)
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
