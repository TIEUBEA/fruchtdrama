"""« Préparer mes comptes » (owner 06/11/2026): every useful account is checked in the background before anything starts.

Real case: in the middle of a production two Flow clips failed « Page du fournisseur indisponible ou vide après 90 secondes
(connexion requise, vérification anti-robot ou blocage) » and the episode went to « Action requise »; the owner had to look
for a background tab. Now the sign-ins and checks are settled in Mes comptes, before starting.

Pure functions on the state. States of a service or a Flow account:
  ready      Prêt
  fix        À régler (sign-in, anti-robot check, empty page): the owner fixes it himself in the tab
  no_access  Pas d'accès (Google account without Flow)
A check never spends a credit and never sends a prompt: it only reads the page.
"""
import datetime as dt
import re

import flow_refill
import flow_accounts

FRESH = 15 * 60          # a check older than this is done again before a production
CHECK_TIMEOUT = 120      # a production never waits longer than this for a check that does not come back
SITE_LABELS = {'chatgpt': 'ChatGPT', 'claude': 'Claude', 'grok': 'Grok', 'arena': 'Arena', 'vidogrid': 'Vidogrid', 'flow': 'Google Flow'}
ENGINE_SITES = ('grok', 'arena', 'vidogrid')
NOT_READY = ('fix', 'no_access')
STATES = ('ready', 'fix', 'no_access')
CHAT_STAGES = ('research', 'ideas', 'sheet', 'script', 'characters', 'images', 'clips', 'quality', 'cover')
VIDEO_STAGES = ('research', 'ideas', 'sheet', 'script', 'characters', 'images', 'clips')
WRITE_STAGES = ('research', 'ideas', 'sheet', 'script')


def age(entry, moment):
    try:
        return moment - dt.datetime.fromisoformat((entry or {}).get('at') or '').timestamp()
    except (TypeError, ValueError):
        return None


def fresh(entry, moment):
    a = age(entry, moment)
    return a is not None and a < FRESH


def store(state):
    r = state.setdefault('readiness', {})
    r.setdefault('sites', {})
    r.setdefault('pending', [])
    return r


def site_entry(state, name):
    return ((state.get('readiness') or {}).get('sites') or {}).get(name)


def usable(profile):
    """A Flow account the automatic switch may use: not marked « À régler » or « Pas d'accès »."""
    return (profile.get('readiness') or {}).get('state') not in NOT_READY


def mask(email):
    """« ab•••x@gmail.com »: enough to tell one's own accounts apart on screen, not the full address."""
    email = str(email or '')
    if '@' not in email:
        return email
    name, domain = email.split('@', 1)
    return name[:2] + '•••' + (name[-1] if len(name) > 3 else '') + '@' + domain


def needs(cfg, stage):
    """Services a production still needs from this stage on."""
    cfg = cfg or {}
    sites = []
    if stage in CHAT_STAGES and stage != 'clips':
        sites.append('chatgpt')  # characters, boards and cover are always drawn by ChatGPT
        if cfg.get('provider') == 'claude' and stage in WRITE_STAGES:
            sites.append('claude')
    engine = cfg.get('video_engine') or 'flow'
    flow = stage in VIDEO_STAGES and engine == 'flow'
    if stage in VIDEO_STAGES and engine in ENGINE_SITES:
        sites.append(engine)
    return {'sites': sites, 'flow': flow}


def site_has_account(state, name):
    """At least one account of this service is ready: the last check says so, or, never checked, the window is signed in."""
    entry = site_entry(state, name)
    if entry and entry.get('state') in STATES:
        return entry['state'] == 'ready'
    return bool(((state.get('sites') or {}).get(name) or {}).get('connected'))


def flow_registered(state):
    return [p for p in state.get('profiles', []) if p.get('flow_email') and p.get('flow_url')]


def flow_has_account(state):
    moment=dt.datetime.now(dt.timezone.utc).timestamp()
    clients=state.get('clients') or {}
    for profile in flow_registered(state):
        if not usable(profile) or profile.get('blocked')=='unavailable' or profile.get('auto_enabled') is False:
            continue
        client_id=profile.get('flow_client')
        if not client_id:
            return True  # Older manually registered profiles have no bound gateway.
        client=clients.get(client_id) or {}
        age=flow_accounts.seen_ago(client,moment)
        if not client.get('disabled') and age is not None and age<180:
            return True
    return False


def setup_missing(state):
    """First step (owner 06/11/2026): nothing starts before ChatGPT and one clip engine have a ready account."""
    missing = []
    if not site_has_account(state, 'chatgpt'):
        missing.append({'key': 'site:chatgpt', 'service': 'chatgpt', 'label': 'ChatGPT', 'reason': 'aucun compte prêt (personnages et planches)'})
    if not (flow_has_account(state) or any(site_has_account(state, e) for e in ENGINE_SITES)):
        missing.append({'key': 'engine', 'service': 'flow', 'label': 'Clips', 'reason': 'aucun compte Google Flow, Arena, Vidogrid ni Grok prêt'})
    return missing


def candidates(state, cost, eligible, order=None):
    """Flow accounts able to pay a clip, readiness ignored, in rotation order."""
    rows = (order or flow_refill.order)(state.get('profiles', []))
    return [p for p in rows if eligible(p) and not p.get('blocked') and int(p.get('balance') or 0) >= cost]


def reason_of(entry):
    return str((entry or {}).get('reason') or 'à vérifier dans son onglet')


def blockers(state, cfg, stage, cost, moment, eligible, selected=None):
    """Known, recent reasons not to start: a needed service « À régler », or every Flow account able to pay « À régler ».

    Unknown or old states never block: they are checked first (checks_needed). No credits at all is not a blocker
    here: the existing wait for credits handles it."""
    need = needs(cfg, stage)
    out = []
    for name in need['sites']:
        entry = site_entry(state, name)
        label = SITE_LABELS[name]
        if entry and entry.get('state') in NOT_READY and fresh(entry, moment):
            out.append({'key': 'site:' + name, 'service': name, 'label': label, 'reason': reason_of(entry)})
        elif not entry and name in ENGINE_SITES + ('claude',) and not site_has_account(state, name):
            out.append({'key': 'site:' + name, 'service': name, 'label': label, 'reason': 'pas connecté'})
    if need['flow']:
        automatic = state.get('settings', {}).get('flow_auto', False)
        if automatic:
            pool = candidates(state, cost, eligible)
            if pool and not any(usable(p) or not fresh(p.get('readiness'), moment) for p in pool):
                for p in pool:
                    out.append({'key': 'flow:' + p['id'], 'service': 'flow', 'label': 'Google Flow ' + mask(p.get('flow_email') or p.get('label')),
                                'reason': reason_of(p.get('readiness'))})
        else:
            p = next((x for x in state.get('profiles', []) if x['id'] == selected), None)
            if p and not usable(p) and fresh(p.get('readiness'), moment):
                out.append({'key': 'flow:' + p['id'], 'service': 'flow', 'label': 'Google Flow ' + mask(p.get('flow_email') or p.get('label')),
                            'reason': reason_of(p.get('readiness'))})
    return out


def checks_needed(state, cfg, stage, cost, moment, eligible, limit=2):
    """What to read before starting: needed services not checked recently, and, unless a Flow account able to pay is
    already known ready, the first `limit` such accounts. Kept short so a production starts within seconds."""
    need = needs(cfg, stage)
    sites = [n for n in need['sites'] if not fresh(site_entry(state, n), moment)]
    profiles = []
    if need['flow'] and state.get('settings', {}).get('flow_auto', False):
        pool = candidates(state, cost, eligible)
        if not any(usable(p) and fresh(p.get('readiness'), moment) for p in pool):
            profiles = [p['id'] for p in pool if not fresh(p.get('readiness'), moment)][:limit]
    return {'sites': sites, 'profiles': profiles}


def full_targets(state):
    """« Préparer mes comptes »: ChatGPT, Claude if used, Grok / Arena if registered, every registered Flow account."""
    sites = ['chatgpt']
    seen = state.get('sites') or {}
    identities = state.get('identities') or []
    if state.get('settings', {}).get('provider') == 'claude' or (seen.get('claude') or {}).get('connected') or any('claude' in i.get('services', []) for i in identities):
        sites.append('claude')
    for engine in ENGINE_SITES:
        if any(a.get('engine') == engine for a in state.get('engine_accounts', [])) or (seen.get(engine) or {}).get('connected'):
            sites.append(engine)
    profiles = [p['id'] for p in flow_registered(state) if p.get('slot') is not None or p.get('auto_enabled')]
    return {'sites': sites, 'profiles': profiles}


def profile_target(p, home):
    """What the extension opens for one Flow account: its project, or its home page when no project exists yet."""
    url = home(p['flow_url']) if p.get('flow_url_home') else p['flow_url']
    return {'id': p['id'], 'url': url, 'email': str(p.get('flow_email') or '').lower(), 'home': bool(p.get('flow_url_home'))}


def clean_entry(raw, at):
    state = raw.get('state') if isinstance(raw, dict) else None
    if state not in STATES:
        return None
    email = str(raw.get('email') or '').strip().lower()[:120]
    return {'state': state, 'reason': ' '.join(str(raw.get('reason') or '').split())[:200], 'at': at,
            **({'email': email} if re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) else {})}


def apply_report(state, report, at, moment, busy_profiles=(), daily=flow_refill.DAILY):
    """Store what the window read. Returns the number of entries kept."""
    r = store(state)
    kept = 0
    for name, raw in (report.get('sites') or {}).items():
        if name not in SITE_LABELS or name == 'flow':
            continue
        entry = clean_entry(raw, at)
        if not entry:
            continue
        r['sites'][name] = entry
        kept += 1
        # The site cards of Avancé read the same session.
        state.setdefault('sites', {})[name] = {'connected': entry['state'] == 'ready', 'email': entry.get('email'),
                                                'challenge': bool(raw.get('challenge')), 'checked': at}
    for pid, raw in (report.get('profiles') or {}).items():
        p = next((x for x in state.get('profiles', []) if x['id'] == pid), None)
        entry = clean_entry(raw, at)
        if not p or not entry:
            continue
        p['readiness'] = entry
        kept += 1
        if entry['state'] == 'no_access':
            p['blocked'] = 'unavailable'
        elif p.get('blocked') == 'unavailable':
            p.pop('blocked', None)
        balance = raw.get('balance')
        # A balance read while a clip of this account is in flight would undo its reservation: kept for the next read.
        if entry['state'] == 'ready' and isinstance(balance, int) and not isinstance(balance, bool) and 0 <= balance <= 100000 and pid not in busy_profiles:
            flow_refill.read(p, balance, moment, daily)
            p['balance'] = balance
            p['credit_source'] = 'read'
            p['checked'] = at
            if balance > 0 and p.get('blocked') == 'credits':
                p.pop('blocked', None)
            elif balance == 0:
                p['blocked'] = 'credits'
    done = {'site:' + n for n in (report.get('sites') or {})} | {'flow:' + i for i in (report.get('profiles') or {})}
    r['pending'] = [k for k in r.get('pending', []) if k not in done]
    r['checked'] = at
    return kept


def mark(state, key, entry_state, reason, at):
    """One service or account marked from a production (a provider page that did not open)."""
    r = store(state)
    entry = {'state': entry_state, 'reason': str(reason)[:200], 'at': at}
    if key.startswith('site:'):
        name = key[5:]
        if name in SITE_LABELS and name != 'flow':
            previous = r['sites'].get(name) or {}
            r['sites'][name] = {**entry, **({'email': previous['email']} if previous.get('email') else {})}
            return True
        return False
    if key.startswith('flow:'):
        p = next((x for x in state.get('profiles', []) if x['id'] == key[5:]), None)
        if p:
            p['readiness'] = entry
            if entry_state == 'no_access':
                p['blocked'] = 'unavailable'
            return True
    return False


def describe(blockers_list):
    return '; '.join(b['label'] + ' : ' + b['reason'] for b in blockers_list)
