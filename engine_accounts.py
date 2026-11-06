"""Grok accounts (P5-07/P5-08). Pure functions on the state; no credential is ever stored.

A site keeps one signed-in session per Chrome profile, so changing account is guided: the owner
signs in to the next account in the FruchtDrama window, the connector checks the identity shown.
"""
import datetime as dt
import re
import uuid

DEFAULT_WALL = 3 * 3600  # used when the provider does not announce its renewal time


def stamp(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()


def local(ts):
    """Hour shown to the owner: local time of this computer, never UTC."""
    return dt.datetime.fromtimestamp(ts).strftime('%H:%M')


def accounts(state, engine):
    return [a for a in state.setdefault('engine_accounts', []) if a['engine'] == engine]


def by_id(state, account_id):
    return next((a for a in state.setdefault('engine_accounts', []) if a['id'] == account_id), None)


def add(state, engine, label, email):
    email = str(email or '').strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise ValueError('Adresse e-mail du compte attendue (aucun mot de passe)')
    if any(a['engine'] == engine and a['email'] == email for a in state.setdefault('engine_accounts', [])):
        raise ValueError('Ce compte est déjà enregistré pour ce moteur')
    account = {'id': uuid.uuid4().hex[:16], 'engine': engine, 'label': str(label or email)[:60], 'email': email}
    state['engine_accounts'].append(account)
    return account


def walled(account, now):
    return account.get('wall', {}).get('until', 0) > now


def choose(state, engine, current, now):
    """Keep the current account while it is usable; otherwise the next usable one in order."""
    rows = accounts(state, engine)
    selected = next((a for a in rows if a['id'] == current), None)
    if selected and not walled(selected, now):
        return selected
    start = rows.index(selected) + 1 if selected else 0
    for a in rows[start:] + rows[:start]:
        if not walled(a, now):
            return a
    return None


def wall(account, now, retry_after=None, message=''):
    until = now + (retry_after or DEFAULT_WALL)
    account['wall'] = {'at': stamp(now), 'until': until, 'until_text': stamp(until), 'message': str(message)[:200]}


def forget(account):
    account.pop('wall', None)


def next_free(state, engine, now):
    times = [a['wall']['until'] for a in accounts(state, engine) if walled(a, now)]
    return min(times) if times else None


def busy(state, account):
    """True while a clip is being generated with this account."""
    return any(t['status'] == 'claimed' and t['kind'] == 'engine_video'
               and t['payload'].get('account', {}).get('email') == account['email']
               and t['payload'].get('engine') == account['engine'] for t in state.get('tasks', []))
