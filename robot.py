"""Robot de surveillance (owner, 09/11/2026: « créer un robot qui va repérer, détecter et corriger toutes les erreurs,
tous les retards de fonctionnement »).

Every minute the studio asks `inspect` what to do with each episode. Pure functions: the server applies the actions.
The robot only takes actions that cost nothing and can never pay twice:
- a texts/boards/research step (ChatGPT, Claude, TikTok) stopped on a technical error is asked again;
- an episode « en cours » with nothing queued nor in progress for too long is scheduled again;
- a Filon refresh that failed is tried again.
A clip that may have been sent to Flow/Grok is never touched (the owner checks it). Each episode gets at most
MAX_FIXES robot actions per 6 hours, so a real problem is never hidden behind endless retries.
"""
from __future__ import annotations

import re

MAX_FIXES = 3
WINDOW = 6 * 3600
QUIET = {'research': 8, 'ideas': 10, 'sheet': 10, 'script': 25, 'characters': 15, 'images': 20, 'cover': 15,
         'quality': 20, 'clips': 40, 'edit': 30}  # minutes without news before a « running » episode is looked at
CHAT_SLOTS = re.compile(r'^(?:script|ideas|sheet|characters|character:.*|state:.*|image:\d+|image_end:\d+|cover|cover_review|board_review|quality_review|meta|research|flow_rewrite:\d+)$')
# Technical failures that happen before anything is paid, or on free services.
TECHNICAL = re.compile(r'Réponse JSON complète non détectée|Receiving end does not exist|Could not establish connection|'
                       r'Frame with ID \d+ was removed|No tab with id|Extension context invalidated|Suivi interrompu|'
                       r'Fenêtre FruchtDrama disparue|Tâche sans nouvelles|Le connecteur de l.onglet ne répond pas|'
                       r'Aucun résultat vidéo TikTok|délai|timeout', re.I)


def recent_fixes(j, moment):
    return [x for x in j.get('robot_fixes') or [] if moment - x.get('t', 0) < WINDOW]


def last_news(j, seconds):
    ev = j.get('events') or []
    return seconds(ev[-1]['at']) if ev else seconds(j.get('updated') or j.get('created'))


def inspect(j, tasks, moment, seconds):
    """What the robot does with this episode now: None, or {'action': 'resume'|'schedule'|'refresh_filon', 'why': str}.
    `tasks`: the tasks of this episode; `seconds`: ISO date → timestamp."""
    if j.get('status') in ('done', 'paused', 'rendering') or j.get('stage') == 'done':
        return None
    if len(recent_fixes(j, moment)) >= MAX_FIXES:
        return None
    live = [t for t in tasks if t.get('status') in ('queued', 'claimed')]
    last = [t for t in tasks if t.get('status') == 'failed']
    last = max(last, key=lambda t: seconds(t.get('claimed') or t.get('created')) or 0) if last else None
    if j.get('filon_only'):
        if j.get('status') == 'attention' and not live and moment - last_news(j, seconds) > 5 * 60:
            return {'action': 'refresh_filon', 'why': 'actualisation du Filon en échec : nouvel essai'}
        return None
    if j.get('status') == 'attention' and not live and last and CHAT_SLOTS.match(str(last.get('slot', ''))) \
            and last.get('kind') not in ('flow_video', 'engine_video'):
        error = ' '.join(str(x) for x in (last.get('error'), (j.get('events') or [{}])[-1].get('text')))
        if TECHNICAL.search(error) and moment - last_news(j, seconds) > 60:
            return {'action': 'resume', 'why': f"« {last.get('slot')} » arrêté sur une erreur technique, sans frais : étape redemandée"}
    if j.get('status') == 'running' and not live:
        quiet = QUIET.get(j.get('stage'), 20) * 60
        if moment - last_news(j, seconds) > quiet:
            return {'action': 'schedule', 'why': f"rien en cours depuis {int((moment - last_news(j, seconds)) // 60)} min à l’étape {j.get('stage')} : production relancée"}
    return None


def note(j, decision, moment, now_iso):
    j.setdefault('robot_fixes', []).append({'t': moment, 'at': now_iso, 'action': decision['action'], 'why': decision['why']})
    del j['robot_fixes'][:-20]
