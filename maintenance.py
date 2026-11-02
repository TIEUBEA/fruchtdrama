"""Data hygiene and support (P4-1). Never deletes without a copy: productions go to data/corbeille,
the state is backed up before a purge, and the failure report contains no secret."""
import datetime as dt
import json
import pathlib
import platform
import re
import shutil
import sys

TASK_KEEP_DAYS = 30
EVENTS_KEEP = 300
SECRET = re.compile(r'(?i)(bearer\s+[\w.-]+|token["\']?\s*[:=]\s*["\']?[\w.-]{8,}|pair_code["\']?\s*[:=]\s*["\']?\w+|x-access-token:[^@\s]+)')
EMAIL = re.compile(r'[^\s@<>()"\']+@[^\s@<>()"\']+\.[a-z]{2,}', re.I)


def stamp():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S')


def trash_job(data, job_id):
    """Move a production folder to data/corbeille (restorable by moving it back)."""
    source = data / 'jobs' / job_id
    target = data / 'corbeille' / f'{job_id}-{stamp()}'
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.move(str(source), str(target))
    return target


def backup_state(data, state):
    folder = data / 'sauvegardes'; folder.mkdir(parents=True, exist_ok=True)
    target = folder / f'state-{stamp()}.json'
    target.write_text(json.dumps(state, ensure_ascii=False), 'utf-8')
    backups = sorted(folder.glob('state-*.json'))
    for old in backups[:-10]:
        old.unlink()  # keep the 10 latest copies
    return target


def purge(state, now):
    """Drop finished tasks older than 30 days and tasks of deleted productions; bound event logs."""
    jobs = {j['id'] for j in state['jobs']}
    limit = now - TASK_KEEP_DAYS * 86400
    def old(t):
        try:
            return dt.datetime.fromisoformat(t.get('created', '')).timestamp() < limit
        except ValueError:
            return False
    before = len(state['tasks'])
    state['tasks'] = [t for t in state['tasks'] if t['job'] in jobs and not (t['status'] in ('done', 'cancelled', 'failed') and old(t) and not unresolved(t))]
    events = 0
    for j in state['jobs']:
        if len(j.get('events', [])) > EVENTS_KEEP:
            events += len(j['events']) - EVENTS_KEEP; j['events'] = j['events'][-EVENTS_KEEP:]
    return {'tasks_removed': before - len(state['tasks']), 'events_removed': events}


def unresolved(t):
    """A possibly charged Flow submission stays as evidence until it is resolved."""
    r = t.get('reservation') or {}
    return t.get('kind') == 'flow_video' and t.get('status') == 'failed' and r and not r.get('refunded') and not t.get('acknowledged')


def redact(text):
    return EMAIL.sub('<adresse>', SECRET.sub('<secret>', str(text)))


def report(state, data, version, now_text):
    lines = [f'Rapport de panne FruchtDrama {version} — {now_text}',
             f'Système : {platform.system()} {platform.release()} · Python {sys.version.split()[0]} · ffmpeg {"présent" if shutil.which("ffmpeg") else "ABSENT"}',
             '', 'Passerelles :']
    for c in state.get('clients', {}).values():
        lines.append(f"- {c.get('label')} · rôle {c.get('role')} · IA {c.get('ai_provider')} · vue {c.get('seen')}")
    lines += ['', 'Productions :']
    for j in state.get('jobs', [])[-20:]:
        cfg = j.get('config', {})
        lines.append(f"- {j['id'][:8]} « {j.get('title')} » · {j.get('stage')} / {j.get('status')} · moteur {cfg.get('video_engine', 'flow')} · langue {cfg.get('language')}"
                     + (f" · dernière erreur {j['last_error'].get('kind')} ({j['last_error'].get('slot')})" if j.get('last_error') else ''))
        for e in j.get('events', [])[-5:]:
            lines.append(f"    {e.get('at', '')[:19]} {e.get('text', '')[:300]}")
    log = data / 'server-errors.log'
    if log.is_file():
        lines += ['', 'Dernières erreurs serveur :'] + log.read_text('utf-8', errors='replace').splitlines()[-60:]
    return redact('\n'.join(lines))
