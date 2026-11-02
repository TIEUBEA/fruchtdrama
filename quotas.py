"""Learned quotas (P2-06/P2-07): without an API, a service's capacity is measured when it refuses.

Every successful generation is a pass, every limit message a wall. Sliding 6 h window. Single writer:
the server mutates this journal only under its lock (fixes the Atelier's lost passes between tabs).
"""
import datetime as dt

WINDOW = 6 * 3600
TOLERANCE = 60
DEFAULT_WAIT = 30 * 60
SERVICES = {'chatgpt_image': 'ChatGPT images', 'chatgpt_text': 'ChatGPT texte', 'claude_text': 'Claude texte'}


def service(task):
    kind = task.get('kind'); provider = task.get('payload', {}).get('provider', 'chatgpt')
    if kind == 'chat_image':
        return 'chatgpt_image'
    if kind == 'chat_text':
        return ('claude' if provider == 'claude' else 'chatgpt') + '_text'
    return None


def journal(state):
    return state.setdefault('quotas', {'passes': [], 'walls': []})


def note_pass(state, name, now):
    q = journal(state); q['passes'].append([now, name]); q['passes'] = q['passes'][-3000:]


def note_wall(state, name, now, retry_after=None, message=''):
    q = journal(state)
    if any(w[1] == name and now - w[0] < 60 for w in q['walls']):
        return  # same wall seen twice within a minute
    q['walls'].append([now, name, str(message)[:200], now + retry_after if retry_after else None]); q['walls'] = q['walls'][-200:]


def status(state, name, now):
    q = journal(state)
    passes = [p[0] for p in q['passes'] if p[1] == name]
    walls = [w for w in q['walls'] if w[1] == name]
    used = sum(1 for t in passes if now - t < WINDOW)
    last = walls[-1] if walls else None
    capacity = sum(1 for t in passes if last and last[0] - WINDOW <= t <= last[0]) if last else None
    blocked = False; retry_at = None
    if last and now - last[0] < WINDOW and not any(t > last[0] + TOLERANCE for t in passes):
        if last[3]:
            retry_at = last[3]
        else:
            window = [t for t in passes if last[0] - WINDOW < t <= last[0]]
            retry_at = min(window) + WINDOW if window else last[0] + DEFAULT_WAIT
        blocked = now < retry_at
    return {'service': name, 'label': SERVICES.get(name, name), 'used': used, 'capacity': capacity,
            'remaining': max(capacity - used, 0) if capacity is not None else None, 'blocked': blocked, 'retry_at': retry_at if blocked else None}


def forget(state, name):
    q = journal(state); q['walls'] = [w for w in q['walls'] if w[1] != name]


def summary(state, now):
    return [status(state, name, now) for name in SERVICES]


def stamp(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()
