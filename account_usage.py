"""Which account works right now, on which AI, for what (owner 06/11/2026: « on doit savoir quel compte est utilisé,
quelle IA est utilisée et à quel moment »). Pure functions on the state; no credential is ever read or kept.

Keys, shared with « Mes comptes » (web/accounts.js):
  flow:<profile id>             one Google Flow account
  engine:<engine>:<email>       one registered Grok / Arena / Vidogrid account
  site:<service>                the session open in the FruchtDrama window (ChatGPT, Claude, or an engine without
                                registered accounts)
"""
import readiness

LABELS = {'flow': 'Google Flow', 'grok': 'Grok', 'arena': 'Arena', 'vidogrid': 'Vidogrid', 'chatgpt': 'ChatGPT', 'claude': 'Claude'}
SLOTS = {'script': 'Scénario', 'ideas': 'Idées', 'sheet': 'Fiche de l’histoire', 'research': 'Recherche TikTok',
         'characters': 'Personnages', 'cover': 'Miniature', 'cover_review': 'Contrôle de la miniature',
         'board_review': 'Contrôle des planches', 'quality_review': 'Contrôle des clips', 'rewrite_meta': 'Titre et description'}


def service_of(task):
    kind = task.get('kind') or ''
    payload = task.get('payload') or {}
    if kind in ('flow_video', 'flow_collect'):
        return 'flow'
    if kind == 'engine_video':
        return payload.get('engine')
    if kind.startswith('chat_'):
        return payload.get('provider') or 'chatgpt'
    return None


def key_of(task):
    """Account key of a task, or None (TikTok research, manual imports)."""
    service = service_of(task)
    if not service:
        return None
    if service == 'flow':
        return 'flow:' + task['profile'] if task.get('profile') else None
    email = ((task.get('payload') or {}).get('account') or {}).get('email')
    if task.get('kind') == 'engine_video' and email:
        return 'engine:' + service + ':' + email
    return 'site:' + service


def what(task, job=None):
    """« Clip 3 de BANANITO », « Planche 7 », « Scénario »."""
    slot = str(task.get('slot') or '')
    name, _, rest = slot.partition(':')
    if name == 'clip' and rest.isdigit():
        text = 'Clip ' + str(int(rest) + 1)
    elif name == 'image' and rest.isdigit():
        text = 'Planche ' + str(int(rest) + 1)
    elif name == 'image_end' and rest.isdigit():
        text = 'Planche de fin ' + str(int(rest) + 1)
    elif name == 'character':
        text = 'Personnage'
    elif name == 'state':
        text = 'Feuille d’état'
    else:
        text = SLOTS.get(slot, slot or 'Tâche')
    title = (job or {}).get('title')
    return text + (' de ' + title if title else '')


def touch(state, task, at):
    """Called when a task is taken by the window: this account was used at `at` (epoch seconds)."""
    key = key_of(task)
    if key:
        state.setdefault('last_used', {})[key] = at
    return key


def number_flow(state):
    """Stable « Compte N » for each Flow account: a number never moves when credits change, so « compte 2 → compte 3 »
    in the journal still names the same accounts later. Accounts first numbered by credits (largest first); a new
    account takes the smallest free number."""
    shown = [p for p in state.get('profiles', []) if p.get('flow_email') or p.get('label')]
    taken = {p['number'] for p in shown if isinstance(p.get('number'), int)}
    n = 1
    for p in sorted((p for p in shown if not isinstance(p.get('number'), int)), key=lambda p: -(p.get('balance') or 0)):
        while n in taken:
            n += 1
        p['number'] = n
        taken.add(n)
    return state


def flow_name(profile, with_credits=True, word='Compte Flow', extra=None):
    """« Compte Flow 2 (ar•••5@example.com, 38 crédits) »."""
    if not profile:
        return word + ' inconnu'
    bits = [readiness.mask(profile.get('flow_email') or profile.get('label'))]
    if with_credits:
        bits.append(credits(profile.get('balance') or 0))
    if extra:
        bits.append(extra)
    number = profile.get('number')
    return (word + ' ' + str(number) if number else word) + ' (' + ', '.join(b for b in bits if b) + ')'


def credits(n):
    return f'{n} crédit' + ('s' if abs(n) > 1 else '')


def switch_line(previous, profile, cost=None):
    """Journal line of an automatic Flow switch: « Compte Flow 2 (…, 0 crédit, vide) → compte 3 (…, 38 crédits) »."""
    if not previous:
        return 'Flow : ' + flow_name(profile) + ' ; clips reçus conservés.'
    # Real case 09/11/2026: « 50 crédits, vide » for an account left for another reason; the journal says the real one.
    if previous.get('blocked') == 'unavailable':
        why = 'sans accès à Flow'
    elif cost is not None and (previous.get('balance') or 0) >= cost:
        state = (previous.get('readiness') or {}).get('state')
        why = 'à régler' if state and state != 'ready' else 'occupé ou non relié à la fenêtre'
    else:
        why = 'vide' if cost is None or not previous.get('balance') else f'moins de {cost} crédits'
    return flow_name(previous, extra=why) + ' → ' + flow_name(profile, word='compte') + ' ; clips reçus conservés.'


def in_use(state):
    """One entry per task taken by the window: who works, on which AI, for what, since when."""
    jobs = {j['id']: j for j in state.get('jobs', [])}
    profiles = {p['id']: p for p in state.get('profiles', [])}
    rows = []
    for t in state.get('tasks', []):
        if t.get('status') != 'claimed':
            continue
        key = key_of(t)
        if not key:
            continue
        service = service_of(t)
        row = {'key': key, 'service': service, 'label': LABELS.get(service, service), 'what': what(t, jobs.get(t.get('job'))), 'short': what(t),
               'job': t.get('job'), 'slot': t.get('slot'), 'since': t.get('claimed'), 'task': t.get('id')}
        if service == 'flow':
            p = profiles.get(t.get('profile')) or {}
            row.update(email=p.get('flow_email') or p.get('label'), number=p.get('number'), credits=p.get('balance', 0), profile=p.get('id'))
        elif key.startswith('engine:'):
            row['email'] = ((t.get('payload') or {}).get('account') or {}).get('email')
        rows.append(row)
    return rows


def view(state):
    number_flow(state)
    return {'in_use': in_use(state), 'last_used': dict(state.get('last_used') or {})}


def clip_account(task, profiles):
    """Account that made a received clip, kept on the scene (« Flow · compte 2 »)."""
    if task.get('kind') == 'flow_video':
        p = next((x for x in profiles if x['id'] == task.get('profile')), None) or {}
        return {'profile': p.get('id'), 'email': p.get('flow_email') or p.get('label')} if p else None
    if task.get('kind') == 'engine_video':
        email = ((task.get('payload') or {}).get('account') or {}).get('email')
        return {'email': email} if email else None
    return None


def ai_text(state, task):
    """« Flow · compte 2 (ar•••5@example.com, 38 crédits) », « Grok · gr•••k@example.com », « ChatGPT »."""
    service = service_of(task)
    if not service:
        return ''
    if service == 'flow':
        p = next((x for x in state.get('profiles', []) if x['id'] == task.get('profile')), None)
        return 'Flow · ' + flow_name(p, word='compte') if p else 'Flow'
    email = ((task.get('payload') or {}).get('account') or {}).get('email')
    return LABELS.get(service, service) + (' · ' + readiness.mask(email) if email else '')


def claim_line(state, task):
    """Journal line when the window takes a task: what, and which AI and account."""
    ai = ai_text(state, task)
    return 'En cours : ' + what(task) + (' · IA : ' + ai if ai else '') + '.'
