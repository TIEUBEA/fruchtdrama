"""One account per e-mail address, like the Atelier: the owner adds an address once and ticks the
services it opens (ChatGPT, Claude, Google Flow, Grok, Arena). Behind the scenes it creates the
Flow credit profile and the Grok / Arena rotation accounts. No password is ever stored.

Pure functions on the state; the server passes its own Flow profile deletion (which checks clips in
flight) so a linked profile is never removed under a running generation.
"""
import re
import uuid

import engine_accounts

SERVICES = ('chatgpt', 'claude', 'flow', 'grok', 'arena')
LABELS = {'chatgpt': 'ChatGPT', 'claude': 'Claude', 'flow': 'Google Flow', 'grok': 'Grok', 'arena': 'Arena'}
EMAIL = re.compile(r'[^\s@]+@[^\s@]+\.[^\s@]+')


def clean_email(value):
    email = str(value or '').strip().lower()
    if not EMAIL.fullmatch(email):
        raise ValueError('Adresse e-mail du compte attendue (aucun mot de passe)')
    return email


def profile_email(profile):
    value = str(profile.get('flow_email') or profile.get('label') or '').strip().lower()
    return value if EMAIL.fullmatch(value) else None


def flow_profiles(state, email):
    return [p for p in state.setdefault('profiles', []) if profile_email(p) == email]


def stored(state, email):
    return next((i for i in state.setdefault('identities', []) if i['email'] == email), None)


def add(state, email, services, label='', balance=0, new_id=None):
    """Create or extend the account for this address. Returns the identity record."""
    email = clean_email(email)
    chosen = [s for s in SERVICES if s in set(services or [])]
    if not chosen:
        raise ValueError('Cochez au moins un service pour ce compte')
    balance = int(balance or 0)
    if not 0 <= balance <= 100000:
        raise ValueError('Solde Flow invalide')
    new_id = new_id or (lambda: uuid.uuid4().hex[:16])
    identity = stored(state, email)
    if not identity:
        identity = {'id': new_id(), 'email': email, 'label': str(label or email)[:60], 'services': []}
        state['identities'].append(identity)
    elif label:
        identity['label'] = str(label)[:60]
    for service in chosen:
        if service not in identity['services']:
            identity['services'].append(service)
    identity['services'] = [s for s in SERVICES if s in identity['services']]
    if 'flow' in chosen and not flow_profiles(state, email):
        state['profiles'].append({'id': new_id(), 'label': email, 'balance': balance, 'checked': None,
                                  'credit_source': 'manual' if balance else 'unknown'})
    for engine in ('grok', 'arena'):
        if engine in chosen and not any(a['email'] == email for a in engine_accounts.accounts(state, engine)):
            engine_accounts.add(state, engine, identity['label'], email)
    return identity


def remove_service(state, email, service, delete_profile):
    email = clean_email(email)
    if service not in SERVICES:
        raise ValueError('Service inconnu')
    if service == 'flow':
        for p in flow_profiles(state, email):
            delete_profile(p['id'])
    if service in ('grok', 'arena'):
        for a in [a for a in engine_accounts.accounts(state, service) if a['email'] == email]:
            if engine_accounts.busy(state, a):
                raise ValueError('Ce compte génère un clip : attendez la fin')
            state['engine_accounts'].remove(a)
    identity = stored(state, email)
    if identity and service in identity['services']:
        identity['services'].remove(service)


def delete(state, email, delete_profile):
    """Remove the address and everything linked to it; refuses while a clip uses it."""
    email = clean_email(email)
    for a in [a for a in state.setdefault('engine_accounts', []) if a['email'] == email]:
        if engine_accounts.busy(state, a):
            raise ValueError('Ce compte génère un clip : attendez la fin')
    for p in flow_profiles(state, email):
        delete_profile(p['id'])
    state['engine_accounts'] = [a for a in state['engine_accounts'] if a['email'] != email]
    state['identities'] = [i for i in state.setdefault('identities', []) if i['email'] != email]


def view(state, now, clip_cost=12):
    """One row per address, merging older Flow profiles and Grok / Arena accounts."""
    emails = []
    for i in state.setdefault('identities', []):
        emails.append(i['email'])
    for p in state.setdefault('profiles', []):
        e = profile_email(p)
        if e:
            emails.append(e)
    for a in state.setdefault('engine_accounts', []):
        emails.append(a['email'])
    rows = []
    for email in dict.fromkeys(emails):
        identity = stored(state, email) or {}
        services = {}
        sites = state.get('sites') or {}

        def session(site):
            # The window holds one session per site: say whether it is this address, another one, or unknown.
            seen = sites.get(site) or {}
            if not seen.get('connected'):
                return 'off', 'Pas connecté'
            if seen.get('email') == email:
                return 'live', 'Connecté'
            if seen.get('email'):
                return 'idle', 'Enregistré · autre compte ouvert'
            return 'idle', 'Enregistré'
        for s in identity.get('services', []):
            if s in ('chatgpt', 'claude'):
                st, text = session(s)
                services[s] = {'state': st, 'text': text}
        profiles = flow_profiles(state, email)
        if profiles:
            total = sum(int(p.get('balance') or 0) for p in profiles)
            blocked = any(p.get('blocked') for p in profiles)
            low = total < clip_cost
            services['flow'] = {'state': 'blocked' if blocked or total <= 0 else 'low' if low else 'live' if (sites.get('flow') or {}).get('email') == email else 'ok',
                                'text': f'{total} crédits' + (' · solde bas' if low and total > 0 else ' · épuisé' if total <= 0 else ' · ouvert' if (sites.get('flow') or {}).get('email') == email else ''),
                                'balance': total, 'profiles': [p['id'] for p in profiles]}
        for engine in ('grok', 'arena'):
            account = next((a for a in engine_accounts.accounts(state, engine) if a['email'] == email), None)
            if account:
                walled = engine_accounts.walled(account, now)
                st, text = session(engine)
                services[engine] = {'state': 'wall' if walled else 'live' if st == 'live' else 'ok', 'account': account['id'],
                                    'text': 'Limite jusqu’à ' + engine_accounts.stamp(account['wall']['until'])[11:16] + ' UTC' if walled else 'Connecté' if st == 'live' else 'Disponible'}
        label = identity.get('label') or next((a['label'] for a in state['engine_accounts'] if a['email'] == email), email)
        rows.append({'email': email, 'label': label, 'services': services,
                     'order': [s for s in SERVICES if s in services]})
    return rows
