"""Local studio. Python 3.10+, Pillow for covers, ffmpeg for exports."""
from __future__ import annotations
import base64, copy, datetime as dt, hashlib, hmac, http.server, json, mimetypes, os, pathlib, re, secrets, shutil, subprocess, threading, time, urllib.parse, uuid, zipfile
import flow_accounts
import source_video
import flow_credits
import editorial
import captions
import covers
import quality
import errors
import engines
import engine_chain
import montage, source_video, moteur_v09, character_styles
import story_backup
import board_check
import engine_accounts
import account_usage
import identities, flow_refill
import ideas
import thumbs
import originality
import refusal
import quotas
import power
import maintenance
import series
import licence
import readiness
VERSION='0.1.96'
OFFICIAL_ORIGIN='chrome-extension://bhdmibhibonmaamgcbpmbhedhohfongj'  # extension/manifest.json "key"
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
DATA = pathlib.Path(os.environ.get('FRUCHT_DATA', ROOT / 'data')).resolve()
PORT = int(os.environ.get('FRUCHT_PORT', '8840'))
LICENCE = licence.Licence(DATA, VERSION)
LOCK = threading.RLock()
BUSY = set()
QUALITY_BUSY = set()
DOWNLOADS_ROOT = pathlib.Path(os.environ.get('FRUCHT_DOWNLOADS',pathlib.Path.home()/'Downloads')).resolve()
STEPS = ['research', 'script', 'characters', 'images', 'clips', 'quality', 'cover', 'edit', 'done']
LABELS = {'ideas':'Dix histoires', 'sheet':'Fiche de décision', 'research':'Recherche', 'script':'Scénario', 'characters':'Personnages', 'images':'Scènes', 'clips':'Animation Flow', 'quality':'Contrôle qualité', 'cover':'Couverture', 'edit':'Montage', 'done':'Terminé'}
CREATION_LANGUAGES=('Deutsch (de-DE)','Français (fr-FR)','English (en-US)','Español (es-ES)','Português (pt-BR)')
# Default research query per creation language (same values as the web form).
SITES=('chatgpt','flow','tiktok','grok','arena','vidogrid','claude')
RESEARCH_QUERIES={'Deutsch (de-DE)':'KI Früchte Geschichten deutsch','Français (fr-FR)':'histoires fruits IA français','English (en-US)':'AI fruit drama stories English','Español (es-ES)':'historias de frutas IA español','Português (pt-BR)':'histórias de frutas IA português'}

# Claude model and effort chosen in « Écrite par » (claude.ai interface, selected by the extension).
CLAUDE_MODELS={'opus-5.5':'Opus 5.5','fable-5.1':'Fable 5.1','sonnet-5.5':'Sonnet 5.5'}
CLAUDE_EFFORTS={'high':'Élevé','extra':'Extra','medium':'Moyen'}
CLAUDE_DEFAULTS={'claude_model':'opus-5.5','claude_effort':'high'}

def claude_choice(field,value):
    """Validated Claude model or effort; None gives the default. A clear refusal otherwise."""
    allowed=CLAUDE_MODELS if field=='claude_model' else CLAUDE_EFFORTS
    value=CLAUDE_DEFAULTS[field] if value is None else value
    if value not in allowed:
        raise ValueError(('Modèle Claude inconnu' if field=='claude_model' else 'Effort Claude inconnu')+' : '+str(value)[:40]+'. Choix possibles : '+', '.join(allowed.values())+'.')
    return value

def creation_language(value):
    value=str(value).strip()
    if value not in CREATION_LANGUAGES:raise ValueError('Choisissez Français, English, Español, Português ou Deutsch')
    return value

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def uid(): return uuid.uuid4().hex[:16]
def fresh():
    return {'version':1, 'token':secrets.token_urlsafe(32), 'pair_code':secrets.token_hex(4), 'jobs':[], 'profiles':[], 'clients':{}, 'tasks':[], 'settings':{'provider':'chatgpt','language':'Deutsch (de-DE)','scene_count':4,'clip_seconds':10,'flow_model':engines.OMNI_12,'flow_resolution':'720p','flow_cost':30,'query':'KI Früchte Geschichten deutsch','daily_budget':50}}
def read_state():
    DATA.mkdir(parents=True, exist_ok=True)
    p=DATA/'state.json'
    state=json.loads(p.read_text('utf-8')) if p.exists() else fresh()
    if 'flow_model' not in state['settings']:
        state['settings'].update(flow_model=engines.OMNI_12,flow_resolution='720p',flow_cost=30)
    if not state['settings'].get('v09_engine'):
        # Moteur V09 (owner, 09/11/2026): new episodes use Omni 1.2 Flash in 10 s, Grok for clip 1 only, Flow for the rest.
        state['settings'].update(v09_engine=1,flow_model=engines.OMNI_12,flow_resolution='720p',flow_cost=30,clip_seconds=10,clip_routing=engine_chain.V09)
        if [e for e in state['settings'].get('engine_chain') or [] if e not in engines.AVAILABLE]:state['settings']['engine_chain']=list(engine_chain.DEFAULT)
    return state
STATE=read_state()
if not os.environ.get('FRUCHT_NO_THUMBS'):
    thumbs.warm([c['url'] for j in STATE['jobs'] for c in j.get('candidates',[])],DATA)
def save():
    p=DATA/'state.tmp'
    p.write_text(json.dumps(STATE, ensure_ascii=False, indent=2),'utf-8')
    for attempt in range(5):
        try:
            p.replace(DATA/'state.json')
            return
        except PermissionError:
            if sys.platform!='win32' or attempt==4:
                raise
            time.sleep(.05*(attempt+1))
def job_by(id):
    return next((j for j in STATE['jobs'] if j['id']==id),None)
def profile_by(id): return next((p for p in STATE['profiles'] if p['id']==id),None)

def delete_profile(id):
    p=profile_by(id)
    if not p:raise ValueError('Profil Flow introuvable')
    related=[t for t in STATE['tasks'] if t.get('profile')==id]
    if any(t['status']=='claimed' for t in related):raise ValueError('Ce compte est utilisé par un clip en cours. Attendez sa récupération avant de supprimer le profil.')
    for t in related:
        j=job_by(t['job']);reservation=t.get('reservation')
        if t['status']=='failed' and reservation and not reservation.get('refunded') and t.get('slot','').startswith('clip:'):
            index=int(t['slot'].split(':')[1])
            if not j or index>=len(j.get('scenes',[])) or not j['scenes'][index].get('clip'):
                raise ValueError('Un clip envoyé reste à vérifier sur ce compte. Récupérez son résultat avant de supprimer le profil.')
    affected=set()
    for t in related:
        if t['status']=='queued':t['status']='cancelled';affected.add(t['job'])
    for j in STATE['jobs']:
        selected=j.get('flow_profile')==id
        if selected:j['flow_profile']=None
        j.get('flow_projects',{}).pop(id,None)
        if (selected or j['id'] in affected) and j['status']!='done':
            j['status']='paused';event(j,'Profil Flow supprimé du studio. Production conservée ; choisissez un autre profil puis Reprendre.')
    for c in STATE['clients'].values():
        if c.get('flow_profile')==id:c['flow_profile']=None
    STATE['profiles'].remove(p)
def remove_service_accounts(service):
    """Every account of one service leaves the studio (Flow profiles, Grok / Arena rotation, addresses). Returns (removed, kept)."""
    removed,kept=0,[]
    if service=='flow':
        for p in list(STATE['profiles']):
            try:delete_profile(p['id']);removed+=1
            except ValueError:kept.append(p.get('flow_email') or p.get('label') or p['id'])
    if service in ('grok','arena','vidogrid'):
        for a in list(engine_accounts.accounts(STATE,service)):
            if engine_accounts.busy(STATE,a):kept.append(a['email']);continue
            STATE['engine_accounts'].remove(a);removed+=1
    for i in STATE.setdefault('identities',[]):
        if service in i.get('services',[]):
            i['services'].remove(service)
            if service in ('chatgpt','claude'):removed+=1
    if service in ('chatgpt','claude','grok','arena','vidogrid'):readiness.store(STATE)['sites'].pop(service,None)
    return removed,kept

def client_accepts(client,task):
    role=client.get('role','all')
    if task['kind'] in ('flow_video','flow_collect'):
        target=task.get('payload',{}).get('flow_route')
        if target and not profile_by(task.get('profile')):return False
        return role in ('all','flow') and (target.get('client')==client.get('id') if target else task.get('profile')==client.get('flow_profile'))
    if task['kind']=='engine_video':return role=='all'
    if role not in ('all','creation'):return False
    if task['kind'] in ('chat_text','chat_collect','chat_image','chat_image_collect'):
        provider=task.get('payload',{}).get('provider','chatgpt')
        return client.get('ai_provider','both') in ('both',provider)
    return task['kind']=='tiktok_search'
# Two lanes per episode (0.1.89, like the Atelier: « les clips partent pendant que ChatGPT dessine les planches »):
# 'chat' (ChatGPT/Claude texts and images, TikTok research) and 'video' (Flow, Grok, Arena). At most one active task per lane and per episode.
VIDEO_KINDS=('flow_video','flow_collect','engine_video')
def lane_of(task): return 'video' if task.get('kind') in VIDEO_KINDS or (not task.get('kind') and str(task.get('slot','')).startswith('clip:')) else 'chat'  # no kind: manual import
def lane_busy(j,lane): return any(t['job']==j['id'] and t['status'] in ('queued','claimed') and lane_of(t)==lane for t in STATE['tasks'])
STAGE_NAMES={'research':'Recherche','ideas':'Idées','sheet':'Fiche','script':'Scénario','characters':'Personnages','images':'Planches',
             'clips':'Clips','quality':'Contrôle qualité','cover':'Miniature','edit':'Montage','done':'Terminé'}
def event(j, text):
    # Speed tracking (owner 09/11/2026): the journal says how long each stage took, to compare with the Atelier.
    clock=j.get('stage_clock');stage=j.get('stage')
    if clock and stage and clock.get('stage')!=stage:
        spent=int(time.time()-flow_credits.seconds(clock.get('at')))
        if 0<=spent<7*86400:
            j.setdefault('stage_durations',{})[clock['stage']]=j.get('stage_durations',{}).get(clock['stage'],0)+spent
            j['events'].append({'at':now(),'text':f"Durée de l’étape {STAGE_NAMES.get(clock['stage'],clock['stage'])} : {spent//60} min {spent%60:02d} s."})
    if stage and (not clock or clock.get('stage')!=stage):j['stage_clock']={'stage':stage,'at':now()}
    j['events'].append({'at':now(),'text':text}); j['updated']=now()

# Parallel clips (owner 06/11/2026: « deux comptes en même temps »): several Flow clips at once, one per Google account,
# each in its own tab. Never twice the same account at once, so a reservation is never made twice on the same credits.
def parallel_cap():
    try:return max(1,min(4,int(STATE.get('settings',{}).get('parallel_flow',4))))
    except (TypeError,ValueError):return 2
def video_tasks(j): return [t for t in STATE['tasks'] if t['job']==j['id'] and t['status'] in ('queued','claimed') and lane_of(t)=='video']
def video_slots(j):
    if engines.of(j)!='flow' or j['config'].get('dry_run') or not STATE.get('settings',{}).get('flow_auto') or not STATE.get('settings',{}).get('parallel_clips',True):return 1
    return parallel_cap()
def busy_flow_profiles(): return {t.get('profile') for t in STATE['tasks'] if t.get('kind') in ('flow_video','flow_collect') and t['status'] in ('queued','claimed') and t.get('profile')}

class AccountsNotReady(ValueError):
    """« Comptes à régler avant de commencer »: nothing is launched; the page shows the list and a link to Mes comptes."""
    def __init__(self,blockers):
        self.blockers=blockers;super().__init__('Comptes à régler avant de commencer : '+readiness.describe(blockers)+'. Règle-les dans Mes comptes.')

def gate_blockers(j,setup=True):
    """Known reasons not to start this production now (first step: accounts added; then nothing known « À régler »)."""
    eligible=lambda p:flow_accounts.eligible(STATE,p)
    stage = j.get('stage', 'research')
    out = readiness.setup_missing(STATE) if setup and stage != 'clips' else []
    return out+readiness.blockers(STATE,j['config'],stage,int(j['config'].get('flow_cost',12)),time.time(),eligible,j.get('flow_profile'))

def window_online():
    return any(client_online(c) and c.get('role','all') in ('all','flow') for c in STATE['clients'].values())

def request_readiness(sites,profiles,background=False,job=None):
    """Ask the FruchtDrama window to read these services and Flow accounts (read only: no credit, no prompt)."""
    rid=uid();targets=[readiness.profile_target(p,flow_accounts.account_home) for p in STATE['profiles']
                      if p['id'] in profiles and p.get('flow_url') and not flow_accounts.offline_route(STATE,p)]
    queue=STATE.setdefault('bridge_requests',[])
    if not job:queue[:]=[r for r in queue if not (r.get('type')=='readiness' and not r.get('job'))]  # one owner check waiting at most
    queue.append({'type':'readiness','id':rid,'sites':list(sites),'profiles':targets,'background':bool(background),**({'job':job} if job else {})})
    r=readiness.store(STATE);r['requested']=now()
    r['pending']=list(dict.fromkeys(r.get('pending',[])+['site:'+n for n in sites]+['flow:'+x['id'] for x in targets]))
    return rid

def start_check(j):
    """Before a production starts: read what is not known recently. True when it may start right away."""
    need=readiness.checks_needed(STATE,j['config'],j.get('stage','research'),int(j['config'].get('flow_cost',12)),time.time(),lambda p:flow_accounts.eligible(STATE,p))
    if not (need['sites'] or need['profiles']) or not window_online():return True
    j['accounts_check']={'at':now(),'id':request_readiness(need['sites'],need['profiles'],job=j['id']),
                        'pending':['site:'+n for n in need['sites']]+['flow:'+p for p in need['profiles']]}
    names=[readiness.SITE_LABELS[n] for n in need['sites']]+(['compte(s) Google Flow'] if need['profiles'] else [])
    event(j,'Vérification des comptes en parallèle ('+', '.join(names)+'), sans crédit ni prompt : la production démarre tout de suite.');return True

def end_check(j,timeout=False):
    """The check came back (or never did): start, or stop cleanly with the list of accounts to fix."""
    j.pop('accounts_check',None)
    if j.get('status')!='running':return
    if timeout:
        event(j,'Vérification des comptes sans réponse : un compte qui ne répond pas sera écarté pendant la production.');return
    found=gate_blockers(j,setup=False)
    if found:
        j['status']='attention';alert(j,'action','Comptes à régler avant de commencer : '+readiness.describe(found)+'. Ouvre Mes comptes, « Régler maintenant », puis Reprendre.');return
    event(j,'Comptes vérifiés : tous prêts.');schedule(j)

def readiness_tick(moment=None):
    moment=moment or time.time();changed=False
    r=readiness.store(STATE)
    if r.get('pending') and moment-flow_credits.seconds(r.get('requested'))>readiness.CHECK_TIMEOUT:
        r['pending']=[];changed=True
        STATE['bridge_requests']=[x for x in STATE.get('bridge_requests',[]) if x.get('type')!='readiness' or x.get('job')]
    for j in STATE['jobs']:
        c=j.get('accounts_check')
        if c and moment-flow_credits.seconds(c.get('at'))>readiness.CHECK_TIMEOUT:end_check(j,timeout=True);changed=True
    return changed

COVER_REVIEW_PROMPT=('Review the attached TikTok COVER image. Do not generate an image. Check: the title text is fully visible, '
    'spelled correctly in {language} and readable on a phone; no cut-off face or text; no extra limbs or deformed faces; the characters look like '
    'the story cast ({cast}); nothing looks like a watermark or a logo. Output JSON only: '
    '{{"production_id": "{job}", "generation_task_id": "...", "ok": true}} if it can be published, or the same with "ok": false and '
    '"problem": "one short sentence saying exactly what to fix".')

def cover_check_pending(j):
    """Atelier "Miniature de la boucle complète": ChatGPT looks at the cover once (one attachment) and it is redrawn once
    when it sees a defect ('fix'), or the defect is only reported ('report'). True while the check holds the montage back."""
    mode=j['config'].get('cover_controls',STATE.get('settings',{}).get('cover_controls','fix'))
    if mode=='none' or not j.get('cover_file') or j.get('cover_checked')==j['cover_file']:return False
    if j.get('autopilot') and j.get('cover_review_unavailable')==j['cover_file']:return False
    review=j.get('cover_review')
    if not review or review.get('file')!=j['cover_file']:
        if any(t['job']==j['id'] and t['slot']=='cover_review' and t['status'] in ('queued','claimed') for t in STATE['tasks']):return True
        cast=', '.join(c.get('name','') for c in j.get('characters',[]))
        add_task(j,'chat_text',{'provider':'chatgpt','prompt':COVER_REVIEW_PROMPT.format(language=j['config'].get('language',''),cast=cast,job=j['id']),
                                'attachments':[asset_url(j,j['cover_file'])],'response_kind':'cover_review','file':j['cover_file']},'cover_review');return True
    j['cover_checked']=j['cover_file']
    if review['ok']:event(j,'Miniature regardée par ChatGPT : rien à corriger.');return False
    if mode=='fix' and not j.get('cover_fixed'):
        j['cover_fixed']=True;j.setdefault('redo_history',[]).append({'slot':'cover','file':j.pop('cover_file'),'note':'contrôle de la miniature','at':now()});j.pop('cover',None)
        j.setdefault('corrections',{})['cover']='Cover check: '+review['problem']+' Fix this, keep everything else.'
        event(j,'Miniature redessinée une fois après le contrôle : '+review['problem']);schedule(j);return True
    alert(j,'auto','Miniature : défaut signalé par ChatGPT — '+review['problem']+' Vérifie-la avant de publier.');return False

def readable_progress(text,slot=None):
    # The extension reports the scenario reader's raw diagnostic; the owner sees a sentence instead.
    if text.startswith('Diagnostic import Flow'):return 'Import de la planche dans Flow…'
    prefix='Lecture du scénario : '
    if not text.startswith(prefix+'{'):return text
    review={'cover_review':'la miniature','quality_review':'les clips','board_review':'les planches'}.get(slot)
    if review:return 'Lecture de la réponse du contrôle sur '+review+' en cours.'
    try:d=json.loads(text[len(prefix):])
    except ValueError:return 'Lecture de la réponse de l’IA en cours.'
    if d.get('parsedScenes'):return f"Scénario reçu ({d['parsedScenes']} scènes) : vérification en cours."
    if d.get('hasJob') or d.get('hasTask'):return 'L’IA écrit le scénario ; réponse pas encore complète.'
    return 'En attente de la réponse de l’IA.'

def take_over(c):
    """An automatic gateway left switched off at pairing (the old one was running a task, then disappeared:
    extension reloaded, real case 06/11/2026) takes over once no other automatic gateway is online."""
    alive=[x for x in STATE['clients'].values() if x is not c and x.get('auto') and not x.get('disabled') and time.time()-flow_credits.seconds(x.get('seen'))<STALL_ONLINE]
    if alive:return False
    for x in STATE['clients'].values():
        if x is not c and x.get('auto'):x['disabled']=True
    c['disabled']=False;flow_accounts.follow_active_browser(STATE);rebind_flow_routes();return True

def clock(ts,moment=None):
    """Local time for the owner (« 15:42 », « demain 08:10 »), never UTC."""
    moment=moment or time.time();at=dt.datetime.fromtimestamp(ts);day=(at.date()-dt.datetime.fromtimestamp(moment).date()).days
    return ('demain ' if day==1 else at.strftime('%d/%m ') if day>1 else '')+at.strftime('%H:%M')
def clock_in(ts,moment=None):
    """« 15:42 (dans 28 min) »: when it comes back, said in local time with the remaining wait."""
    moment=moment or time.time();left=max(0,int((ts-moment+59)//60))
    return clock(ts,moment)+(' (dans '+(f'{left//60} h {left%60:02d}' if left>=60 else f'{left} min')+')' if left else '')

def client_online(c,limit=None):
    return bool(c) and not c.get('disabled') and time.time()-flow_credits.seconds(c.get('seen'))<(limit or STALL_ONLINE)

def rebind_flow_routes():
    """Queued Flow work follows its account to the browser that now holds it (real case 06/11/2026).

    A queued clip and a queued balance check carried the pairing of the moment they were prepared: after the
    extension was reinstalled the new FruchtDrama window, online in the same Chrome, never accepted them and
    the studio tried to open Chrome instead. Claimed work keeps its browser: it may already be in Flow."""
    flow_accounts.follow_active_browser(STATE);moved=0
    for t in STATE['tasks']:
        route=(t.get('payload') or {}).get('flow_route')
        if t.get('status')!='queued' or t.get('kind') not in ('flow_video','flow_collect') or not route:continue
        p=profile_by(t.get('profile'))
        if t['kind']=='flow_video' and p and flow_accounts.offline_route(STATE,p):
            t['status']='cancelled';t['cancel_reason']='offline_route';moved+=1
            event(job_by(t['job']),'Clip '+str(int(t['slot'].split(':')[1])+1)+' : ancienne fenêtre Flow hors ligne ; tâche non envoyée libérée pour un compte disponible, aucun crédit réservé.')
            continue
        if p and p.get('flow_client') and route.get('client')!=p['flow_client']:
            route['client']=p['flow_client'];t.pop('browser_opened',None);moved+=1
    for p in STATE['profiles']:
        probe=p.get('credit_probe')
        if probe and probe.get('status')=='queued' and p.get('flow_client') and probe.get('client')!=p['flow_client']:
            probe['client']=p['flow_client'];probe['target']={**probe.get('target',{}),'client':p['flow_client']};probe.pop('browser_opened',None);moved+=1
    return moved

def release_dead_chat(c):
    """Texts and boards claimed by a FruchtDrama window that is gone (reinstalled extension: new pairing, the old one
    never answers again) are asked again by the window that works now, instead of « Relancer cette étape ».
    Chat lane only: no Flow credit is ever at stake; clips keep the owner's check."""
    if not c.get('auto') or c.get('disabled'):return 0
    released=0
    for t in STATE['tasks']:
        if t['status']!='claimed' or lane_of(t)!='chat' or t.get('client')==c['id']:continue
        old=STATE['clients'].get(t.get('client'))
        if old and (not old.get('auto') or client_online(old)):continue
        j=job_by(t['job'])
        if not j:continue
        t['status']='failed';t['error']='Fenêtre FruchtDrama disparue : étape redemandée par la nouvelle fenêtre.';released+=1
        event(j,'La fenêtre qui faisait « '+t['slot']+' » ne répond plus : la fenêtre FruchtDrama en ligne la reprend (aucun crédit Flow).')
        if j.get('status')=='running':schedule(j)
    return released

def release_job_chat(j,reason):
    """Queued tasks of this episode, and its chat-lane tasks in progress, are cancelled (the window clears its binding)."""
    freed=0
    for t in STATE['tasks']:
        if t['job']!=j['id'] or t['status'] not in ('queued','claimed'):continue
        if t['status']=='claimed' and lane_of(t)!='chat':continue
        t['status']='cancelled';t['error']=reason;freed+=1
    return freed

# A chat-lane task (text, board, research) claimed for longer than this without any news is considered lost
# (window reloaded, tab closed): it is cancelled and asked again, instead of blocking every episode (owner 09/11/2026).
CHAT_LOST_MINUTES={'chat_text':20,'chat_collect':10,'chat_image':15,'chat_image_collect':10,'tiktok_search':15}

def release_lost_chat(moment=None):
    moment=moment or time.time();released=0
    for t in STATE['tasks']:
        if t['status']!='claimed' or lane_of(t)!='chat':continue
        last=max(flow_credits.seconds(t.get('claimed')) or 0,flow_credits.seconds(t.get('progress_at')) or 0)
        if not last or moment-last<CHAT_LOST_MINUTES.get(t.get('kind'),20)*60:continue
        j=job_by(t['job'])
        t['status']='cancelled';t['error']='Tâche sans nouvelles : redemandée';released+=1
        if j:
            event(j,f"« {t['slot']} » sans nouvelles depuis {CHAT_LOST_MINUTES.get(t.get('kind'),20)} min (fenêtre rechargée ou onglet fermé) : étape redemandée, les autres épisodes ne l’attendent plus.")
            if j.get('status')=='running':schedule(j)
    return released

def event_all(text):
    for j in STATE['jobs']:
        if j.get('status') not in ('done',) and not j.get('filon_only') and any(t['job']==j['id'] and t['status'] in ('queued','claimed') for t in STATE['tasks']):event(j,text)

def alert(j,level,text):
    # Shown as a banner at the top of the episode: 'action' = the owner must act, 'auto' = decided alone, to check.
    event(j,text);alerts=j.setdefault('alerts',[]);alerts.append({'at':now(),'level':level,'text':text});del alerts[:-6]
STALL_ONLINE=180  # seconds without a heartbeat: the FruchtDrama window is considered gone
STALL_QUIET={'chat_text':12,'chat_collect':6,'chat_image':10,'chat_image_collect':6,'research':12,'flow_video':20,'engine_video':45}  # minutes (Arena: up to 40 min, real test 06/11/2026)
ENGINE_STALL_QUIET={'grok':8,'vidogrid':12,'arena':45}
SERVICE={'chatgpt':'ChatGPT','claude':'Claude'}

def stall_info(j,moment=None):
    """Why a running episode does not move, said plainly (owner 05/11/2026: « on doit voir pourquoi la vidéo ne progresse pas »).
    None while things move normally."""
    if j.get('status')!='running' or j.get('filon_only'):return None
    moment=moment or time.time()
    def ago(at):
        try:return moment-dt.datetime.fromisoformat(at).timestamp()
        except (TypeError,ValueError):return None
    claimed=[t for t in STATE['tasks'] if t['job']==j['id'] and t['status']=='claimed']
    # Two lanes may work at once: each active task is looked at; the first one that does not move is said.
    for task in claimed+[t for t in STATE['tasks'] if t['job']==j['id'] and t['status']=='queued']:
        info=task_stall(j,task,moment,ago,len(claimed)>1)
        if info:return {**info,'task':task['id']}
    return None

def task_stall(j,task,moment,ago,shared):
    kind=task.get('kind','');service=SERVICE.get((task.get('payload') or {}).get('provider'),'Google Flow' if kind=='flow_video' else engines.ENGINES.get((task.get('payload') or {}).get('engine'),{}).get('label','Grok, Arena ou Vidogrid') if kind=='engine_video' else 'le site')
    online=[c for c in STATE['clients'].values() if not c.get('disabled') and (ago(c.get('seen')) or 1e9)<STALL_ONLINE]
    paid=kind in ('flow_video','engine_video')
    retry_note=('Vérifie d’abord dans '+service+' si le clip a été créé : le relancer peut coûter des crédits.' if paid else 'Relancer renvoie la demande à '+service+' (aucun crédit Flow).')
    if task['status']=='queued':
        route=(task.get('payload') or {}).get('flow_route')
        if route and not client_online(STATE['clients'].get(route.get('client'))):
            return {'reason':'Le compte de ce clip est affecté à une fenêtre Flow hors ligne.',
                    'hint':'Détecter mes comptes dans la fenêtre ouverte permet de retrouver les comptes disponibles.','retry':False,'since':task.get('created')}
        if not online:
            return {'reason':'Aucune fenêtre FruchtDrama n’est ouverte : l’étape attend qu’une fenêtre se connecte.','hint':'Ouvre la fenêtre FruchtDrama (icône épinglée), l’étape repart toute seule.','retry':False,'since':task.get('created')}
        return None
    client=STATE['clients'].get(task.get('client')) or {}
    gone=ago(client.get('seen'))
    if client.get('disabled') or gone is None or gone>=STALL_ONLINE:
        when=dt.datetime.fromisoformat(client['seen']).astimezone().strftime('%H:%M') if client.get('seen') else '?'
        return {'reason':f'La fenêtre FruchtDrama qui faisait cette étape ne répond plus depuis {when} (fermée, rechargée ou extension mise à jour) : sa réponse ne viendra pas.',
                'hint':retry_note,'retry':True,'paid':paid,'since':client.get('seen')}
    # With both lanes active, the other lane's news must not hide this one's silence: its own progress only.
    news=ago(task.get('progress_at')) if shared else ago((j.get('events') or [{}])[-1].get('at'))
    last=min([x for x in (ago(task.get('claimed')),news) if x is not None],default=None)
    limit=STALL_QUIET.get(kind,12)
    if kind=='engine_video':
        limit=ENGINE_STALL_QUIET.get((task.get('payload') or {}).get('engine'),limit)
    if last is not None and last>=limit*60:
        return {'reason':f'Aucune nouvelle de {service} depuis {int(last//60)} min : l’onglet attend peut-être une connexion, une vérification anti-robot, ou la réponse s’est arrêtée.',
                'hint':'Regarde l’onglet '+service+' dans la fenêtre FruchtDrama. '+retry_note,'retry':True,'paid':paid,'since':task.get('claimed')}
    return None

def public_state(light=False):
    account_usage.number_flow(STATE)  # « Compte 1, 2, 3… » stable, before the copy
    s=copy.deepcopy({k:v for k,v in STATE.items() if k not in ('token','tasks')})
    s['tasks']=[]
    for source in STATE['tasks']:
        t={k:v for k,v in source.items() if k not in ('result','payload')}
        if not light:
            t['payload']=source.get('payload',{})
        elif source['status'] in ('queued','claimed'):
            t['payload']={k:v for k,v in source.get('payload',{}).items() if k in ('prompt','query')}
        t=copy.deepcopy(t)
        if t.get('progress'):t['progress']=readable_progress(t['progress'])
        s['tasks'].append(t)
    for public,j in zip(s['jobs'],STATE['jobs']):
        for e in public.get('events',[]):e['text']=readable_progress(e['text'])
        public['uncertain_clips']=sorted({int(t['slot'].split(':')[1]) for t in uncertain_clip_tasks(j)})
        public['stall']=stall_info(j)
    s['quota_status']=quotas.summary(STATE,time.time());s['version']=VERSION
    s['usage']=account_usage.view(STATE)  # which account works now, on which AI, for what (0.1.95)
    s['accounts']=identities.view(STATE,time.time(),int(STATE['settings'].get('flow_cost',12)));s.pop('extension_origin',None)
    s['setup']=readiness.setup_missing(STATE);s.setdefault('readiness',{'sites':{},'pending':[]})
    s['key_saved']=bool(STATE['clients'])  # an extension holds the key once it has paired, manually or automatically
    s['ffmpeg']=bool(shutil.which('ffmpeg'))
    s['character_styles']=character_styles.options()
    try:s['extension_version']=json.loads((ROOT/'extension'/'manifest.json').read_text('utf-8')).get('version')
    except (OSError,ValueError):s['extension_version']=None
    s['licence']=LICENCE.view()
    s['montage']=montage.validate({},STATE['settings'].get('montage'));s['montage_summary']=montage.summary(s['montage'])
    root=backups_root();s['backups']={'folder':str(root),'count':len(story_backup.listing(root))}
    return s
def safe_child(parent, name):
    target=(parent/name).resolve()
    if target==parent.resolve() or parent.resolve() not in target.parents: raise ValueError('Chemin interdit')
    return target
def backups_root():
    # Outside the studio folder, like the Atelier (Téléchargements › atelier › sauvegardes): survives a reinstall.
    if os.environ.get('FRUCHT_BACKUPS'):return pathlib.Path(os.environ['FRUCHT_BACKUPS'])
    if DATA!=(ROOT/'data').resolve():return DATA/'histoires-sauvegardees'  # tests and side installs keep them local
    home=pathlib.Path.home();downloads=next((home/x for x in ('Téléchargements','Downloads') if (home/x).is_dir()),home)
    return downloads/'FruchtDrama'/'sauvegardes'
def backup_story(j):
    try:
        if story_backup.save(j,job_dir(j),backups_root()):j['backed_up']=now()
    except Exception as e:log_error('Sauvegarde de l’histoire',e)
def job_dir(j):
    d=safe_child(DATA/'jobs',j['id']); d.mkdir(parents=True,exist_ok=True); return d
def asset_url(j, file): return f"/media/{j['id']}/{file}"

def refill_check(at=None):
    """A Flow account's daily credits are due: ask the window to read every balance again (at most every 10 min)."""
    at=at or time.time()
    if not flow_refill.due(STATE['profiles'],at) or at-STATE.get('refill_requested',-1e9)<600:return False
    queue=STATE.setdefault('bridge_requests',[])
    # background: done only while the FruchtDrama window is open (closing it must not reopen it).
    if not any(r.get('type')=='scan_flow' for r in queue):queue.append({'type':'scan_flow','background':True})
    # A balance that cannot be read (window closed, session expired) is asked again in an hour, not every 10 min.
    for p in flow_refill.due(STATE['profiles'],at):p['refill_at']=at+flow_refill.RETRY
    STATE['refill_requested']=at;save();return True

def flow_dispatch_tick():
    """Wake only the one browser needed for the next queued Flow clip.

    A FruchtDrama window that answers is never doubled (real case 06/11/2026): queued work follows the accounts
    to it (rebind_flow_routes) and nothing is launched. Chrome is started, in the background and without a
    window, only when no FruchtDrama window answers at all and a production needs it."""
    pending=None
    with LOCK:
        if not STATE.get('settings',{}).get('flow_auto'):return
        if rebind_flow_routes():save()
        if any(t['kind'] in ('flow_video','flow_collect') and t['status']=='claimed' for t in STATE['tasks']):return
        for j in STATE['jobs']:
            if j['stage']=='clips' and j['status']=='waiting_credit':
                if flow_accounts.choose(STATE,j.get('flow_profile'),j['config']['flow_cost']):j['status']='running'
            if j['status']=='running':schedule(j)
        refill_check()
        window=any(client_online(c) and c.get('role','all') in ('all','flow') for c in STATE['clients'].values())
        task=next((t for t in STATE['tasks'] if t['kind']=='flow_video' and t['status']=='queued' and job_by(t['job'])['status']=='running'),None)
        if not task:
            p=flow_credits.prepare(STATE,time.time())
            if not p:return
            probe=p['credit_probe'];client=STATE['clients'].get(probe['client'],{})
            # A balance check never opens anything while a window answers, nor for a background reading.
            if window or probe.get('background') or client_online(client):save();return
            if probe.get('browser_opened'):return
            probe['browser_opened']=now();pending=copy.deepcopy(p);save()
        else:
            target=task['payload'].get('flow_route');p=profile_by(task.get('profile'))
        if not task:
            try:flow_accounts.launch(pending)
            except Exception as e:
                # The launch runs outside the lock; record its failure on the live profile under the lock.
                with LOCK:
                    live=profile_by(pending['id'])
                    if live and live.get('credit_probe',{}).get('id')==pending['credit_probe']['id']:
                        live['credit_error']='Ouverture Flow impossible : '+str(e);live['credit_probe']['status']='failed';live['credit_next_check']=flow_credits.stamp(time.time()+900);save()
            return
        if not target or not p:return
        if client_online(STATE['clients'].get(target['client'])):return
        j=job_by(task['job'])
        if window:
            # A window answers but this account is held by another, silent browser (several browsers paired):
            # said once, nothing opened; the task goes as soon as that browser answers or the accounts are detected again.
            if not task.get('route_wait'):
                task['route_wait']=now();event(j,'Le compte Flow '+target.get('email','')+' est mémorisé par une autre fenêtre FruchtDrama, hors ligne : ouvre-la, ou clique « Détecter mes comptes » (Mes comptes) dans la fenêtre en ligne.');save()
            return
        if task.get('browser_opened'):return  # once per task; the episode keeps waiting, the bandeau « Bloqué » says why
        task['browser_opened']=now();pending=copy.deepcopy(p);event(j,'Aucune fenêtre FruchtDrama ouverte : Chrome démarre en arrière-plan, la fenêtre reprendra le clip sans passer au premier plan.');save()
    try:flow_accounts.launch(pending)
    except Exception as e:
        with LOCK:
            # Nothing to resume by hand: the clip stays queued and leaves as soon as a FruchtDrama window opens.
            event(job_by(task['job']),'Chrome non démarré ('+str(e)+'). Le clip attend : il part dès que la fenêtre FruchtDrama est ouverte.');save()

LAST_ERRORS={}
def log_error(context,error,interval=60):
    """Write a traceback to stderr (data/server-errors.log), at most once per interval for the same error."""
    key=(context,type(error).__name__,str(error));moment=time.time()
    if moment-LAST_ERRORS.get(key,0)<interval:return False
    LAST_ERRORS[key]=moment
    print(f'[{now()}] {context} : '+''.join(traceback.format_exception(type(error),error,error.__traceback__)),file=sys.stderr,flush=True)
    return True

def wake_waiting(moment=None):
    """P5-08: productions waiting for a quota renewal resume by themselves."""
    moment=moment or time.time();woken=[]
    with LOCK:
        for j in STATE['jobs']:
            if j.get('status')=='waiting_quota' and (j.get('wait_until') or 0)<=moment:
                j['status']='running';j.pop('wait_until',None);j.pop('quota_lane',None);event(j,'Limite renouvelée : reprise automatique.');schedule(j);woken.append(j['id'])
        if woken:save()
    return woken

# P2-10/P2-11: night queue. One production at a time, bounded automatic retries, owner decisions respected.
NIGHT_ACTIVE=('running','rendering','waiting_quota','waiting_credit')
NIGHT_HUMAN={'waiting_review':'histoire à relire','waiting_research':'références à choisir','waiting_script':'scénario à fournir','waiting_account':'changement de compte à faire','paused':'mise en pause par vous'}
def night():
    return STATE.setdefault('night',{'active':False,'ids':[],'failures':{},'retry_at':{},'log':[]})

def night_log(text):
    n=night();n['log'].append({'at':now(),'text':text});n['log']=n['log'][-50:]

def night_drop(j,reason):
    n=night();n['ids'].remove(j['id']);n['failures'].pop(j['id'],None);n['retry_at'].pop(j['id'],None)
    night_log(j.get('title','Production')+' : retirée de la file, '+reason+'.');event(j,'File de nuit : production retirée ('+reason+').')

def night_add(j):
    n=night()
    if j['id'] in n['ids']:raise ValueError('Déjà dans la file de nuit')
    if j['status']=='done':raise ValueError('Production déjà terminée')
    if j['config'].get('dry_run'):raise ValueError('File de nuit interdite en essai à blanc : désactivez-le d’abord')
    if j['status'] in NIGHT_HUMAN and j['status']!='paused':raise ValueError('Action humaine requise d’abord : '+NIGHT_HUMAN[j['status']])
    if any(t['job']==j['id'] and t['status']=='claimed' for t in STATE['tasks']):raise ValueError('Une tâche est en cours : attendez sa fin')
    for t in STATE['tasks']:
        if t['job']==j['id'] and t['status']=='queued':t['status']='cancelled'
    n['ids'].append(j['id']);j['status']='waiting_night';event(j,'Ajoutée à la file de nuit : démarrera à son tour.')

def night_remove(j):
    n=night()
    if j['id'] not in n['ids']:raise ValueError('Pas dans la file de nuit')
    night_drop(j,'retirée par vous')
    if j['status']=='waiting_night':j['status']='paused'

def night_tick(moment=None):
    moment=moment or time.time();n=night()
    if not n['active']:return
    for id in list(n['ids']):
        j=job_by(id)
        if not j:n['ids'].remove(id);continue
        if j['status']=='done':night_drop(j,'terminée');continue
        if j['status'] in NIGHT_HUMAN:night_drop(j,NIGHT_HUMAN[j['status']]);continue
        if j['status']=='attention':
            kind=(j.get('last_error') or {}).get('kind')
            if kind in errors.RETRYABLE and not uncertain_clip_tasks(j) and j.get('stage')!='quality' and n['failures'].get(id,0)<3:
                n['failures'][id]=n['failures'].get(id,0)+1;n['retry_at'][id]=moment+120*n['failures'][id]
                n['ids'].remove(id);n['ids'].append(id);j['status']='waiting_night'
                night_log(j.get('title','Production')+' : échec réessayable ('+kind+'), nouvel essai '+str(n['failures'][id])+'/3 plus tard.')
            else:night_drop(j,'a besoin de vous : '+(j['events'][-1]['text'][:160] if j['events'] else 'à vérifier'))
    if any(job_by(id)['status'] in NIGHT_ACTIVE for id in n['ids']):return
    for id in n['ids']:
        j=job_by(id)
        if j['status']=='waiting_night' and n['retry_at'].get(id,0)<=moment:
            for t in STATE['tasks']:
                if t['job']==id and t['status']=='queued':t['status']='cancelled'
            j.pop('last_error',None);j['status']='running';event(j,'File de nuit : production lancée.');night_log(j.get('title','Production')+' : lancée.');schedule(j);return
    if not n['ids']:
        n['active']=False;night_log('File de nuit terminée.')

def night_once():
    with LOCK:
        before=json.dumps(STATE.get('night'),sort_keys=True,default=str)
        night_tick()
        if json.dumps(STATE.get('night'),sort_keys=True,default=str)!=before:save()
        active=night()['active']
    power.sync(active)  # same long-lived dispatch thread every time

FILON_EVERY=2*3600
# Atelier "Mes niches": each niche has its own TikTok search; Fruits keeps the historical queries.
# Search words per niche: French, German, English, Spanish, Portuguese (Brazil).
NICHE_WORDS={'Animaux':('animaux','Tiere','animal','animales','animais'),'Chats':('chats','Katzen','cat','gatos','gatos'),'Bébés':('bébé','Baby','baby','bebé','bebê'),
             'Gourmandises':('gourmandises','Süßigkeiten','sweets','dulces','doces'),'Cartoon':('cartoon','Cartoon','cartoon','caricatura','desenho'),
             'Survie':('survie','Survival','survival','supervivencia','sobrevivência'),'Créatures':('créatures','Kreaturen','creature','criaturas','criaturas'),
             'Avatar humain':('avatar humain','Avatar Mensch','human avatar','avatar humano','avatar humano'),'Brainrot':('brainrot','Brainrot','brainrot','brainrot','brainrot'),
             'Construction':('construction','Bau','construction','construcción','construção'),'Jeux vidéo':('jeux vidéo','Videospiele','video game','videojuegos','videogame')}
def niche_name(value):
    name=' '.join(str(value or '').split())  # too long is refused, never cut silently
    if not re.fullmatch(r"[\w'’ \-]{2,30}",name):raise ValueError('Nom de niche invalide')
    return name
def niche_query(niche,language):
    if niche=='Fruits':return RESEARCH_QUERIES[language]
    fr,de,en,es,pt=NICHE_WORDS.get(niche,(niche,)*5)
    return {'Français (fr-FR)':f'histoire {fr} IA','Deutsch (de-DE)':f'{de} KI Geschichte','English (en-US)':f'AI {en} story',
            'Español (es-ES)':f'historia {es} IA','Português (pt-BR)':f'história {pt} IA'}[language]
def filon_refresh(language=None,niche=None):
    """Start a research-only job that refreshes Le Filon (no story, no paid generation)."""
    if any(j.get('filon_only') and j['status'] not in ('done','attention','paused') for j in STATE['jobs']):raise ValueError('Actualisation du Filon déjà en cours')
    cfg={**STATE['settings']};cfg['language']=creation_language(language or cfg.get('language','Deutsch (de-DE)'))
    cfg['filon_niche']=niche_name(niche or cfg.get('filon_niche') or 'Fruits');cfg['query']=niche_query(cfg['filon_niche'],cfg['language'])
    j={'id':uid(),'title':'Actualisation du Filon','brief':'','config':cfg,'filon_only':True,'status':'running','stage':'research','created':now(),'updated':now(),'events':[],'candidates':[],'characters':[],'scenes':[],'flow_profile':None}
    STATE['jobs'].append(j);schedule(j);STATE['settings']['filon_attempted']=j['created'];return j

def filon_tick(moment=None):
    moment=moment or time.time();s=STATE.get('settings',{})
    if not s.get('filon_auto'):return None
    try:last=dt.datetime.fromisoformat(max(s.get('filon_attempted',''),s.get('filon_refreshed',''))).timestamp()
    except ValueError:last=0
    if moment-last<FILON_EVERY:return None
    try:return filon_refresh()
    except ValueError:return None

def dispatch_once():
    try:
        with LOCK:
            if filon_tick():save()
    except Exception as e:log_error('Filon automatique',e)
    try:night_once()
    except Exception as e:log_error('File de nuit',e)
    try:wake_waiting()
    except Exception as e:log_error('Réveil des productions en attente',e)
    try:
        with LOCK:
            if release_lost_chat():save()
    except Exception as e:log_error('Tâches sans nouvelles',e)
    try:
        with LOCK:
            if readiness_tick():save()
    except Exception as e:log_error('Vérification des comptes',e)
    try:flow_dispatch_tick()
    except Exception as e:
        # An unavailable account must not stop the HTTP server, but the failure must stay diagnosable.
        log_error('Boucle de dispatch Flow',e)

def flow_dispatch_loop():
    while True:
        dispatch_once()
        time.sleep(3)
def image_assets(j):
    # A shared character sheet is attached once, not once per character.
    return list(dict.fromkeys(asset_url(j,p['file']) for p in j.get('characters',[]) if p.get('file')))

def sheet_prompt(j):
    cast='\n'.join(f"- {c['name']} ({c['id']}): {c['appearance']}. {c['image_prompt']}" for c in j['characters'])
    return ('Create ONE character reference sheet image containing every character below, side by side, full body, front view, '
            'same scale, neutral light background, consistent premium 3D animation style, portrait 9:16. '
            +(('CHARACTER STYLE (every character): '+character_styles.get(j)['make']+' ') if (j.get('config') or {}).get('character_style') else '')+
            'Each character appears exactly once, clearly separated, with a small plain name label under each one. '
            'No other text, no scene, no props unless part of the outfit.\n'
            # Atelier "Personnages : Détaillé": richer sheet so every board keeps the same details.
            +('Detailed sheet: for each character add a three-quarter view and a face close-up next to the full body, '
              'and make the skin texture, outfit, accessories and distinctive marks clearly readable.\n' if j['config'].get('characters_detail')=='detailed' else '')
            +cast)

def state_changes(j): return (j.get('script') or {}).get('state_changes') or []

def state_sheets_enabled(j):
    # Like the Atelier: « Normale » makes state sheets, « Économie » does not.
    return (j.get('config') or {}).get('quality')!='economy'

def state_entry(j,change):
    return next((x for x in j.get('state_sheets') or [] if x.get('character')==change['character'] and x.get('from_scene')==change['from_scene']),None)

def slot_of_state(j,entry):
    k=next((k for k,c in enumerate(state_changes(j)) if c['character']==entry.get('character') and c['from_scene']==entry.get('from_scene')),None)
    return f'state:{k}' if k is not None else 'state'

def state_reference(j,character,scene_number):
    """State sheet of this character in force at this scene (numbered from 1), or None."""
    rows=[x for x in j.get('state_sheets') or [] if x.get('character')==character and x.get('file') and x.get('from_scene',0)<=scene_number]
    return max(rows,key=lambda x:x['from_scene'],default=None)

def state_base(j,change):
    """Image the state sheet is drawn from: an earlier state sheet of the same character, else its reference."""
    earlier=state_reference(j,change['character'],change['from_scene']-1)
    if earlier:return earlier['file']
    return next((c.get('file') for c in j.get('characters',[]) if c['id']==change['character']),None)

def state_needed(j,change):
    """A state sheet is paid only if a board from its scene on, with this character, is still to draw."""
    if not state_sheets_enabled(j) or state_entry(j,change) or not state_base(j,change):return False
    return any(change['character'] in (s.get('characters') or []) and not s.get('image') for s in (j.get('scenes') or [])[change['from_scene']-1:])

def state_sheet_prompt(j,change):
    c=next(c for c in j['characters'] if c['id']==change['character'])
    earlier=state_reference(j,change['character'],change['from_scene']-1)
    return ('Redraw the attached character reference image exactly: same characters, same layout, same poses, same scale, '
            'same background, same premium 3D animation style and the same small name labels, portrait 9:16. '
            f"Change ONLY {c['name']} ({c['id']}): {change['change']}. "
            +(f"Keep the earlier visible change of {c['name']}: {earlier['change']}. " if earlier else '')
            +'Every other character and every other detail stays identical. No other text.')

def scene_references(j,i):
    """Board i: from its scene on, a character's state sheet replaces the reference sheet (same look all along)."""
    scene=j['scenes'][i];states=[]
    for c in j.get('characters',[]):
        st=state_reference(j,c['id'],i+1) if c['id'] in (scene.get('characters') or []) else None
        if st and st not in states:states.append(st)
    if not states:return image_assets(j),[]
    sheet=j.get('character_sheet_file');files=[x['file'] for x in states]
    for c in j.get('characters',[]):
        # A state sheet of the shared sheet shows the whole cast: the old sheet would contradict it.
        if c.get('file') and not any(x['character']==c['id'] for x in states) and not (sheet and c['file']==sheet):files.append(c['file'])
    return list(dict.fromkeys(asset_url(j,f) for f in files)),states

def state_note(j,states):
    if not states:return ''
    names={c['id']:c['name'] for c in j.get('characters',[])}
    return ' Changed look from this scene on (shown in the attached updated sheet, keep it): '+'; '.join(f"{names.get(x['character'],x['character'])}: {x['change']}" for x in states)+'.'

FINGERPRINTS={}

def image_fingerprint(j,file):
    # Cached per file version: the startup duplicate check compares every pair of images.
    path=safe_child(job_dir(j),file);info=path.stat();key=(str(path),info.st_size,info.st_mtime_ns)
    if key not in FINGERPRINTS:FINGERPRINTS[key]=decode_fingerprint(path)
    return FINGERPRINTS[key]

def decode_fingerprint(path):
    from PIL import Image
    with Image.open(path) as image:
        if image.width*image.height>17000000:raise ValueError('Image trop grande')
        image.load()
        rgb=image.convert('RGB')
        return (rgb.size,hashlib.sha256(rgb.tobytes()).hexdigest())

def flow_reference(j,file):
    from PIL import Image, ImageOps
    source=safe_child(job_dir(j),file)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()[:20]
    target=job_dir(j)/f'flow_reference_{digest}.jpg'
    if not target.exists():
        with Image.open(source) as original:
            if original.width*original.height>17000000:raise ValueError('Image trop grande')
            image=ImageOps.exif_transpose(original).convert('RGBA')
            image.thumbnail((1280,1280),Image.Resampling.LANCZOS)
            background=Image.new('RGB',image.size,'white');background.paste(image,mask=image.getchannel('A'))
            background.save(target,'JPEG',quality=90,optimize=True)
    return target.name

def import_browser_download(j,t,info):
    download_id=info.get('download_id')
    if not isinstance(download_id,int) or isinstance(download_id,bool) or download_id<0:raise ValueError('Identifiant de téléchargement invalide')
    previous=t.get('download_import')
    if previous and previous['id']==download_id and (job_dir(j)/previous['file']).is_file():return previous['file']
    if previous:raise ValueError('Un autre téléchargement est déjà associé à cette tâche')
    source=pathlib.Path(str(info.get('filename',''))).resolve()
    if DOWNLOADS_ROOT not in source.parents:raise ValueError('Le fichier doit provenir du dossier Téléchargements')
    if source.suffix.lower() not in ('.mp4','.webm') or not source.is_file():raise ValueError('Fichier vidéo téléchargé absent')
    size=source.stat().st_size
    if not 0<size<=100*1024*1024 or size!=info.get('size'):raise ValueError('Taille du téléchargement invalide')
    claimed=dt.datetime.fromisoformat(t['claimed']).timestamp()
    if source.stat().st_mtime<claimed-120:raise ValueError('Ce fichier est antérieur à la récupération demandée')
    probe=shutil.which('ffprobe')
    if not probe:raise ValueError('ffprobe requis pour valider les clips téléchargés')
    result=subprocess.run([probe,'-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','json',str(source)],capture_output=True,text=True,timeout=20)
    if result.returncode:raise ValueError('Le fichier téléchargé n’est pas une vidéo lisible')
    metadata=json.loads(result.stdout);streams=metadata.get('streams',[]);video=next((x for x in streams if x.get('codec_type')=='video'),{})
    if not 4<=float(metadata.get('format',{}).get('duration',0))<=12 or (video.get('height',0)>video.get('width',0))==horizontal(j) or not any(x.get('codec_type')=='audio' for x in streams):raise ValueError('Le clip doit être vertical, durer environ huit secondes et contenir de l’audio')
    name=t['slot'].replace(':','_')+'_'+uid()+source.suffix.lower();shutil.copyfile(source,job_dir(j)/name)
    t['download_import']={'id':download_id,'file':name};return name

def duplicate_scene_source(j,file,index):
    fingerprint=image_fingerprint(j,file)
    sources=[c.get('file') for c in j.get('characters',[])]+[x.get('file') for x in j.get('state_sheets') or []]+[s.get('image') for i,s in enumerate(j.get('scenes',[])) if i!=index]
    for source in sources:
        if source and fingerprint==image_fingerprint(j,source):return source
    return None

def repair_duplicate_scenes(j):
    invalid=[]
    for i,scene in enumerate(j.get('scenes',[])):
        file=scene.get('image')
        if file and duplicate_scene_source(j,file,i):invalid.append((i,file))
    if not invalid:return 0
    if any(t['job']==j['id'] and t['status']=='claimed' for t in STATE['tasks']):
        raise ValueError('Attendez la fin de la tâche en cours avant de réparer les scènes')
    (job_dir(j)/f'repair_backup_{uid()}.json').write_text(json.dumps(j,ensure_ascii=False,indent=2),'utf-8')
    for i,file in invalid:
        j.setdefault('invalid_images',[]).append({'scene':i,'file':file,'reason':'Image identique à une référence ou à une autre scène','at':now()})
        j['scenes'][i].pop('image',None)
        for t in STATE['tasks']:
            if t['job']==j['id'] and t['slot']==f'image:{i}' and t['kind']=='chat_image' and t['status']=='done':
                t['status']='failed';t['error']='Image de référence capturée à la place de la scène'
    for t in STATE['tasks']:
        if t['job']==j['id'] and t['status']=='queued':t['status']='cancelled'
    j['stage']='images';j['status']='attention'
    event(j,f'{len(invalid)} images de scène incorrectes mises de côté ; fichiers conservés. Récupération des images originales à effectuer avant animation.')
    return len(invalid)

def rank_candidates(rows,language='Deutsch (de-DE)'):
    valid=[]
    for r in rows[:100]:
        url=str(r.get('url','')); u=urllib.parse.urlparse(url)
        if u.hostname not in ('www.tiktok.com','tiktok.com') or not re.fullmatch(r'/@[^/]+/video/\d+',u.path): continue
        item={'url':f'https://www.tiktok.com{u.path}','title':str(r.get('title',''))[:1500], 'observed_at':now()}
        for k in ('views','likes','signal'):
            v=r.get(k)
            item[k]=float(v) if type(v) in (int,float) and 0<=v<1e12 else None
        item['date']=str(r.get('date',''))[:40]
        thumb=urllib.parse.urlparse(str(r.get('thumb','')))
        # Filon gallery: TikTok CDN covers only, never arbitrary hosts.
        item['thumb']=str(r.get('thumb'))[:2000] if thumb.scheme=='https' and thumb.hostname and re.search(r'(?:^|\.)(?:tiktokcdn(?:-[a-z]+)?\.com|ibyteimg\.com|tiktok\.com)$',thumb.hostname) else None
        age=None
        try: age=max(1,(dt.datetime.now(dt.timezone.utc).date()-dt.date.fromisoformat(item['date'][:10])).days)
        except ValueError: pass
        item['age_days']=age
        text=item['title'].lower()
        words={'Deutsch (de-DE)':['deutsch','frücht','frucht','ki','story','geschichte'], 'Français (fr-FR)':['français','francais','fruit','histoire','ia','drame'], 'English (en-US)':['english','fruit','story','stories','ai','drama'], 'Español (es-ES)':['español','fruta','historia','ia','drama'], 'Português (pt-BR)':['português','fruta','história','ia','drama']}.get(language,[])
        relevance=sum(w in text for w in words)
        # Never relabel unknown search counters as views.
        metric=item['views'] if item['views'] is not None else item['likes'] if item['likes'] is not None else item['signal']
        item['score']=(metric or 0)/(age or 30)*(1+relevance*.12)
        item['metric_kind']='views' if item['views'] is not None else 'likes' if item['likes'] is not None else 'unknown'
        item['basis']='vues/jour' if item['views'] is not None and age else 'vues' if item['views'] is not None else 'mentions J’aime' if item['likes'] is not None else 'compteur affiché non identifié'
        valid.append(item)
    unique={}
    priority={'views':2,'likes':1,'unknown':0}
    for r in valid:
        previous=unique.get(r['url'])
        if not previous or priority[r['metric_kind']]>=priority[previous['metric_kind']]:unique[r['url']]=r
    return sorted(unique.values(),key=lambda r:({'views':2,'likes':1,'unknown':0}[r['metric_kind']],r['score']),reverse=True)

# Rich plans (06/11/2026, seen in the Atelier's real production): each scene says what the image shows, what the viewer
# learns, the framing, the camera, three actions (the last one closes the shot), how each line is acted and who stays
# silent; each character has a distinctive mark and a fixed place in the frame. The server turns them into the image
# and clip prompts, so every planche and every clip carries the same direction.
def _txt(v,limit=400):return ' '.join(str(v or '').split())[:limit]
def cast_place(j,cid):
    c=next((c for c in j.get('characters',[]) if c.get('id')==cid),{})
    return _txt(c.get('place'),120)
def scene_lettering(s):
    mark=_txt(s.get('critical_mark'),180)
    if mark:
        return 'The only permitted lettering is the following exact in-world mark, readable on its specified surface: '+mark+'. No subtitles, overlays, logos or watermarks.'
    return 'No text, letters, numbers, subtitles, logos or watermarks.'

def plan_image_block(j,s):
    script=j.get('script') or {}
    parts=[]
    if s.get('montre'):parts.append('WHAT THE IMAGE SHOWS: '+_txt(s['montre'],600))
    if s.get('cadre'):parts.append('FRAMING: '+_txt(s['cadre'],300))
    if s.get('deplacement'):parts.append('STARTING FRAME: show starting positions and leave room for this route: '+_txt(s['deplacement'],300))
    place=(script.get('lieux') or {}).get(s.get('lieu')) if isinstance(script.get('lieux'),dict) else None
    if place:parts.append('PLACE: '+_txt(place,300))
    if script.get('lieu'):parts.append('WORLD: '+_txt(script['lieu'],300))
    names={c.get('id'):c.get('name') for c in j.get('characters',[])}
    visible=[names[cid] for cid in s.get('characters',[]) if names.get(cid)]
    if visible:parts.append('ONLY THESE CHARACTERS ARE VISIBLE: '+', '.join(visible))
    marks=[f"{c.get('name')}: {_txt(c.get('tenue'),120)}; {_txt(c.get('detail'),120)}; {_txt(c.get('place'),120)}" for c in j.get('characters',[]) if c.get('id') in s.get('characters',[]) and (c.get('detail') or c.get('place'))]
    if marks:parts.append('CHARACTER COSTUME, DISTINCTIVE MARK AND USUAL STARTING POSITION: '+' | '.join(marks))
    if s.get('actions'):parts.append('Catch the moment of: '+_txt((s['actions'] or [''])[0],200)+' Faces show the emotion strongly (exaggerated, readable on a phone).')
    said=[f"{names.get(x.get('speaker'),x.get('speaker'))} says « {_txt(x.get('text'),160)} »"+(f" ({_txt(x.get('jeu'),80)})" if x.get('jeu') else '') for x in s.get('dialogue',[])]
    if parts and said:parts.append('THE FACES PLAY THESE LINES (do not print the dialogue): '+' / '.join(said))
    if parts:parts.append(('HOW THEY ARE MADE: the fruit is the WHOLE body (head, face, neck, arms, hands, fingers), four fingers per hand, fully clothed in ordinary covering clothes, no human, no human skin. ' if not (j.get('config') or {}).get('character_style') else 'HOW THEY ARE MADE: '+character_styles.get(j)['make']+' Fully clothed in ordinary covering clothes. ')+
                          'The attached sheet rules faces, species, proportions and outfits; a character who is not on the sheet does not exist in this image. '
                          'ONE single shot filling the whole frame edge to edge, like a still from the film. '+scene_lettering(s))
    return ('\n'+'\n'.join(parts)) if parts else ''
def plan_video_block(j,s):
    parts=[]
    if s.get('camera'):parts.append('CAMERA: '+_txt(s['camera'],200))
    acts=[_txt(a,200) for a in (s.get('actions') or []) if _txt(a)]
    if acts:parts.append('ACTIONS IN ORDER (the last one closes the shot): '+' / '.join(acts))
    if s.get('deplacement'):
        parts.append('CHARACTER MOVEMENT: '+_txt(s['deplacement'],300)+'. Follow the moving character in one continuous shot. Keep the speaker’s face readable while they speak.')
    silent=set(s.get('characters') or [])-{line['speaker'] for line in s.get('dialogue',[])}
    mute=[c['name'] for c in j.get('characters',[]) if c.get('id') in silent]
    if mute:parts.append('SILENT, MOUTH CLOSED: '+', '.join(mute))
    parts.append('Use the gestures specified for this shot. Silent characters react with eyes, brows and hands, lips closed. Only add tears, sweat or screams when explicitly directed. Start from the positions shown in the reference frame. Preserve identity and outfit as characters move. Deliver the exchange at a natural pace with clear turns.')
    parts.append(scene_lettering(s))
    return '\n'+'\n'.join(parts)
def plan_mute_block(j,s):
    silent=set(s.get('characters') or [])-{line['speaker'] for line in s.get('dialogue',[])}
    mute=[c['name'] for c in j.get('characters',[]) if c.get('id') in silent]
    return ('\nSILENT, MOUTH CLOSED: '+', '.join(mute) if mute else '')+scene_lettering(s).join(['\n',''])

def dialogue_lines(j,s):
    out=[]
    for x in s['dialogue']:
        where=cast_place(j,x['speaker']);acting=_txt(x.get('jeu'),80)
        out.append(x['speaker']+(f' ({where})' if where and not s.get('deplacement') else '')+(f' [{acting}]' if acting else '')+': '+x['text'])
    return '\n'.join(out)

SIZE_WORDS={'énorme','énormes','gros','grosse','grosses','géant','géante','géants','immense','immenses','obèse','huge','big','fat','giant','enormous','riesig','enorme','gordo','gorda','gigante'}

def size_problems(chars):
    out=[]
    for c in chars:
        found=sorted({w for w in re.findall(r"[\w’']+",' '.join(str(c.get(k,'')) for k in ('detail','tenue')).lower()) if w in SIZE_WORDS})
        if found:out.append(f"Le détail de {c.get('name','un personnage')} : « {', '.join(found)} » fait grossir le personnage dans la vidéo. Décris le détail sans parler de sa taille.")
    return out

def validate_script(s, n, check_size=True, word_limit=25, max_chars=5):
    if not isinstance(s,dict): raise ValueError('Objet JSON attendu')
    chars=s.get('characters',[]); scenes=s.get('scenes',[])
    # Name the count actually received: the rewrite request and the journal must say what to fix.
    if not 1<=len(chars)<=max_chars: raise ValueError(f'{len(chars)} personnage(s) reçu(s), il en faut 1 à {max_chars} : fusionner ou retirer les personnages secondaires')
    if len(scenes)!=n: raise ValueError(f'{len(scenes)} scène(s) reçue(s), il en faut exactement {n}')
    def character_id(value):
        return value.strip().lower() if isinstance(value,str) else ''
    ids=[character_id(c.get('id')) for c in chars]
    if len(set(ids))!=len(ids) or any(not re.fullmatch('[a-z][a-z0-9_]{0,24}',x) for x in ids):
        raise ValueError('Identifiants personnages invalides : utilise des identifiants uniques comme fruit_a, identiques dans les scènes et les dialogues.')
    for c, cid in zip(chars, ids):
        c['id']=cid
        if not all(isinstance(c.get(k),str) and c[k].strip() for k in ['name','appearance','voice','image_prompt']): raise ValueError('Fiche personnage incomplète')
    for scene in scenes:
        if not all(isinstance(scene.get(k),str) and scene[k].strip() for k in ['image_prompt','video_prompt','meaning']): raise ValueError('Prompt ou sens de scène manquant')
        lines=scene.get('dialogue',[])
        for line in lines:line['speaker']=character_id(line.get('speaker'))
        for key in ('characters','muets'):
            if isinstance(scene.get(key),list):scene[key]=[character_id(x) for x in scene[key]]
        if not lines or any(x.get('speaker') not in ids or not isinstance(x.get('text'),str) or not x['text'].strip() for x in lines): raise ValueError('Dialogue ou locuteur invalide')
        if not set(scene.get('characters',[])).issubset(ids) or not scene.get('characters'): raise ValueError('Distribution de scène invalide')
        if any(x['speaker'] not in scene['characters'] for x in lines): raise ValueError('Locuteur absent de la scène')
        mark=scene.get('critical_mark')
        if isinstance(mark,str) and mark.strip():scene['critical_mark']=_txt(mark,180)
        else:scene.pop('critical_mark',None)
        movement=scene.get('deplacement')
        if isinstance(movement,str) and movement.strip():scene['deplacement']=_txt(movement,300)
        else:scene.pop('deplacement',None)
        if check_size and sum(len(x['text'].split()) for x in lines)>word_limit: raise ValueError(f'Dialogue trop long pour ce clip ({word_limit} mots maximum)')
    for k in ['title','cover_title','description']:
        if not isinstance(s.get(k),str) or not s[k].strip(): raise ValueError('Titre, couverture ou description manquant')
    # Seen in the Atelier's checks (06/11/2026): size words in a character's distinctive mark make the video engine
    # inflate the whole character. Refused with the exact words, so the rewrite fixes only that.
    if check_size:
        problems=size_problems(chars)
        if problems:raise ValueError(' ; '.join(problems))
    # Optional extra: a wrong entry is dropped, it never refuses the script.
    changes=clean_state_changes(s.get('state_changes'),ids,n)
    if changes:s['state_changes']=changes
    else:s.pop('state_changes',None)
    return s

STATE_CHANGES_MAX=3

def clean_state_changes(raw,ids,n):
    """« Au fil de l'histoire »: visible changes of a character from one scene on (wound, torn outfit, lost object).
    Tolerant: invalid, duplicate or extra entries are ignored; at most three, ordered by scene."""
    if not isinstance(raw,list):return []
    clean=[];seen=set()
    for x in raw:
        if not isinstance(x,dict):continue
        scene=x.get('from_scene')
        if isinstance(scene,str) and scene.strip().isdigit():scene=int(scene.strip())
        if isinstance(scene,bool) or not isinstance(scene,int) or not 1<=scene<=n:continue
        character=x.get('character')
        if isinstance(character,str):character=character.strip().lower()
        change=' '.join(str(x.get('change') or '').split())[:200] if isinstance(x.get('change'),str) else ''
        if character not in ids or not change or (character,scene) in seen:continue
        seen.add((character,scene));clean.append({'from_scene':scene,'character':character,'change':change})
    return sorted(clean[:STATE_CHANGES_MAX],key=lambda x:x['from_scene'])

def repair_json(text):
    """A ChatGPT reply read as page text: code fences and their labels, typographic quotes around keys, trailing commas.
    Returns the JSON object text bound to the task (from its first « { » to the matching last « } »)."""
    s=str(text)
    s=re.sub(r'^\s*(?:json|JSON)\s*(?:\n|Copier le code|Copy code|Code kopieren)+','',s)
    s=re.sub(r'```(?:json)?','',s)
    start=s.find('{');end=s.rfind('}')
    if start<0 or end<start:return s
    body=s[start:end+1]
    try:json.loads(body);return body
    except ValueError:pass
    fixed=re.sub(r'[“”]','"',body)
    fixed=re.sub(r',\s*([}\]])',r'\1',fixed)
    try:json.loads(fixed);return fixed
    except ValueError:return body

def parse_json(text):
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',str(text).strip())
    start=text.find('{'); end=text.rfind('}')
    if start<0 or end<start: raise ValueError('La réponse ne contient pas de JSON')
    return json.loads(text[start:end+1])

def translation_prompt(j):
    """Language version (Atelier "Langues"): same story, same boards, new lines and voices."""
    language=j['config']['language'];source=copy.deepcopy(j['variant']['script'])
    for k in ('production_id','generation_task_id','creative_selection','opening_plan'):source.pop(k,None)
    source['production_id']=j['id']
    return f'''Traduis et adapte ce scénario de mini-fiction de fruits dans la langue : {language}. Garde exactement la même structure JSON, les mêmes identifiants de personnages, le même nombre de scènes, les mêmes locuteurs et le même sens. Adapte naturellement les répliques (pas de mot à mot), le titre, cover_title (3 à 5 mots) et la description (mentionne la création par IA). Les prénoms peuvent être adaptés à la langue. Garde des échanges naturels, avec au plus {engines.word_limit(j)} mots par scène. Les champs image_prompt et video_prompt restent tels quels, sauf la langue parlée indiquée dans video_prompt. Réponds UNIQUEMENT avec le JSON. JSON : {json.dumps(source,ensure_ascii=False)}'''

PLAN_RULES='''
PLANS (règles de mise en scène) :
- Chaque plan apporte une information NEUVE (champ apporte) et sert l’histoire (champ sert) ; aucun plan de remplissage.
- Commence le plan sur un geste ou un indice visible et termine-le avec une conséquence nouvelle. Varie le cadrage entre plans voisins. Une action principale lisible sur téléphone suffit. Alterne les moments immobiles et les déplacements motivés par l’histoire : entrer, suivre quelqu’un, traverser jusqu’à une porte ou s’approcher pour intervenir. Dans deplacement, indique qui bouge, son départ et sa destination. Prévois un cadrage qui laisse la place dès la première image.
- Décris ce qui est visible par des consignes positives. Réserve les larmes, cris et gouttes de sueur aux plans qui les justifient. Un personnage silencieux réagit avec les yeux, les sourcils ou les mains, bouche fermée.
- La dernière action de chaque plan est un geste qui ferme le plan et appelle le suivant (porte qui s’ouvre, objet qui tombe, regard choqué vers…) : c’est la transition.
- Chaque réplique va au personnage qui parle vraiment à l’image ; les autres personnages présents sont dans muets. Chaque réplique a son jeu (comment elle est dite).
- Limite la distribution visible à deux personnages quand la scène le permet, trois si l'action en a besoin. Dans les prompts de rendu, décris uniquement les personnages présents. Distingue les voix par leur énergie et leur timbre. Écris des phrases courtes et idiomatiques dans la langue cible, qui répondent à un geste ou à la réplique précédente.
- Chaque personnage garde sa tenue et son détail reconnaissable. La place dans le cadre indique le départ et peut évoluer si le plan prévoit un déplacement.
- Dans une scène de dialogue, vise environ trois quarts du budget de mots ou davantage si l’échange le mérite. Écris des phrases parlées complètes et propres à chaque personnage. Fais réagir au geste ou à la réplique précédente, avec des objections, des hésitations et du sous-texte selon l’enjeu. Fais coïncider les paroles et l’action sans accélérer la diction.
- detail et tenue ne parlent JAMAIS de taille (interdits : énorme, gros, géant, immense, obèse, big, huge, giant…) : le moteur vidéo grossirait tout le personnage. Décris la forme, la couleur, la matière.
- critical_mark est facultatif. Si une inscription ou un chiffre joue un rôle dans l'intrigue, indique sa valeur exacte et son support (objet ou personnage et emplacement) dans chaque plan où il doit être lisible. Reprends-le dans les deux prompts du plan. Si le signe est caché à ce moment de l'histoire, omets le champ. Les sous-titres sont ajoutés au montage.
- Réserve state_changes aux modifications physiques qui restent visibles d'un plan à l'autre. Une émotion momentanée va dans montre et actions.
'''

FLOW_SCENE_RULES='''
PRÉPARATION POUR FLOW :
- Écris des personnages fictifs originaux et invente leurs vêtements, accessoires et décors. Ne demande ni ressemblance avec une personne réelle, ni personnage de franchise, logo, imitation de voix réelle ou reproduction reconnaissable d’une planche existante.
- Fais porter le conflit par une décision, un objet original, un silence ou un désaccord. Pour une scène tendue, montre l’urgence et les réactions avec une mise en scène tous publics. Si un élément pose problème, change réellement l’action ou le visuel avant de produire la planche.
- La première image doit permettre de tourner l’action prévue. Choisis un trajet simple et une caméra qui peut suivre le personnage sans coupe. Garde le visage lisible pendant ses paroles.
'''

def is_identical(j):
    return ((j.get('selected') or {}).get('source')=='owner_link' and j['config'].get('recreate')=='identical')

def correction_ready(j):
    return bool(j.get('rejected_script') and j.get('editorial_feedback'))

def correction_prompt(j):
    """Light rewrite, like the Atelier's « corrige et renvoie l'épisode ENTIER »: the refused script and its defects,
    without the source images. A full rewrite took 5 to 7 min each time (real case 06/11/2026, 4 refusals = 47 min)."""
    sheet=j.get('sheet') or {}
    choices=j.get('sheet_choice') or {}
    approved=ideas.brief(sheet,choices.get('title',0),choices.get('hook',0),choices.get('call',0)) if j.get('sheet_approved') and sheet else ''
    return ('Voici un scénario JSON refusé par le contrôle avant les images. Défauts à corriger : '
            +json.dumps(j['editorial_feedback'],ensure_ascii=False)
            +('\n'+approved+' Place uniquement les paroles dans dialogue[0].text.\n' if approved else '')
            +'\nCorrige UNIQUEMENT les défauts signalés. Conserve le nombre de scènes et la langue. Pour un défaut de longueur, raccourcis seulement les répliques concernées. Pour un détail visible manquant, reprends exactement opening_plan.visible_detail dans les deux prompts de la première scène. Ne remplace pas le scénario par une seule scène. '
            'Pas de mots de taille (énorme, gros, géant, immense…) dans detail et tenue. Tout le reste reste identique.\n'
            'Renvoie le JSON ENTIER corrigé, seul, sans commentaire, dans un bloc ```json.\n\n```json\n'
            +json.dumps({k:v for k,v in j['rejected_script'].items() if k not in ('production_id','generation_task_id')},ensure_ascii=False)+'\n```')

def script_prompt(j):
    if (j.get('variant') or {}).get('kind')=='language':return translation_prompt(j)
    if correction_ready(j):return correction_prompt(j)
    ref=j['selected']; n=j['config']['scene_count']
    language=j['config'].get('language','Deutsch (de-DE)')
    schema={'production_id':j['id'],'title':'Titre dans la langue choisie','cover_title':'Question courte dans la langue choisie','hook_text':'Accroche écrite à l’écran pendant les 3 premières secondes : 4 à 7 mots, question ou promesse choc, sans révéler la fin','description':'Description TikTok dans la langue choisie, mentionnant la création par IA','lieu':'LE MONDE DE TOUT L’ÉPISODE, une fois : époque, lumière, matières ; sans enseignes ni logos','lieux':{'CUISINE':'la pièce décrite pour un dessinateur'},'su_du_public':'ce que le spectateur VOIT avant les personnages','cliffhanger':'la dernière réplique','characters':[{'id':'fruit_a','name':'Prénom dans la langue choisie','role':'protagoniste | antagoniste | témoin','appearance':'âge, corps selon le STYLE DES PERSONNAGES imposé (matière, couleur, signe), vêtements précis, attitude','tenue':'la tenue en quelques mots, toujours la même','detail':'LE détail reconnaissable de loin (ex. une mèche blanche sur le front)','place':'sa position de départ habituelle dans le cadre vertical : « À DROITE — la prune violette en sweat gris »','voice':'Voix native de la langue choisie, âge, timbre, ton','veut':'ce qu’il veut','image_prompt':'Prompt de référence dans la langue choisie'}],'scenes':[{'title':'Titre court du plan (2 à 4 mots, MAJUSCULES, langue choisie)','sert':'moteur | obstacle | aggravation | twist | revanche | appel','apporte':'ce que le spectateur apprend de NEUF dans ce plan, une phrase','lieu':'CUISINE','characters':['fruit_a'],'muets':['personnages présents qui ne parlent pas'],'meaning':'Action compréhensible sans le son','montre':'CE QUE L’IMAGE MONTRE, en majuscules : qui, où, quel geste, quel objet, quelle émotion exagérée','cadre':'PLAN TAILLE / GROS PLAN… : qui est où dans le cadre vertical','camera':'ce que fait la caméra, quelques mots','actions':['ACTION 1.','ACTION 2.','LE GESTE QUI FERME LE PLAN et appelle le suivant.'],'image_prompt':'Prompt d’image dans la langue choisie, 9:16','video_prompt':'Animation, caméra, action, position des locuteurs, lèvres et personnages silencieux','dialogue':[{'speaker':'fruit_a','text':'Réplique naturelle dans la langue choisie, avec une intention claire','jeu':'3 à 6 mots de jeu : « dans un souffle, les mains sur la bouche »'}]}],'state_changes':[{'from_scene':2,'character':'fruit_a','change':'Changement d’apparence visible à partir de cette scène (blessure, vêtement déchiré, objet perdu, maquillage coulé…), langue choisie'}]}
    guidance=''
    owner_link=(ref or {}).get('source')=='owner_link'
    identical=owner_link and j['config'].get('recreate')=='identical'
    # Use the same dialogue budget in the prompt and in validation.
    word_limit=engines.word_limit(j)
    schema['scenes'][0]['deplacement']='Facultatif : personnage, point de départ, trajet et destination'
    if identical:
        # A faithful remake never receives the originality rules (five new concepts, history to avoid): they made the
        # writer invent another story (real case 05/11/2026: a maid hiding her poverty became two sisters and a pendant).
        # Moteur V09 (09/11/2026): not the retention rules either (they rewrite the opening); the V09 rules come with the
        # reference below. Each scene keeps the time of the source it reproduces.
        guidance=''
        schema['scenes'][0]={'ref':'00:00-00:10 (temps de la source reproduit par cette scène ; vide pour l’appel final)',**schema['scenes'][0]}
    elif j.get('editorial_version')==2:
        if not j.get('sheet_approved'):
            schema['creative_selection']={'candidates':[{'title':'Titre du concept','hook':'Première réplique','conflict':'Conflit','setting':'Décor','twist':'Retournement','ending':'Fin','scores':{'hook':4,'clarity':4,'emotion':4,'novelty':5}} for _ in range(5)],'selected_index':0,'reason':'Justification éditoriale, pas une prédiction de vues'}
        if j.get('hook_version')==1:
            schema['opening_plan']={'visible_detail':'Objet ou geste visible dès la première image','question':'Question laissée ouverte par la première réplique','payoff_scene':n,'payoff':'Explication concrète apportée dans cette scène'}
        schema['story_signature']={'relationship':'short English relationship','setting':'short English setting','central_object':'short English object','twist_mechanism':'short English plot mechanism'}
        guidance=editorial.instructions(j,STATE['jobs'])+'\nRéférences comparées : '+json.dumps(j.get('candidates',[])[:6],ensure_ascii=False)+'\nCorrections demandées : '+json.dumps(j.get('editorial_feedback',[]),ensure_ascii=False)
    else:guidance=editorial.STORY_CRAFT
    if identical and j.get('editorial_feedback'):guidance+='\nCorrections demandées : '+json.dumps(j['editorial_feedback'],ensure_ascii=False)
    if not identical:
        # Moteur V09: these rules ask for new framings, invented outfits and settings: never in a faithful copy.
        guidance+=PLAN_RULES
        if engines.of(j)=='flow' or engine_chain.flow_grok_policy(STATE.get('settings'),j['config']) or engine_chain.v09_policy(STATE.get('settings'),j['config']):
            guidance+=FLOW_SCENE_RULES
    schema['scenes'][0]['critical_mark']='Facultatif : inscription exacte et emplacement précis sur un objet ou un personnage, seulement si nécessaire à l’intrigue'
    if not identical:
        guidance+=(
            '\nDramaturgie : suis un seul protagoniste et rends visible ce qu’il veut dès l’ouverture. '
            'Place l’anomalie dans les cinq premiers mots de la première réplique. Montre la règle qui fait obstacle par une action. '
            'Sème une fois un indice concret, puis fais-le payer près de la fin par un seul retournement. '
            'Le retournement se voit avant d’être expliqué. La dernière scène montre sa conséquence et donne au protagoniste '
            'une chute brève, puis l’appel validé si la fiche en prévoit un. '
            'Pour une suite, pars de l’état final établi dans l’épisode précédent.'
        )
    if j.get('sheet_approved'):
        guidance+=(
            '\nFiche validée : garde le conflit, le retournement, la première réplique et l’appel choisis. '
            'Découpe-les en actions visibles. Fais apparaître un indice concret avant la révélation, '
            'puis montre ce qui change pour le personnage après cette révélation. '
            'Dans un dialogue, chaque réponse doit réagir au geste ou à la phrase qui la précède. '
            'Prévois le geste et la place du locuteur dans le cadre. Répartis les répliques trop longues '
            'sur les scènes disponibles, sans ajouter de plans ni dépasser la durée prévue. '
            'Avant de rendre le JSON, relis le scénario dans l’ordre : si un objet change de main, '
            'si un vêtement est retiré ou si un signe physique est dévoilé, indique la première scène '
            'où ce changement est visible dans state_changes et conserve-le dans les scènes suivantes. '
            'Dans la fiche du personnage, décris son apparence de départ. '
            'Dans le dernier plan, prononce l’appel choisi avec le personnage prévu. '
            'Dans dialogue[0].text, écris uniquement les paroles de la première réplique, sans le nom du locuteur ni son jeu.'
        )
    reference=(source_video.guidance(j['config'].get('recreate','inspired'),j.get('source_analysis'),len(j.get('source_captures') or []),n,clip_seconds=engines.spec(j)['seconds'],language=language,style=character_styles.get(j))+(f"\nInstructions en plus du propriétaire (à respecter) : {j['brief']}" if j.get('brief','').strip() else '')) if owner_link else None
    style=character_styles.get(j)
    style_rule=(f" STYLE DES PERSONNAGES IMPOSÉ pour cette vidéo : {style['writer']}. Chaque personnage suit ce style (aucun autre style, aucun humain réaliste sauf si le style est humain), avec un détail qui le distingue des autres ; nom : {style['name_rule']}. Décris ce corps dans appearance et dans chaque image_prompt.")
    return f'''Crée une mini-fiction animée {'qui refait fidèlement la vidéo indiquée' if identical else 'entièrement ORIGINALE'}. Langue demandée pour les dialogues, les voix, les textes de couverture, la description et les prompts (sauf les clés techniques et la signature narrative) : {language}. La langue demandée prime sur la langue française des instructions et des descriptions du schéma. Aucune traduction ni réplique dans une autre langue. Les personnages parlent avec des voix natives de la langue demandée. Réponds UNIQUEMENT avec du JSON valide, sans explication. Conserve les clés techniques du schéma en anglais. {reference if reference else 'Référence comme indice de tendance seulement, jamais copier les répliques ou les plans : '+json.dumps(ref,ensure_ascii=False)+'.'} Idée : {j['brief']}. Exactement {n} scènes de {engines.spec(j)['seconds']} secondes, {'les mêmes personnages que la vidéo d’origine (8 au plus : laisse en figurant muet les rôles sans réplique)' if identical else '2 à 5 personnages (au moins 3 quand l’histoire le permet : héros, adversaire, témoin ou figurant)'}. Au plus {word_limit} mots parlés par scène pour les langues avec espaces ; dans toutes les langues, vérifie que la scène peut être jouée au rythme naturel dans la durée du clip. {'Les répliques de l’original dans la fenêtre de la scène, au plus quatre répliques et trois locuteurs par scène.' if identical else 'Jusqu’à trois répliques, avec au maximum deux locuteurs par scène.'} {'HOOK : garde l’ouverture de la vidéo d’origine (elle a déjà prouvé qu’elle accroche) ; sa première réplique, traduite fidèlement, est dite dans la première seconde ; hook_text pose une question résolue seulement à la fin.' if identical else 'HOOK OBLIGATOIRE : la scène 1 s’ouvre sur l’instant le plus fort (danger, injustice, secret révélé), la première réplique est une phrase choc de moins de 10 mots dite dans les 2 premières secondes, et hook_text pose une question résolue seulement à la fin.'} {'Cadrages, mouvements de caméra, gestes et lieux : ceux de l’original, plan par plan (aucun lieu ni plan ajouté).' if identical else 'Mouvement : chaque scène a un cadrage différent (gros plan, plan large, plongée), un mouvement de caméra motivé (travelling, panoramique, zoom), des gestes précis et un arrière-plan vivant par les objets, la lumière ou la météo ; au moins deux lieux différents dans l’épisode.'} Retournement visible, conclusion satisfaisante. Pas de présentation comme fait réel. Animation 3D premium, personnages dans le style imposé ci-dessous, vêtements couvrants sans logos, grands visages expressifs, {'mêmes décors que la vidéo d’origine' if identical else 'décor cohérent avec l’intrigue choisie et différent des épisodes récents'}, vertical 9:16. Même identité et tenue partout, aucune voix de narrateur, personnages parlant à l'écran, caméra en mouvement continu dans chaque clip. Sous-titres ajoutés au montage.{style_rule} {guidance} Champ state_changes FACULTATIF : seulement si l’histoire change vraiment l’apparence visible d’un personnage (blessure, vêtement déchiré, objet perdu, maquillage coulé…), de 0 à 3 entrées, from_scene = numéro de la première scène (1 à {n}) où le changement se voit, character = identifiant du personnage, change = description courte ; sinon une liste vide []. Le champ cover_title doit être une accroche de couverture de 3 à 5 mots maximum dans la langue demandée, sans révéler la fin. Schéma : {json.dumps(schema,ensure_ascii=False)}'''

def horizontal(j): return (j.get('config') or {}).get('format')=='horizontal'
def frame_size(j): return (1920,1080) if horizontal(j) else (1080,1920)  # best resolution for TikTok (owner priority)

def normalize_flow_resolution(cfg):
    """Our Omni Flash/Lite Flow connectors generate in native 720p; export size is separate.

    Also protects jobs sent by an already-open older form and restored productions.
    Keep the requested value as evidence instead of letting an unsupported setting block paid work.
    """
    if cfg.get('flow_model') in engines.NATIVE_720 and cfg.get('flow_resolution')=='1080p':
        cfg['flow_resolution_requested']='1080p';cfg['flow_resolution']='720p';return True
    return False
def check_publish_size(probe,path,expected):
    """The exported video must be exactly 1080p (1080 x 1920 or 1920 x 1080); never hand over a smaller one."""
    if not probe:return
    out=subprocess.run([probe,'-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','csv=p=0',str(path)],capture_output=True,text=True,timeout=30).stdout.strip()
    try:size=tuple(int(x) for x in out.split(',')[:2])
    except ValueError:size=None
    if size!=tuple(expected):raise ValueError(f'Vidéo finale en {out or "?"} au lieu de {expected[0]} × {expected[1]} : export refusé, relancez le montage.')
def landscape(text):
    """Horizontal 16:9 version (Atelier-like): the same prompts, turned to landscape."""
    text=re.sub(r'portrait 9:16','landscape 16:9',str(text));text=text.replace('9:16','16:9')
    return re.sub(r'\bvertical\b','horizontal',re.sub(r'\bportrait\b','landscape',text))

def add_task(j, kind, payload, slot, profile=None):
    if horizontal(j) and kind in ('chat_image','flow_video','engine_video') or (horizontal(j) and kind=='chat_text' and slot=='script'):
        payload={**payload,'prompt':landscape(payload.get('prompt','')),'aspect':'16:9'}
    if kind=='chat_image' and j.get('refusal_levels',{}).get(slot):
        # P2-05: an image refused by ChatGPT is reworded, level by level.
        payload={**payload,'prompt':refusal.soften(payload['prompt'],j['refusal_levels'][slot]),'refusal_level':j['refusal_levels'][slot]}
    if any(t['job']==j['id'] and t['slot']==slot and t['status'] in ('queued','claimed') for t in STATE['tasks']): return
    name=quotas.service({'kind':kind,'payload':payload})
    if name:
        moment=time.time();q=quotas.status(STATE,name,moment)
        if q['blocked']:
            # P2-07: nothing is sent while the service is at its limit; the production resumes by itself.
            j['status']='waiting_quota';j['wait_until']=q['retry_at'];j['quota_lane']=lane_of({'kind':kind,'slot':slot})
            event(j,q['label']+' à sa limite'+(' (délai annoncé par le service)' if q.get('announced') else '')+' : nouvel essai automatique à '+clock_in(q['retry_at'])+'.'+(' Les clips des planches déjà dessinées continuent.' if kind=='chat_image' and j.get('stage')=='images' else ''));return
    if kind=='chat_text' and payload.get('provider')=='claude':
        # The extension selects this model and effort in claude.ai before sending (older episodes: defaults).
        payload={**payload,**{k:j.get('config',{}).get(k) or CLAUDE_DEFAULTS[k] for k in CLAUDE_DEFAULTS}}
    t={'id':uid(),'job':j['id'],'kind':kind,'payload':payload,'slot':slot,'status':'queued','created':now(),'profile':(profile or j.get('flow_profile')) if kind=='flow_video' else None}
    STATE['tasks'].append(t); j['status']='running'; event(j,f"Tâche préparée : {slot}")

def cover_prompt(j):
    if j.get('cover_style')=='family_poster_v3':return covers.family_poster_prompt(j)
    language=j['config'].get('language','Deutsch (de-DE)')
    title=j['script']['cover_title']
    cast='\n'.join(c['name']+': '+c['appearance'] for c in j['characters'])
    return f"""Create one finished premium TikTok cover image, portrait 9:16, preferably 1080x1920 or higher. Language of ALL visible text: {language} only.
Story: {j['title']}. Conflict: {j['scenes'][0]['meaning']}.
Headline idea: {title}. Use a faithful headline of 3 to 5 words total, maximum two lines. If the idea already fits, reproduce it exactly. Otherwise shorten it naturally in the requested language without inventing facts or revealing the ending. No other text.
Input image 1 is the scene: use it for identity and story. If a second image is attached, it is ONLY the approved layout/style template: reproduce its close-up composition, emotional hierarchy and white/yellow headline treatment, but never copy its characters, story or German text. The new story and requested language always take priority. The attached scene is the identity and story reference. Preserve these exact characters, fruit skin, age and clothing:
{cast}
Recompose a tight chest-up confrontation with clearly visible expressive faces: dominant emotions and the main conflict instantly readable. Show the victim and opposing character large; a witness may be smaller. Simplify and softly blur the story setting. No empty floor or distant full-body framing. Sharp eyes, bright readable faces and cinematic 3D fruit textures.
Bold clean condensed sans serif headline: white first line, warm yellow emphasis on second line, restrained dark outline and shadow. Place text in the lower middle BELOW faces, inside the central 80 percent width; leave the top 15 percent and bottom 20 percent free of important text for cropping. Never cover eyes. No large dark banner across faces. No logos, watermarks, arrows, interface, fake evidence, extra characters or sensational claims not present in the story. Generate the finished image now, not a tutorial."""

def reference_text(j):
    sel=j.get('selected') or {}
    return ' '.join([(thumbs.cached(sel.get('url',''),DATA) or {}).get('desc',''),sel.get('title','')])

def check_originality(j):
    """Estimated originality before publishing (images, texts, origin, repetition, duration, AI label)."""
    d=job_dir(j);images=[d/x['image'] for x in j['scenes'] if x.get('image')]+([d/j['cover_file']] if j.get('cover_file') else [])
    def cover(url):
        p=thumbs.cached(url,DATA,'cover')
        return originality.dhash(p) if p else None
    url=(j.get('selected') or {}).get('url','')
    reference={'hash':cover(url),'text':reference_text(j)} if url else None
    figs=thumbs.all_figures(DATA)
    trends=[{'hash':cover(c['url']),'text':(figs.get(thumbs.video_id(c['url']) or '',{}) or {}).get('desc') or c.get('title','')} for c in {c['url']:c for x in STATE['jobs'] for c in x.get('candidates',[]) if c.get('url') and c.get('url')!=url}.values()]
    own=[{'title':x.get('title',''),'signature':(x.get('script') or {}).get('story_signature'),'hash':originality.dhash(job_dir(x)/x['cover_file']) if x.get('cover_file') and (job_dir(x)/x['cover_file']).is_file() else None} for x in STATE['jobs'] if x is not j and x.get('status')=='done']
    duration=len(j['scenes'])*int(j['config'].get('clip_seconds',8))
    j['originality']={**originality.evaluate(j,images,reference,trends,own,duration),'at':now()}
    event(j,'Contrôle d’originalité : '+str(j['originality']['score'])+' % · '+{'publish':'publication conseillée','fix':'corrections conseillées avant publication','hold':'publication déconseillée'}[j['originality']['verdict']]+'.')
    return j['originality']

def flow_scan(state,client,accounts,only_profile=None):
    """Google accounts found in this Chrome: one Flow profile each, real credits, automatic rotation."""
    added=updated=0;names=[]
    for a in accounts[:40]:
        email=str(a.get('email') or '').strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):continue
        if only_profile and email!=only_profile.get('flow_email','').lower():continue
        p=only_profile or next((x for x in state['profiles'] if (x.get('flow_email') or x.get('label','')).lower()==email),None)
        if p and any(c.get('role') == 'flow' and c.get('flow_profile') == p['id']
                     and c['id'] != client['id'] and not c.get('disabled')
                     for c in state['clients'].values()):
            continue
        if not p:
            p={'id':uid(),'label':email,'balance':0};state['profiles'].append(p);added+=1
        else:updated+=1
        p.update(flow_email=email,flow_client=client['id'],auto_enabled=True,slot=int(a.get('slot',0)))
        try:
            if a.get('project'):p['flow_url']=flow_accounts.project_url(a['project']);p.pop('flow_url_home',None)
        except ValueError:pass
        if not p.get('flow_url'):
            # No project yet: each production creates its own project from this account's home page.
            p['flow_url']=f"https://flow.google.com/u/{int(a.get('slot',0))}/project/home";p['flow_url_home']=True
        p['flow_url']=flow_accounts.at_slot(p['flow_url'],p['slot'])
        # This scan just verified the email at its current Google slot. An older wrong-slot warning is obsolete.
        if (p.get('readiness') or {}).get('state')=='fix' and 'Autre compte Google ouvert' in p['readiness'].get('reason',''):
            p.pop('readiness',None)
        if isinstance(a.get('balance'),int) and 0<=a['balance']<=100000:
            flow_refill.read(p,a['balance'],time.time(),int(state.get('settings',{}).get('flow_daily',flow_refill.DAILY)));p['balance']=a['balance'];p['credit_source']='read';p['checked']=now();p.pop('blocked',None) if a['balance']>0 else p.update(blocked='credits')
        names.append(email)
    if names and not only_profile:
        # Google renumbers /u/N when accounts are added or removed: an account of this browser that the scan no
        # longer finds must not keep a number that now opens another account (real case 04/11/2026: fruit123abc
        # kept /u/0, its balance checks read arnaudchewa65 and failed every 15 min). Kept, out of rotation.
        for x in state['profiles']:
            if x.get('flow_client')==client['id'] and x.get('slot') is not None and (x.get('flow_email') or '').lower() not in names:
                x['slot']=None;x['auto_enabled']=False;x.pop('credit_probe',None);x.pop('refill_at',None)
    if names:state.setdefault('settings',{})['flow_auto']=True
    total=sum(int(x.get('balance') or 0) for x in state['profiles'] if (x.get('flow_email') or '') in names)
    if not names:
        if only_profile:return 'Aucun compte correspondant dans ce profil Chrome. Ouvre la bonne session Google dans ce profil, puis réessaie.'
        return 'Aucun compte Google détecté dans cette fenêtre. Connecte-toi avec « Ajouter un compte Google », puis clique sur « Détecter les comptes Flow ».'
    # Says "in this window": with several FruchtDrama windows the table below adds up all of them.
    return f'Dernière détection dans une fenêtre : {len(names)} compte(s) Google ({added} nouveau(x)), {total} crédits Flow sur ces comptes. Changement de compte automatique activé.'

def prepare_source(id):
    """Refaire une virale: fetch the TikTok video once, key-frame board + local transcription, then write."""
    with LOCK:
        j=job_by(id)
        if not j or j.get('status')!='waiting_source':return
        url=(j.get('selected') or {}).get('url','');d=job_dir(j)
    analysis={}
    try:
        info=source_video.download(url,d/'source.mp4');analysis.update(info)
        if source_video.board(d/'source.mp4',d/'source_board.jpg',info['duration']):analysis['board']='source_board.jpg'
        try:analysis['sheets']=source_video.frame_sheets(d/'source.mp4',d,info['duration'])
        except Exception as e:log_error('Images de la vidéo d’origine',e)
        analysis['transcript']=source_video.transcribe(d/'source.mp4',ROOT)
        if j.get('config',{}).get('recreate')=='identical' and not analysis['transcript']:
            log_error('Transcription de la vidéo d’origine',RuntimeError('transcription vide (contrôle local absent ou modèle incomplet)'))
        message='Vidéo d’origine analysée : '+(f"{sum(1 for x in analysis['sheets'])} images (début, une toutes les 6 s, chaque changement de plan)" if analysis.get('sheets') else 'planche des moments clés' if analysis.get('board') else 'description')+(' et transcription' if analysis.get('transcript') else '')+' transmises à l’IA.'+('' if analysis.get('transcript') or j.get('config',{}).get('recreate')!='identical' else ' Attention : aucune transcription (contrôle local à installer ou à réparer avec Installer-Controle-Qualite) ; les répliques de l’original seront devinées sur les images, la copie sera moins fidèle.')
    except Exception as e:
        analysis['error']=str(e)[:200];message='Vidéo d’origine non récupérée ('+str(e)[:160]+') : l’histoire s’appuie sur '+('tes captures et ' if j.get('source_captures') else '')+'son lien seulement.'
    with LOCK:
        j=job_by(id)
        if not j:return
        j['source_analysis']=analysis
        if j['config'].get('recreate')=='identical' and analysis.get('duration'):
            # Moteur V09: one scene per window of the source (one clip length) plus the call clip.
            n=moteur_v09.scene_count(analysis['duration'],engines.spec(j)['seconds'])
            if n!=j['config'].get('scene_count'):
                j['config']['scene_count']=n
                event(j,f"Copie fidèle (moteur V09) : vidéo d’origine de {analysis['duration']} s → {n-1} scènes de {engines.spec(j)['seconds']} s + 1 clip d’appel.")
        if j.get('status')=='waiting_source':j['status']='running'
        event(j,message);schedule(j);save()

def captures_of(j):
    return [asset_url(j,f) for f in (j.get('source_captures') or []) if (job_dir(j)/f).is_file()]
def capture_note(j):
    # "Mets ma tête à la place du personnage X": the owner's images and instructions reach the character drawing.
    if not j.get('source_captures'):return ''
    return ' Owner reference images are attached'+(f" (owner instructions: {j['brief'][:400]})" if j.get('brief','').strip() else '')+': follow them only where these instructions ask (for example a face to use for a character); otherwise ignore them.'

def source_attachments(j):
    """Board of the video to redo and the owner's captures, as files the chat can attach."""
    a=j.get('source_analysis') or {}
    # Atelier-like: first image, one frame every 6 s, then the detected shots; the single board for older analyses.
    files=([x['file'] for x in a['sheets']] if a.get('sheets') else [a['board']] if a.get('board') else [])+list(j.get('source_captures') or [])
    return [asset_url(j,f) for f in files if (job_dir(j)/f).is_file()]

def approve_sheet(j,sheet,title_index,hook_index,message,call_index=0):
    j['sheet']=sheet;j['sheet_approved']=now();j['sheet_choice']={'title':int(title_index),'hook':int(hook_index),'call':int(call_index)}
    j['brief']=ideas.brief(sheet,title_index,hook_index,call_index);j['title']=sheet['titles'][min(int(title_index),len(sheet['titles'])-1)].capitalize()
    j.pop('sheet_previous',None);j.pop('sheet_note',None);j['stage']='script';j['status']='running';event(j,message);schedule(j)

def schedule(j):
    # Consultation only (access ended, revoked, unchecked for 3 days): nothing advances, nothing is sent or paid.
    if not LICENCE.allowed(): return
    # Speed (owner 09/11/2026, « beaucoup plus lent que l'Atelier »): the account check runs in parallel; the production
    # no longer waits up to 2 min for it. An account found « À régler » stops the episode when the answer comes.
    if j['status']=='waiting_quota' and j.get('quota_lane')=='chat' and j['stage']=='images':
        # ChatGPT at its image limit: the boards wait, the clips of the boards already drawn keep going (Flow, Grok).
        early_clip(j);return
    if j['status'] in ('paused','attention','done','rendering','waiting_research','waiting_script','waiting_credit','waiting_review','waiting_quota','waiting_account','waiting_night','waiting_source'): return
    step=j['stage']
    # The boards stage works on two lanes (see VIDEO_KINDS); every other stage waits for the episode's single task.
    if step=='images':return schedule_images(j)
    if step=='clips' and not any(t['job']==j['id'] and t['status'] in ('queued','claimed') and lane_of(t)=='chat' for t in STATE['tasks']):
        if schedule_clips(j):return
    if any(t['job']==j['id'] and t['status'] in ('queued','claimed') for t in STATE['tasks']): return
    if step=='ideas':
        if j.get('ideas'):
            j['status']='waiting_review';event(j,'Dix histoires proposées : choisissez celle qui deviendra votre épisode.');return
        avoid=[x['title'] for x in STATE['jobs'] if x is not j and x.get('title') not in (None,'Nouvel épisode') and not x.get('filon_only')][:20]
        add_task(j,'chat_text',{'provider':j['config']['provider'],'prompt':ideas.ideas_prompt(j['config']['language'],j['config'].get('niche','Fruits'),ideas.trends(STATE['jobs']),j.get('brief','') if j.get('brief','').strip() else '',avoid),'response_kind':'ideas'},'ideas')
    elif step=='sheet':
        if j.get('sheet') and not j.get('sheet_approved'):
            if j['config'].get('auto_sheet'):
                # Like the Atelier in automatic mode: first title, first hook, first call.
                approve_sheet(j,j['sheet'],0,0,'Fiche validée automatiquement : premier titre, première réplique et premier appel.');return
            j['status']='waiting_review';event(j,'Fiche de décision prête : relisez, choisissez le titre et la première réplique, puis validez.');return
        add_task(j,'chat_text',{'provider':j['config']['provider'],'prompt':ideas.sheet_prompt(j['config']['language'],j['brief'],j['config']['scene_count'],engines.spec(j)['seconds'],j.get('sheet_note',''),j.get('sheet_previous')),'response_kind':'sheet'},'sheet')
    elif step=='research':
        query=j['config']['query']
        if j.get('editorial_version')==2:
            j.setdefault('research_queries',editorial.queries(j,STATE['jobs']))
            index=min(j.get('research_round',0),len(j['research_queries'])-1);query=j['research_queries'][index]
        add_task(j,'tiktok_search',{'query':query},'research')
    elif step=='script':
        if j.get('editorial_version')==2:editorial.direction(j,STATE['jobs'])
        add_task(j,'chat_text',{'provider':j['config']['provider'],'prompt':script_prompt(j),'scene_count':j['config']['scene_count'],**({'attachments':source_attachments(j)} if source_attachments(j) and not correction_ready(j) else {})},'script')
    elif step=='characters':
        if review_pending(j):
            # Nothing is paid before the owner has read the story (P1-1).
            j['status']='waiting_review';event(j,'Histoire prête : relisez et corrigez les dialogues, puis validez pour lancer les images.');return
        if j.get('character_sheet')==1 and len(j['characters'])>1 and not any(c.get('file') for c in j['characters']):
            # P1-2: one image for the whole cast instead of one paid image per character.
            add_task(j,'chat_image',{'provider':'chatgpt','prompt':sheet_prompt(j)+correction(j.get('corrections',{}).get('characters'))+capture_note(j),'attachments':captures_of(j)},'characters');return
        for c in j['characters']:
            if not c.get('file'):
                add_task(j,'chat_image',{'provider':'chatgpt','prompt':c['image_prompt']+' Create one full-body character reference image. No text. Premium 3D animation, 9:16.'+correction(j.get('corrections',{}).get('character:'+c['id']))+capture_note(j),'attachments':captures_of(j)},f"character:{c['id']}"); return
        for k,change in enumerate(state_changes(j)):
            if state_needed(j,change):
                # « Au fil de l'histoire »: the same sheet with the change applied, attached to later boards.
                add_task(j,'chat_image',{'provider':'chatgpt','prompt':state_sheet_prompt(j,change)+correction(j.get('corrections',{}).get(f'state:{k}')),'attachments':[asset_url(j,state_base(j,change))]},f'state:{k}');return
        j['stage']='images'; schedule(j)
    elif step=='clips':
        if j.get('quality_version')==1:
            j['stage']='quality';schedule(j);return
        if j.get('cover_style') in ('dramatic_v2','family_poster_v3'):
            j['stage']='cover';event(j,'Création de la couverture : gros plans, titre court, style dramatique.');schedule(j)
        else:
            j['stage']='edit'; j['status']='rendering'; event(j,'Montage local démarré.'); start_render(j['id'])
    elif step=='quality':
        schedule_quality(j)
    elif step=='cover':
        if not j.get('cover_file'):
            base=j.get('cover_base')
            # Atelier-like: the owner picks the scene the cover is drawn from; first scene otherwise.
            reference=j['scenes'][base]['image'] if isinstance(base,int) and 0<=base<len(j['scenes']) and j['scenes'][base].get('image') else next((scene['image'] for scene in j['scenes'] if scene.get('image')),None)
            attachments=[asset_url(j,reference)] if reference else image_assets(j)
            template=ROOT/('cover-reference-grid.png' if j.get('cover_style')=='family_poster_v3' else 'cover-proposal-v2.png')
            if template.is_file():
                style_file=job_dir(j)/'cover-style-reference.png'
                if not style_file.exists():shutil.copyfile(template,style_file)
                attachments.append(asset_url(j,style_file.name))
            add_task(j,'chat_image',{'provider':'chatgpt','prompt':cover_prompt(j)+correction(j.get('corrections',{}).get('cover')),'attachments':attachments},'cover');return
        if cover_check_pending(j):return
        j['stage']='edit';j['status']='rendering';event(j,'Montage local démarré.');start_render(j['id'])
    elif step=='edit':
        # A failed or interrupted montage is retried locally; no media is regenerated.
        if not j.get('final'):
            j['status']='rendering';event(j,'Montage local relancé avec les médias existants.');start_render(j['id'])

FLOW_REWRITE_FIELDS=('image_prompt','video_prompt','meaning','montre','cadre','camera','actions','deplacement','dialogue')


def flow_rewrite_prompt(j,i):
    scene=j['scenes'][i]
    fields={k:scene[k] for k in FLOW_REWRITE_FIELDS if k in scene}
    return (f'Adapte uniquement cette scène de {j["config"]["language"]} pour une animation Flow de 8 secondes. '
            'Conserve les personnages, les locuteurs, la conséquence dans l’histoire et tout signe indispensable. '
            'Conçois une nouvelle composition et, si nécessaire, remplace une action ou un accessoire problématique par une action réellement différente, '
            'originale et tous publics. Évite les références reconnaissables à une œuvre ou à une personne réelle. '
            'Garde des dialogues parlés et naturels, jusqu’à trois répliques et 24 mots en tout. '
            'La planche décrit le départ, puis le clip décrit un mouvement réalisable. '
            'Renvoie uniquement le JSON avec production_id, generation_task_id et scene_rewrite contenant les champs modifiés. '
            'Inclue au minimum image_prompt et video_prompt, réellement différents. '
            f'Personnages présents : {json.dumps(scene["characters"],ensure_ascii=False)}. '
            f'Raison indiquée par Flow : {scene["engine_tries"][-1]["reason"]}. '
            f'Scène : {json.dumps(fields,ensure_ascii=False)}')


def apply_flow_rewrite(j,t,result):
    i=int(t['slot'].split(':')[1])
    scene=j['scenes'][i]
    answer=parse_json(result.get('text',''))
    changes=answer.get('scene_rewrite') if isinstance(answer,dict) else None
    if (not scene.get('flow_rewrite_pending') or not isinstance(changes,dict)
            or answer.get('production_id')!=j['id'] or answer.get('generation_task_id')!=t['id']):
        raise ValueError('Adaptation Flow non associée à cette tâche.')
    for key in ('image_prompt','video_prompt'):
        value=changes.get(key)
        if not isinstance(value,str) or not value.strip() or value.strip()==scene[key].strip():
            raise ValueError('L’adaptation doit fournir deux nouveaux prompts.')
    updated={**scene,**{key:changes[key] for key in FLOW_REWRITE_FIELDS if key in changes}}
    lines=updated['dialogue']
    if (not isinstance(lines,list) or not 1<=len(lines)<=engines.MAX_DIALOGUE_TURNS
            or any(not isinstance(line,dict) or not isinstance(line.get('text'),str) or not line['text'].strip() for line in lines)
            or {line.get('speaker') for line in lines}!={line['speaker'] for line in scene['dialogue']}
            or sum(len(line['text'].split()) for line in lines)>engines.words_for('flow')):
        raise ValueError('L’adaptation doit conserver les locuteurs et tenir dans huit secondes.')
    if any(not isinstance(updated.get(key,''),str) for key in ('meaning','montre','cadre','camera','deplacement')):
        raise ValueError('Consignes de mise en scène invalides.')
    if not isinstance(updated.get('actions',[]),list) or any(not isinstance(action,str) for action in updated.get('actions',[])):
        raise ValueError('Actions de la scène invalides.')
    if scene.get('image'):
        j.setdefault('redo_history',[]).append({'slot':f'image:{i}','file':scene['image'],'note':'adaptation après refus Flow','at':now()})
    updated.pop('image',None)
    updated.pop('flow_rewrite_pending',None)
    j['scenes'][i]=updated
    if j.get('board_review'):
        j['board_review']['boards']=[board for board in j['board_review']['boards'] if board['index']!=i]
    if j.get('script'):
        j['script']['scenes'][i].update({k:copy.deepcopy(updated[k]) for k in FLOW_REWRITE_FIELDS if k in updated})
        (job_dir(j)/'scenario.json').write_text(json.dumps(j['script'],ensure_ascii=False,indent=2),'utf-8')
    event(j,f'Clip {i+1} : scène adaptée. Nouvelle planche avant le deuxième essai Flow.')


def schedule_images(j):
    """Boards stage on two lanes: the chat lane draws the boards one by one (then the board check), while the video
    lane already animates each validated board, one clip at a time. The clips stage then makes only what is missing."""
    if not lane_busy(j,'chat'):
        for i,s in enumerate(j['scenes']):
            if s.get('flow_rewrite_pending'):
                add_task(j,'chat_text',{'provider':'chatgpt','prompt':flow_rewrite_prompt(j,i),
                                       'response_kind':'flow_rewrite'},f'flow_rewrite:{i}');break
            if not s.get('image'):
                attachments,states=scene_references(j,i)
                add_task(j,'chat_image',{'provider':'chatgpt','prompt':s['image_prompt']+plan_image_block(j,s)+' Use attached character references. Same identity and outfit, 9:16. Dynamic cinematic composition with a camera angle different from the other scenes, characters caught in action, detailed living background. Highest resolution available (at least 1024×1536), ultra sharp, no blur.'+state_note(j,states)+correction(j.get('corrections',{}).get(f'image:{i}')),'attachments':attachments},f'image:{i}');break
        else:
            if not board_gate(j):
                # Every board drawn and validated: the clips stage waits for a clip still in progress, then goes on.
                j['stage']='clips';j.pop('early_clips_off',None);j['alerts']=[a for a in j.get('alerts',[]) if a.get('stage')!='images'];schedule(j);return
    if j['stage']=='images' and (j['status']=='running' or (j['status']=='waiting_quota' and j.get('quota_lane')=='chat')):early_clip(j)

def board_ready(j,i):
    """Board i may be animated: it is drawn and, when the board check is on, the check has given its verdict.
    The check looks at all boards together, so before its verdict no board counts as validated."""
    if j['scenes'][i].get('flow_rewrite_pending') or not j['scenes'][i].get('image'):return False
    return j['config'].get('board_controls','none')=='none' or bool(j.get('board_checked'))

def held_clips(j):
    """Clips that wait for the owner: a Flow submission that may have been charged, or every engine tried.
    The other clips go on (owner 06/11/2026); « Action requise » comes only when nothing else is left to make."""
    out={int(t['slot'].split(':')[1]) for t in uncertain_clip_tasks(j)}
    return out|{i for i,s in enumerate(j.get('scenes') or []) if s.get('engine_exhausted') and not s.get('clip')}

def held_message(j):
    uncertain=uncertain_clip_tasks(j)
    if uncertain:return uncertain_message(j)
    rows=[f'clip {i+1} : '+engine_chain.summary(s) for i,s in enumerate(j['scenes']) if s.get('engine_exhausted') and not s.get('clip')]
    return 'Aucun moteur n’a pu faire '+('ces clips' if len(rows)>1 else 'ce clip')+', même avec le prompt adouci — '+' ; '.join(rows)+'. Modifie la scène (« Refaire » avec une consigne) ou importe un clip, puis Reprendre.'

def schedule_clips(j):
    """Clips stage. Returns True while clips remain to make (queued, in flight or waiting); False when every clip is in.
    One clip first (unchanged rules: switch, wait for credits); then, with Flow and the automatic switch, more clips at
    once on other ready accounts, up to the « clips en parallèle » setting. A clip held for the owner never stops the others."""
    active=video_tasks(j);busy={int(t['slot'].split(':')[1]) for t in active if str(t.get('slot','')).startswith('clip:')}
    held=held_clips(j)
    todo=[i for i,s in enumerate(j['scenes']) if not s.get('clip') and i not in busy and i not in held]
    if not todo:
        if active:return True
        if held:
            if j['status']=='running':j['status']='attention';event(j,held_message(j))
            return True
        return False
    if not active:
        # Find ready work before setting a global account/credit wait for the first scene.
        for i in list(todo):
            schedule_clip(j,i,early=True)
            active=video_tasks(j)
            if active:
                todo.remove(i);break
        if not active:
            schedule_clip(j,todo[0]);return True
    for i in todo:
        if len(video_tasks(j))>=video_slots(j):break
        # A Flow account waiting its turn must not starve a later clip ready on Grok.
        schedule_clip(j,i,early=True,parallel=True)
    return True

def early_clip(j):
    """Atelier-like: a clip leaves for Flow/Grok while ChatGPT still draws the next boards. Only when everything is
    ready; otherwise nothing is changed and the clips stage, after the boards, waits and says why as before."""
    if not STATE.get('settings',{}).get('parallel_clips',True) or j['config'].get('dry_run') or j.get('early_clips_off'):return False
    active=video_tasks(j)
    if len(active)>=video_slots(j):return False
    busy={int(t['slot'].split(':')[1]) for t in active if str(t.get('slot','')).startswith('clip:')};held=held_clips(j)
    i=next((i for i,s in enumerate(j['scenes']) if not s.get('clip') and i not in busy and i not in held and board_ready(j,i)),None)
    return i is not None and schedule_clip(j,i,early=True,parallel=bool(active))

# Bascule par clip (0.1.93, owner 06/11/2026: « un essai par cas »): each clip tries Flow, then Arena, Vidogrid, Grok
# (order in the settings), one try each, engines without a ready account skipped; see engine_chain.py.
def current_account(j,engine):
    return (j.get('engine_account_by') or {}).get(engine) or (j.get('engine_account') if engine==engines.of(j) else None)

def flow_can_pay(j):
    """A Flow account can pay this clip now or after the clip it works on (busy accounts count: the clip waits its turn)."""
    return bool(flow_accounts.choose(STATE,j.get('flow_profile'),int(j['config'].get('flow_cost',12))))

def engine_ready(j,engine,moment=None):
    """This engine may take a clip of this episode: an account known ready, never one « À régler » or at its limit.
    The episode's own engine (« Moteur des clips ») is tried as before 0.1.93 even when nothing was checked yet."""
    moment=moment or time.time()
    if engine not in engines.AVAILABLE:return False
    if engine=='flow':return flow_can_pay(j)
    # Owner 06/11/2026: Grok is costly, never used without their go-ahead (« Utiliser Grok » on the episode).
    if engine=='grok' and not (j.get('grok_ok') or STATE.get('settings',{}).get('grok_auto') or engine_chain.flow_grok_policy(STATE.get('settings'),j['config']) or engine_chain.v09_policy(STATE.get('settings'),j['config'])):return False
    own=engine==engines.of(j)
    if j['config'].get('dry_run') and not own:return False  # a dry run checks the episode's engine only
    if (STATE.get('engine_walls') or {}).get(engine,0)>moment:return False
    rows=engine_accounts.accounts(STATE,engine)
    if rows:
        account=engine_accounts.choose(STATE,engine,current_account(j,engine),moment)
        if not account:return False
        # A fallback never asks the owner to change account: a guided change is for the episode's own engine only.
        if not own and current_account(j,engine) and account['id']!=current_account(j,engine):return False
    entry=readiness.site_entry(STATE,engine)
    if entry and entry.get('state') in readiness.NOT_READY:return False
    return own or bool(rows) or readiness.site_has_account(STATE,engine)

def clip_engine_for(j,i,early=False):
    """Engine of the next try of clip i, or None when every engine has been tried (the clip waits for the owner)."""
    s=j['scenes'][i];chain=engine_chain.order(STATE.get('settings'),j['config'])
    if engine_chain.v09_policy(STATE.get('settings'),j['config']):
        # Moteur V09: clip 1 on Grok when it is ready (else Flow), clips 2 and later on Flow only, never Grok.
        return engine_chain.v09_next(s,i,i==0 and engine_ready(j,'grok'),engine_ready(j,'vidogrid'))
    if engine_chain.flow_grok_policy(STATE.get('settings'),j['config']):
        return engine_chain.flow_grok_next(s)
    if j['config'].get('dry_run'):return engines.of(j)
    ready=lambda e:engine_ready(j,e)
    nxt=engine_chain.pick(s,chain,ready)
    if nxt:return nxt
    if not s.get('engine_tries'):
        # Nothing ready at all: the first engine keeps its own wait (credits, quota, accounts to fix), as before.
        return chain[0]
    if early:return None
    before=engine_chain.round_of(s);nxt=engine_chain.advance(s,chain,ready)
    if nxt:
        if engine_chain.round_of(s)>before:event(j,f'Clip {i+1} : prompt adouci, nouvel essai sur {engine_chain.LABELS[nxt]}.')
        return nxt
    if redraw_refused_board(j,i):return None
    ask_grok(j,i)
    s['engine_exhausted']=True;alert(j,'action','Clip '+str(i+1)+' : '+held_message(j))
    return None

def clip_prompt(j,i,engine):
    s=j['scenes'][i]
    visible=s.get('characters') or [c['id'] for c in j['characters']]
    cast='\n'.join(c['id']+': '+c['appearance']+' Voice: '+c['voice'] for c in j['characters'] if c['id'] in visible)
    dialog=dialogue_lines(j,s);language=j['config'].get('language','Deutsch (de-DE)');seconds=engines.seconds(j,engine)
    if is_identical(j):
        # Moteur V09: the writer's timed beats, cast lock and exact lines, then the closing block of the V09 clips.
        prompt=moteur_v09.clip_prompt(j,s,seconds,cast,dialog,language,character_styles.get(j)['make'] if j['config'].get('character_style') else None)+plan_mute_block(j,s)+correction(j.get('corrections',{}).get(f'clip:{i}'))
        return engine_chain.soften(prompt) if engine_chain.round_of(s)>=engine_chain.FINAL_ROUND else prompt
    prompt=(f"One continuous shot, {seconds} seconds, portrait 9:16. Animate the attached image with the directed camera motion and gestures. "
            f"No music. Spoken language ONLY: {language}. Natural native voices, no translation or extra narration. "
            f"Only the following cast appears. Preserve their identity.\n{cast}\n"+(character_styles.get(j)['make']+'\n' if j['config'].get('character_style') else '')+f"{s['video_prompt']}{plan_video_block(j,s)}\n"
            f"Exact dialogue in this order; only the named speaker moves their lips, all others stay silent:\n{dialog}")
    if engine=='flow':
        prompt+='\nUse the reference as the first frame. Keep the fictional cast and setting original, and use a general-audience presentation.'
    prompt+=correction(j.get('corrections',{}).get(f'clip:{i}'))
    # Last round (every engine refused): the scene is reworded once so that an engine accepts it.
    return engine_chain.soften(prompt) if engine_chain.round_of(s)>=engine_chain.FINAL_ROUND else prompt

def schedule_clip(j,i,early=False,parallel=False):
    """Queue clip i on the engine of its next try (Flow, Arena, Vidogrid or Grok). early=True (during the boards): returns
    False without touching the episode when an account, credits or a check is missing. Returns True when a task was queued
    or the episode waits. parallel=True: an extra clip while another one works: another ready account only."""
    if i in held_clips(j):
        if early:return False
        j['status']='attention';event(j,held_message(j));return True
    engine=clip_engine_for(j,i,early)
    if not engine:
        if early:return False
        return True  # held for the owner: schedule_clips goes on with the other clips
    if engine!='flow':return schedule_engine_clip(j,i,engine,early,parallel)
    return schedule_flow_clip(j,i,early,parallel)

def engine_busy(engine):
    """One tab per site in the FruchtDrama window: never two clips at once on Grok, Arena or Vidogrid."""
    return any(t.get('kind')=='engine_video' and t['status'] in ('queued','claimed') and (t.get('payload') or {}).get('engine')==engine for t in STATE['tasks'])

def schedule_engine_clip(j,i,engine,early=False,parallel=False):
    # P5-06: Grok / Arena / Vidogrid. No credit balance to reserve; quotas are handled per account.
    s=j['scenes'][i]
    if parallel and engine_busy(engine):return False
    seconds=engines.seconds(j,engine)
    payload={'engine':engine,'prompt':clip_prompt(j,i,engine),'attachments':[asset_url(j,flow_reference(j,s['image']))],'seconds':seconds}
    if engine_accounts.accounts(STATE,engine) and not j['config'].get('dry_run'):
        moment=time.time();account=engine_accounts.choose(STATE,engine,current_account(j,engine),moment)
        if not account:
            if early:return False
            # P5-08: every registered account is at its limit: wait for the first renewal.
            j['status']='waiting_quota';j['wait_until']=engine_accounts.next_free(STATE,engine,moment)
            event(j,'Tous les comptes '+engines.ENGINES[engine]['label']+' sont à leur limite. Reprise automatique vers '+clock_in(j['wait_until'])+', ou ajoutez un compte.');return True
        if current_account(j,engine) and account['id']!=current_account(j,engine):
            if early:return False
            previous=engine_accounts.by_id(STATE,current_account(j,engine))
            j['engine_account']=account['id'];j.setdefault('engine_account_by',{})[engine]=account['id'];j['status']='waiting_account'
            j['account_switch']={'engine':engine,'from':(previous or {}).get('email'),'to':account['email'],'label':account['label']}
            event(j,'Compte '+engines.ENGINES[engine]['label']+' suivant : connectez-vous vous-même à '+account['email']+' dans l’onglet de la fenêtre FruchtDrama, puis cliquez « J’ai changé de compte ». Clips reçus conservés.');return True
        j.setdefault('engine_account_by',{})[engine]=account['id']
        if engine==engines.of(j):j['engine_account']=account['id']
        payload['account']={'email':account['email'],'label':account['label']}
    if j['config'].get('dry_run'):payload['dry_run']=True
    if horizontal(j):payload['aspect']='16:9'
    words=sum(len(x['text'].split()) for x in s.get('dialogue') or [])
    if engine!=engines.of(j) and words>engines.words_for(engine,j=j):
        event(j,f'Clip {i+1} sur {engines.ENGINES[engine]["label"]} : {seconds} s pour {words} mots écrits pour un clip plus long, la fin de la réplique peut être coupée.')
    add_task(j,'engine_video',payload,f'clip:{i}');return True

def schedule_flow_clip(j,i,early=False,parallel=False):
    s=j['scenes'][i]
    if normalize_flow_resolution(j['config']):
        event(j,'Réglage Flow corrigé avant envoi : génération native 720p pour ce modèle ; export final 1080p conservé.')
    flow_accounts.follow_active_browser(STATE)
    cost=j['config']['flow_cost'];busy=busy_flow_profiles()
    if parallel:
        p=flow_accounts.choose(STATE,None,cost,exclude=busy)
        if not p or p['balance']<cost or not flow_accounts.route(p):return False
    else:p=flow_accounts.choose(STATE,j.get('flow_profile'),cost,exclude=busy)
    if not p and busy and flow_accounts.choose(STATE,j.get('flow_profile'),cost):
        # Every account able to pay already works on a clip: this one waits its turn (nothing changes, no message).
        return not early
    if not p and STATE.get('settings',{}).get('flow_auto'):
        unready=[x for x in readiness.candidates(STATE,cost,lambda x:flow_accounts.eligible(STATE,x)) if not flow_accounts.usable(x)]
        refill=[x for x in STATE['profiles'] if x.get('refill_at') and x.get('auto_enabled') and x['refill_at']>time.time() and flow_accounts.usable(x)]
        if unready and refill:
            # Real case 09/11/2026: the only account with enough credits had no access to Flow, and others refill within the
            # hour: the episode waits for the refill and resumes alone (with the account to fix named), no « Action requise ».
            if early:return False
            j['status']='waiting_credit';back=min(x['refill_at'] for x in refill)
            event(j,f'Plus aucun compte Flow prêt avec {cost} crédits : le clip part tout seul à la prochaine recharge, vers {clock_in(back)}. À régler quand tu veux : '
                  +'; '.join(readiness.mask(x.get('flow_email') or x.get('label'))+' : '+readiness.reason_of(x.get('readiness')) for x in unready)+'. Clips reçus conservés.')
            return True
        if unready:
            # Accounts with credits exist but none is ready: only now « Action requise », with the exact reasons.
            if early:return False
            j['status']='attention'
            alert(j,'action','Aucun compte Google Flow prêt : '+'; '.join(readiness.mask(x.get('flow_email') or x.get('label'))+' : '+readiness.reason_of(x.get('readiness')) for x in unready)+'. Ouvre Mes comptes, « Régler maintenant » puis « C’est fait » : la production reprend avec Reprendre.')
            return True
    if not p or p['balance']<cost:
        if early:return False
        j['status']='waiting_credit'
        back=min([x['refill_at'] for x in STATE['profiles'] if x.get('refill_at') and x.get('auto_enabled')],default=None)
        if STATE.get('settings',{}).get('flow_auto') and any(flow_accounts.route(x) for x in STATE['profiles']):
            event(j,f'Plus aucun compte Flow avec {cost} crédits : le clip part tout seul dès qu’un compte est rechargé'+(' (premier vers '+clock_in(back)+')' if back else '')+' ou ajouté. Clips reçus conservés.')
        else:event(j,'Solde insuffisant ou profil Flow absent. Choisis un profil et vérifie son solde.')
        return True
    if p['id']!=j.get('flow_profile') and not parallel:
        previous=profile_by(j.get('flow_profile'))
        j['flow_profile']=p['id'];account_usage.number_flow(STATE);event(j,account_usage.switch_line(previous,p,cost))
    payload={'prompt':clip_prompt(j,i,'flow'),'attachments':[asset_url(j,flow_reference(j,s['image']))],'cost':cost,'balance':p['balance'],'seconds':engines.flow_seconds(j),**({'model':j['config']['flow_model'],'resolution':j['config'].get('flow_resolution','720p')} if j['config'].get('flow_model') else {})}
    if j['config'].get('dry_run'):payload['dry_run']=True
    target=flow_accounts.route(p) if STATE.get('settings',{}).get('flow_auto') else None
    if target:
        existing=j.get('flow_projects',{}).get(p['id'])
        if existing:target['url']=existing
        else:target['new_project']=True
        payload['flow_route']=target
    if parallel:account_usage.number_flow(STATE);event(j,'Clip '+str(i+1)+' en parallèle : '+account_usage.flow_name(p,word='compte Flow')+'.')
    add_task(j,'flow_video',payload,f'clip:{i}',profile=p['id']);return True

def clip_failed(j,t,result,kind):
    """A clip failed (0.1.93). Returns True when handled here: next engine, softened last round, or held for the owner.

    Known failure (nothing sent to Flow, or a free engine): the clip moves at once to the next engine, no « Action
    requise ». A Flow submission that may have been charged is never sent again by chance (uncertain_clip_tasks): that
    clip waits for the owner, the other clips go on."""
    slot=str(t.get('slot',''))
    if t.get('kind') not in ('flow_video','engine_video') or not slot.startswith('clip:') or j['config'].get('dry_run'):return False
    i=int(slot.split(':')[1])
    if i>=len(j.get('scenes') or []) or j['scenes'][i].get('clip'):return False
    scene=j['scenes'][i];engine='flow' if t['kind']=='flow_video' else (t.get('payload') or {}).get('engine')
    reason=result.get('error','')
    if t['kind']=='flow_video':
        # Flow's own failure message after the submission (flow_failed): nothing more to wait for, nothing charged.
        if result.get('generation_submitted') is not False and result.get('flow_failed') is not True:
            t['status']='failed';t['uncertain']=True;j['status']='running'
            alert(j,'action',f'Clip {i+1} : envoi Flow incertain ({engine_chain.short(reason)}) : le clip a peut-être été généré et facturé. Vérifie le projet Flow, puis importe-le ou confirme qu’il n’existe pas. Les autres clips continuent.')
            schedule(j);return True
        if result.get('flow_blocked') in ('credits','unavailable','not_ready') and (t.get('payload') or {}).get('flow_route'):
            return False  # this Google account, not Flow itself: the next Flow account, then the next engine (schedule_clip)
    if engine_chain.v09_policy(STATE.get('settings'),j['config']):
        # Moteur V09: Grok failed on clip 1 (limit, sign-in, refusal…) → Flow at once; Flow refused → one adapted retry.
        if kind=='quota' and engine in ('grok','vidogrid'):
            moment=time.time();email=((t.get('payload') or {}).get('account') or {}).get('email')
            account=next((a for a in engine_accounts.accounts(STATE,engine) if a['email']==email),None) or engine_accounts.by_id(STATE,current_account(j,engine))
            if account:engine_accounts.wall(account,moment,errors.retry_after(result),reason)
            else:STATE.setdefault('engine_walls',{})[engine]=moment+(errors.retry_after(result) or engine_accounts.DEFAULT_WALL)
        if engine in ('grok','vidogrid'):note_not_ready(t,result)
        engine_chain.record(scene,engine,kind,reason,now())
        nxt=engine_chain.v09_next(scene,i,False,engine_ready(j,'vidogrid'))
        t['status']='failed';j['status']='running'
        if engine=='flow' and kind=='refusal' and nxt=='flow':
            scene['flow_rewrite_pending']=True;j['stage']='images'
            event(j,f'Clip {i+1} : refus confirmé de Flow. Adaptation de la scène avant le deuxième essai sur Flow.')
            schedule(j);return True
        event(j,engine_chain.line(i,engine,kind,reason,nxt))
        if not nxt and redraw_refused_board(j,i):schedule(j);return True
        if not nxt:
            scene['engine_exhausted']=True
            if engine=='flow':j['status']='attention'
            alert(j,'action',f'Clip {i+1} : Flow'+(' et Vidogrid n’ont' if any(x.get('engine')=='vidogrid' for x in scene.get('engine_tries') or []) else ' n’a')+f' pas livré le clip ({engine_chain.short(reason)}). '+('Grok ne fait que le clip 1 : ' if i else '')+'modifie la scène (« Refaire » avec une consigne) ou importe un clip, puis Reprendre. Les autres clips continuent.')
        schedule(j);return True
    if engine_chain.flow_grok_policy(STATE.get('settings'),j['config']):
        engine_chain.record(scene,engine,kind,reason,now())
        nxt=engine_chain.flow_grok_next(scene)
        t['status']='failed';j['status']='running'
        if engine=='flow' and kind=='refusal' and nxt=='flow':
            scene['flow_rewrite_pending']=True;j['stage']='images'
            event(j,f'Clip {i+1} : refus confirmé de Flow. Adaptation de la scène avant le deuxième essai.')
            schedule(j);return True
        event(j,engine_chain.line(i,engine,kind,reason,nxt))
        if not nxt:
            scene['engine_exhausted']=True
            if engine=='flow':j['status']='attention'  # shared Flow settings: fix once before trying every other clip
            alert(j,'action',f'Clip {i+1} : '+('Grok n’a pas livré le clip après le refus de Flow.' if engine=='grok' else 'Flow rencontre un problème technique ; Grok est réservé aux refus de génération.')+' '+engine_chain.short(reason))
        schedule(j);return True
    chain=engine_chain.order(STATE.get('settings'),j['config'])
    ready=lambda e:engine_ready(j,e)
    if kind=='quota' and t['kind']=='engine_video':
        moment=time.time();email=((t.get('payload') or {}).get('account') or {}).get('email')
        account=next((a for a in engine_accounts.accounts(STATE,engine) if a['email']==email),None) or engine_accounts.by_id(STATE,current_account(j,engine))
        if not engine_chain.pick(scene,chain,lambda e:e!=engine and ready(e)):return False  # nothing else: the existing wait for renewal
        if account:engine_accounts.wall(account,moment,errors.retry_after(result),reason)
        else:STATE.setdefault('engine_walls',{})[engine]=moment+(errors.retry_after(result) or engine_accounts.DEFAULT_WALL)
    elif kind in errors.HUMAN and not engine_chain.pick(scene,chain,lambda e:e!=engine and ready(e)):
        return False  # nothing else ready: the owner signs in or solves the check, as before
    note_not_ready(t,result)
    engine_chain.record(scene,engine,kind,reason,now())
    before=engine_chain.round_of(scene);nxt=engine_chain.advance(scene,chain,ready)
    t['status']='failed';j['status']='running'
    event(j,engine_chain.line(i,engine,kind,reason,nxt,engine_chain.round_of(scene)>before))
    if not nxt and redraw_refused_board(j,i):schedule(j);return True
    if not nxt:ask_grok(j,i)
    if not nxt:
        scene['engine_exhausted']=True
        alert(j,'action',f'Clip {i+1} : aucun moteur ne l’a fait, même avec le prompt adouci — {engine_chain.summary(scene)}. Modifie la scène (« Refaire » avec une consigne) ou importe un clip, puis Reprendre. Les autres clips continuent.')
    schedule(j);return True

THIRD_PARTY=re.compile(r'contenu(?:s)? tiers|fournisseurs de contenu|third[- ]party|Drittanbieter',re.I)
THIRD_PARTY_NOTE=('Video engine refusal: this board looks too close to existing third-party content. Draw the SAME moment again but '
    'clearly different: another camera angle and framing, another pose and gesture for each character, another background '
    'layout and lighting, different colours for clothes details and props. Keep the characters recognisable (species, hair, '
    'outfit type) and keep the meaning of the scene.')

def ask_grok(j,i):
    """Every free engine failed: offer Grok, once per episode, never used before the owner says yes."""
    if j.get('grok_ok') or 'grok' not in engine_chain.order(STATE.get('settings'),j['config']) or j.get('grok_asked') or engine_chain.v09_policy(STATE.get('settings'),j['config']):return
    j['grok_asked']=True
    alert(j,'action',f'Clip {i+1} : Flow n’y arrive pas. Grok peut essayer, mais il consomme beaucoup : valide pour l’utiliser sur cet épisode.')
    j['alerts'][-1]['command']='allow_grok';j['alerts'][-1]['label']='Utiliser Grok pour cet épisode'

def redraw_refused_board(j,i):
    """Real case 06/11/2026: Flow refused a board « en raison des intérêts des fournisseurs de contenu tiers » whatever the
    prompt (a faithful remake draws too close to the original video). Once every engine has failed, the board is drawn
    again, clearly different, and the clip starts over from the first engine. Twice at most per scene."""
    sc=j['scenes'][i]
    if not any(THIRD_PARTY.search(str(x.get('reason',''))) for x in sc.get('engine_tries') or []) or sc.get('third_party_redraws',0)>=2:return False
    sc['third_party_redraws']=sc.get('third_party_redraws',0)+1
    if sc.get('image'):j.setdefault('redo_history',[]).append({'slot':f'image:{i}','file':sc.pop('image'),'note':'refus contenu tiers','at':now()})
    j.setdefault('corrections',{})[f'image:{i}']=THIRD_PARTY_NOTE;engine_chain.reset(sc);j.pop('early_clips_off',None)
    j['stage']='images';j['status']='running'
    event(j,f'Clip {i+1} : la planche ressemble trop à un contenu existant pour Flow → planche redessinée (autre cadrage, autre pose, autre fond), puis nouvel essai du clip.')
    return True

def uncertain_clip_tasks(j):
    """Flow submissions that may have been charged but whose clip was never received."""
    scenes=j.get('scenes',[])
    def missing(t):
        index=int(t['slot'].split(':')[1])
        return index<len(scenes) and not scenes[index].get('clip')
    return [t for t in STATE['tasks'] if t.get('job')==j['id'] and t.get('kind')=='flow_video' and t.get('status')=='failed'
            and ((t.get('reservation') and not t['reservation'].get('refunded')) or t.get('uncertain')) and not t.get('acknowledged')
            and str(t.get('slot','')).startswith('clip:') and missing(t)]

def uncertain_message(j):
    scenes=sorted({int(t['slot'].split(':')[1])+1 for t in uncertain_clip_tasks(j)})
    return ('Envoi Flow incertain pour la scène '+', '.join(map(str,scenes))+' : le clip a peut-être déjà été généré et facturé. '
            'Laissez la passerelle le récupérer, importez-le, ou confirmez qu’il n’existe pas dans Flow avant toute nouvelle génération.')

def correction(note):
    return f'\nOwner correction for this new attempt (apply it, keep everything else unchanged): {note}' if note else ''

REDO_STAGES={'characters':'characters','character':'characters','state':'characters','image':'images','clip':'clips','cover':'cover'}

def stale_clips(j):
    """Scenes whose board changed after their clip was made (only clips that know their board)."""
    return [i for i,s in enumerate(j.get('scenes') or []) if s.get('clip') and s.get('clip_from') and s.get('image') and s['clip_from']!=s['image']]

def redo_clips(j,indexes):
    """« Refaire ces clips » (like the Atelier): every clip whose board changed, in one go."""
    stale=stale_clips(j);chosen=[i for i in indexes if i in stale] if indexes else stale
    if not chosen:raise ValueError('Aucun clip à refaire : leurs planches n’ont pas changé')
    for i in chosen:redo(j,f'clip:{i}','la planche a changé : animer la nouvelle planche',start=False)
    schedule(j);return chosen

def edit_scene(j,index,texts):
    """« Modifier le texte » of one scene, any time: the clip keeps its old words until it is made again."""
    scenes=j.get('scenes') or []
    if not isinstance(index,int) or not 0<=index<len(scenes):raise ValueError('Scène inconnue')
    lines=scenes[index].get('dialogue') or []
    if not isinstance(texts,list) or len(texts)!=len(lines):raise ValueError('Une réplique par ligne est attendue')
    limit=engines.word_limit(j)
    clean=[' '.join(str(t or '').split())[:300] for t in texts]
    if any(not t for t in clean):raise ValueError('Une réplique ne peut pas être vide')
    if sum(len(t.split()) for t in clean)>limit:raise ValueError(f'Trop long pour un clip : {limit} mots parlés au plus dans cette scène')
    if any(t['job']==j['id'] and t['slot']==f'clip:{index}' and t['status'] in ('queued','claimed') for t in STATE['tasks']):raise ValueError('Ce clip est en cours de fabrication : attendez sa fin')
    for line,text in zip(lines,clean):line['text']=text
    script_scenes=(j.get('script') or {}).get('scenes') or []
    if index<len(script_scenes) and script_scenes[index] is not scenes[index]:
        for line,text in zip(script_scenes[index].get('dialogue') or [],clean):line['text']=text
    if scenes[index].get('clip'):scenes[index]['text_after_clip']=True
    event(j,f'Texte de la scène {index+1} modifié par le propriétaire'+(' : le clip garde l’ancien texte tant qu’il n’est pas refait.' if scenes[index].get('clip') else '.'))

def restore_version(j,slot,file):
    """« Remettre » (like the Atelier): a previous board or clip of a scene comes back; the current one is kept in turn."""
    slot=str(slot);m=re.fullmatch(r'(image|clip):(\d+)',slot)
    if not m:raise ValueError('Seules les planches et les clips d’une scène se remettent')
    kind,index=('image' if m.group(1)=='image' else 'clip'),int(m.group(2))
    if index>=len(j.get('scenes') or []):raise ValueError('Scène inconnue')
    if j.get('status')=='rendering' or j['id'] in BUSY:raise ValueError('Montage en cours : attendez sa fin')
    if any(t['job']==j['id'] and t['slot']==slot and t['status'] in ('queued','claimed') for t in STATE['tasks']):raise ValueError('Cet élément est en cours de fabrication : attendez sa fin')
    history=j.setdefault('redo_history',[])
    entry=next((h for h in reversed(history) if h.get('slot')==slot and h.get('file')==file),None)
    if not entry or not safe_child(job_dir(j),file).is_file():raise ValueError('Version introuvable')
    scene=j['scenes'][index];current=scene.get(kind)
    history.remove(entry)
    if current:history.append({'slot':slot,'file':current,'note':'remplacé par une version précédente','at':now()})
    scene[kind]=file
    if kind=='clip':scene.pop('clip_from',None);scene.pop('text_after_clip',None)  # its board is unknown: no false « planche changée »
    if kind=='clip' and j.get('quality_report'):j['quality_report'].pop('fingerprint',None)  # the clip check runs again
    if j.get('final'):j['montage_stale']=True
    event(j,f"{'Planche' if kind=='image' else 'Clip'} de la scène {index+1} : version précédente remise ; l’autre est gardée."+(' Remontez la vidéo pour l’inclure.' if j.get('final') and kind=='clip' else ''))

def redo(j,slot,note='',include_clip=False,start=True):
    """P1-3: regenerate one media with an owner correction; earlier media and files are kept."""
    slot=str(slot);note=' '.join(str(note or '').split())[:500]
    j.get('refusal_levels',{}).pop(slot,None)  # a new owner instruction restarts the rewording (P2-05)
    kind=slot.split(':')[0]
    if kind not in REDO_STAGES or not re.fullmatch(r'(?:cover|characters|character:[a-z][a-z0-9_]{0,24}|state:\d+|image:\d+|clip:\d+)',slot):raise ValueError('Élément à refaire inconnu')
    if j.get('status')=='rendering' or j['id'] in BUSY:raise ValueError('Montage en cours : attendez sa fin avant de refaire un élément')
    if any(t['job']==j['id'] and t['status'] in ('queued','claimed') for t in STATE['tasks']):raise ValueError('Une tâche est en cours sur cette production : attendez sa fin')
    if not j.get('scenes'):raise ValueError('Aucun scénario : rien à refaire')
    scenes=j['scenes'];history=j.setdefault('redo_history',[])
    def remember(item,file):
        history.append({'slot':item,'file':file,'note':note,'at':now()})
        if item.startswith('clip:'):
            # Earlier failed submissions for this scene were resolved by the received clip: never resurrect them as uncertain.
            for t in STATE['tasks']:
                if t['job']==j['id'] and t['slot']==item and t.get('kind')=='flow_video' and t['status']=='failed':t.setdefault('acknowledged',now())
    if kind in ('image','clip'):
        index=int(slot.split(':')[1])
        if index>=len(scenes):raise ValueError('Scène inconnue')
        scene=scenes[index]
    if kind in ('characters','character'):
        targets=j['characters'] if kind=='characters' else [c for c in j['characters'] if c['id']==slot.split(':')[1]]
        if not targets:raise ValueError('Personnage inconnu')
        if any(x.get('image') for x in scenes):raise ValueError('Les scènes utilisent déjà ces personnages : refaites plutôt les images concernées')
        if not any(c.get('file') for c in targets):raise ValueError('Rien à refaire : élément pas encore créé')
        for c in targets:
            if c.get('file'):remember('character:'+c['id'],c.pop('file'))
        if kind=='characters':j.pop('character_sheet_file',None)
        for x in [x for x in j.get('state_sheets') or [] if any(x['character']==c['id'] for c in targets) or kind=='characters']:
            # A state sheet is drawn from the reference: it is drawn again after it.
            if x.get('file'):remember(slot_of_state(j,x),x['file'])
            j['state_sheets'].remove(x)
    elif kind=='state':
        changes=state_changes(j);k=int(slot.split(':')[1])
        entry=state_entry(j,changes[k]) if k<len(changes) else None
        if not entry or not entry.get('file'):raise ValueError('Rien à refaire : feuille d’état pas encore créée')
        later=[i+1 for i,x in enumerate(scenes) if i>=entry['from_scene']-1 and x.get('image') and entry['character'] in (x.get('characters') or [])]
        if later:raise ValueError('Les planches '+', '.join(map(str,later))+' utilisent déjà cette feuille : refaites plutôt les planches concernées')
        remember(slot,entry['file']);j['state_sheets'].remove(entry)
    elif kind=='image':
        if not scene.get('image'):raise ValueError('Rien à refaire : image pas encore créée')
        if scene.get('clip') and not include_clip:raise ValueError('Le clip de cette scène a été animé depuis cette image : refaites l’image et le clip ensemble')
        remember(slot,scene.pop('image'))
        if scene.get('clip'):remember(f'clip:{index}',scene.pop('clip'))
        if include_clip:j.setdefault('corrections',{})[f'clip:{index}']=note
        engine_chain.reset(scene)  # a new board: every engine may try it again
    elif kind=='clip':
        # 0.1.93: a clip that no engine could make is redone with the owner's instruction, from the first engine.
        if not scene.get('clip') and not scene.get('engine_exhausted'):raise ValueError('Rien à refaire : clip pas encore créé')
        if scene.get('clip'):remember(slot,scene.pop('clip'))
        engine_chain.reset(scene)
    else:
        if not j.get('cover_file'):raise ValueError('Rien à refaire : couverture pas encore créée')
        remember('cover',j.pop('cover_file'));j.pop('cover',None)
    if note:j.setdefault('corrections',{})[slot]=note
    else:j.get('corrections',{}).pop(slot,None)
    # Downstream results are now stale: re-check, re-cover nothing paid twice, re-render.
    for key in ('final','qc'):j.pop(key,None)
    order=['characters','images','clips','quality','cover','edit','done']
    target=REDO_STAGES[kind]
    if j.get('stage') not in order or order.index(target)<order.index(j['stage']):j['stage']=target
    j['status']='running'
    event(j,'À refaire : '+slot+(' — correction : '+note if note else '')+'. Fichier précédent conservé.')
    if start:schedule(j)  # start=False: the caller redoes several items, then schedules once

def board_gate(j):
    """Atelier "Planches de la boucle complète": True while the board check holds the clips back."""
    level=j['config'].get('board_controls','none')
    if level=='none' or j.get('board_checked'):return False
    review=j.get('board_review')
    if not review:
        d=job_dir(j);sheets=board_check.make_sheets(d,[s['image'] for s in j['scenes']])
        attachments=image_assets(j)+[asset_url(j,x['file']) for x in j.get('state_sheets') or [] if x.get('file')]+[asset_url(j,x) for x in sheets]
        add_task(j,'chat_text',{'provider':'chatgpt','prompt':board_check.prompt(j),'attachments':attachments,'response_kind':'board_review','scene_count':len(j['scenes'])},'board_review')
        event(j,'Contrôle des planches avant les clips : ChatGPT compare chaque planche à la feuille des personnages.');return True
    bad=board_check.failing(review);j['board_checked']=now()
    if not bad:event(j,'Planches contrôlées : toutes conformes.');return False
    detail=' ; '.join(f"planche {b['index']+1} : {b['detail']}" for b in review['boards'] if b['status']=='issue')
    if level=='report':
        event(j,'Planches signalées (non redessinées, réglage « Signaler seulement ») — '+detail);return False
    todo=bad[:board_check.MAX_REDRAW]
    for i in todo:
        # Redrawn once with the reason as correction; the previous board stays in redo_history.
        s=j['scenes'][i];j.setdefault('redo_history',[]).append({'slot':f'image:{i}','file':s.pop('image'),'note':'contrôle des planches','at':now()})
        j.setdefault('corrections',{})[f'image:{i}']='Board check: '+next(b['detail'] for b in review['boards'] if b['index']==i)+' Fix this, keep everything else.'
    event(j,'Planche(s) '+', '.join(str(i+1) for i in todo)+' redessinée(s) une fois après le contrôle — '+detail)
    schedule(j);return True

def auto_redo(j,report,issues=()):
    """Atelier-like "Refaire tout seul": a clip flagged by the checks is regenerated once, then the owner decides."""
    bad=sorted({i for i,c in enumerate(report.get('clips',[])) if (c.get('speech') or {}).get('match') is not None and c['speech']['match']<quality.MIN_MATCH}|{x['index'] for x in issues if isinstance(x.get('index'),int) and x.get('status')=='issue'})
    # "uncertain" means the stills cannot tell (owner decision 03/11): never paid for again on a guess, the owner looks.
    done=set(j.setdefault('auto_redone',[]));todo=[i for i in bad if i not in done and i<len(j['scenes'])]
    todo=[i for i in todo if j['scenes'][i].get('clip')]
    # All flagged clips are detached first, then one schedule: redoing them one by one made the second redo
    # see the first one's queued task and fail ("Une tâche est en cours"), leaving the episode half redone.
    for i in todo:
        redo(j,'clip:'+str(i),'Refait automatiquement après le contrôle qualité : respecter exactement le dialogue et la continuité.',start=False)
        j['auto_redone'].append(i)
    if todo:event(j,'Contrôle qualité : clip(s) '+', '.join(str(i+1) for i in todo)+' refait(s) une fois, automatiquement.');schedule(j)
    return bool(todo)

def schedule_quality(j):
    folder=job_dir(j);key=quality.fingerprint(j,folder);report=j.get('quality_report',{})
    if j['config'].get('controls')=='none':
        # "Pas de contrôle": the owner chose to skip the checks and go straight to the cover.
        j['stage']='cover';event(j,'Contrôles désactivés par le propriétaire : passage direct à la miniature.');schedule(j);return
    if report.get('fingerprint')!=key:
        if j['id'] not in QUALITY_BUSY:
            QUALITY_BUSY.add(j['id']);event(j,'Contrôle local des clips, transcription et préparation des images de revue démarrés.')
            threading.Thread(target=run_quality,args=(j['id'],key),daemon=True).start()
        return
    report['auto']=quality.decision(report,[x for x in [*report.get('visual',{}).get('scenes',[]),report.get('visual',{}).get('continuity',{})] if x and x.get('status')!='pass'])
    if report.get('hard_errors'):
        j['status']='attention';alert(j,'action','Contrôle qualité bloquant : '+report['hard_errors'][0]+' Les clips sont conservés ; remplace le média en cause puis relance la boucle complète.');return
    if report.get('warnings') and j.get('quality_speech_approval')!=key and j.get('quality_approval')!=key:
        if j['config'].get('controls')=='redo' and auto_redo(j,report):return
        low=[f"{i+1} ({round(c['speech']['match']*100)} %)" for i,c in enumerate(report.get('clips',[])) if (c.get('speech') or {}).get('match') is not None and c['speech']['match']<quality.MIN_MATCH]
        if j.get('autopilot'):
            j['quality_speech_approval']=key;j['autopilot_approval']=key
            alert(j,'auto','Paroles acceptées automatiquement (boucle complète) malgré un écart avec le scénario : scène(s) '+(', '.join(low) or '?')+'. Souvent une erreur de transcription ; écoute ces scènes avant de publier.')
        else:
            j['status']='attention';alert(j,'action','Paroles à vérifier : scène(s) '+(', '.join(low) or '?')+' sous 85 %. Écoute-les, puis « J’ai écouté les dialogues » ou « Boucle complète » pour laisser le studio décider.');return
    visual=report.get('visual')
    if not visual and j['config'].get('clip_look')=='ear':
        # "À l'oreille seulement": no ChatGPT look at the clips; said plainly in the report, never shown as checked.
        visual=report['visual']={'skipped':True,'scenes':[{'index':i,'status':'pass','detail':'Non regardé : contrôle à l’oreille seulement (réglage du propriétaire).'} for i in range(len(j['scenes']))],
                                 'continuity':{'status':'pass','detail':'Non regardée : contrôle à l’oreille seulement.'}}
        event(j,'Clips contrôlés à l’oreille seulement : aucune revue visuelle demandée à ChatGPT.')
    if not visual:
        attachments=image_assets(j)
        attachments += [asset_url(j,c['sheet']) for c in report['clips'] if c.get('sheet')]
        add_task(j,'chat_text',{'provider':'chatgpt','prompt':quality.visual_prompt(j),'attachments':attachments,'response_kind':'quality_review','scene_count':len(j['scenes']),'fingerprint':key},'quality_review');return
    issues=[x for x in [*visual['scenes'],visual['continuity']] if x['status']!='pass']
    if issues and j.get('quality_approval')!=key:
        if j['config'].get('controls')=='redo' and auto_redo(j,report,issues):return
        where=', '.join(str(x['index']+1) for x in issues if isinstance(x.get('index'),int)) or 'continuité'
        if j.get('autopilot'):
            j['quality_approval']=key;j['autopilot_approval']=key
            alert(j,'auto','Réserves visuelles acceptées automatiquement (boucle complète) : scène(s) '+where+' — '+issues[0]['detail']+' Regarde ces scènes dans la vidéo finale.')
        else:
            j['status']='attention';alert(j,'action','Cohérence visuelle à vérifier (scène(s) '+where+') : '+issues[0]['detail']+' Médias conservés, aucun nouvel envoi Flow.');return
    report['status']='approved_with_reservations' if report.get('warnings') or issues else 'checked'
    report['auto']=quality.decision(report,issues)
    if report['auto']['decision']=='review':report['auto']['approved_by']='autopilot' if j.get('autopilot_approval')==key else 'owner'
    (folder/'quality-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    j['stage']='cover';event(j,'Contrôles disponibles terminés. Synchronisation labiale et identité des voix restent à vérifier à l’écoute.');schedule(j)

def run_quality(id,key):
    try:
        with LOCK:
            j=copy.deepcopy(job_by(id));folder=job_dir(j)
        config=folder/'quality-input.json';config.write_text(json.dumps(j,ensure_ascii=False),'utf-8')
        result=subprocess.run([sys.executable,str(ROOT/'quality.py'),str(config)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=1200)
        if result.returncode:raise RuntimeError('Analyse locale impossible : '+result.stderr[-500:])
        report=json.loads((folder/'quality-local.json').read_text('utf-8'))
        with LOCK:
            actual=job_by(id)
            if not actual or quality.fingerprint(actual,folder)!=key or actual.get('stage')!='quality':return
            actual['quality_report']=report
            event(actual,'Analyse des fichiers et des paroles terminée ; résultats disponibles dans le rapport qualité.')
            if actual['status']!='paused':actual['status']='running'
            QUALITY_BUSY.discard(id);schedule(actual);save()
    except Exception as e:
        with LOCK:
            actual=job_by(id)
            if actual and actual.get('stage')=='quality':
                actual['status']='attention' if actual['status']!='paused' else 'paused';event(actual,'Contrôle qualité interrompu : '+str(e));save()
    finally:QUALITY_BUSY.discard(id)


def review_pending(j):
    return bool(j.get('config',{}).get('review_script')) and not j.get('script_approved')

def script_editable(j):
    return j.get('stage')=='characters' and not j.get('script_approved') and not any(c.get('file') for c in j.get('characters',[])) \
        and not any(t['job']==j['id'] and t['status'] in ('queued','claimed') for t in STATE['tasks'])

def edit_script(j,changes):
    """Owner corrections of title, cover, description and dialogue before any image is paid."""
    if not script_editable(j):raise ValueError('L’histoire ne peut plus être modifiée : les images ont commencé ou une tâche est en cours')
    draft=copy.deepcopy(j['script'])
    for key in ('title','cover_title','description'):
        if key in changes:draft[key]=str(changes[key]).strip()
    edited=changes.get('scenes')
    if edited is not None:
        if not isinstance(edited,list) or len(edited)!=len(draft['scenes']):raise ValueError('Une correction par scène est attendue')
        for scene,change in zip(draft['scenes'],edited):
            lines=change.get('dialogue') if isinstance(change,dict) else None
            if not isinstance(lines,list):raise ValueError('Dialogue de scène attendu')
            scene['dialogue']=[{'speaker':str(x.get('speaker','')),'text':' '.join(str(x.get('text','')).split())} for x in lines if isinstance(x,dict)]
    if draft==j['script']:return False
    validate_script(draft,j['config']['scene_count'],word_limit=max(25,engines.word_limit(j)))
    if j.get('editorial_version')==2 and j.get('retention_version')==1:
        for i,scene in enumerate(draft['scenes']):
            if len(scene['dialogue'])>engines.MAX_DIALOGUE_TURNS or len({x['speaker'] for x in scene['dialogue']})>2 or sum(len(x['text'].split()) for x in scene['dialogue'])>engines.word_limit(j):
                raise ValueError(f"Scène {i+1} : trois répliques entre deux personnages et {engines.word_limit(j)} mots au plus pour tenir dans le clip de {engines.spec(j)['seconds']} secondes")
    j['script']=draft;j['title']=draft['title']
    for scene,source in zip(j['scenes'],draft['scenes']):scene['dialogue']=copy.deepcopy(source['dialogue'])
    d=job_dir(j);(d/'scenario.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2),'utf-8');(d/'description.txt').write_text(draft['description'],'utf-8')
    event(j,'Histoire corrigée par le propriétaire avant les images.')
    return True

def store_script(j,s):
    if s.get('production_id') and s['production_id']!=j['id']:raise ValueError('Ce scénario appartient à une autre production')
    identical=is_identical(j)
    validate_script(s,j['config']['scene_count'],check_size=not identical,word_limit=engines.word_limit(j),max_chars=8 if identical else 5)
    if identical:
        # Faithful remake: no concept comparison, no novelty check against the history; only what fits in the clips.
        # Like the Atelier, every defect is listed in one refusal: one rewrite fixes them all (one per refusal cost 5 min each).
        problems=size_problems(s['characters'])
        # The prompt asks for word_limit; the refusal only falls past 3 words a second (the Atelier refuses 22 words in 6 s,
        # not 21): a rewrite costs 5 to 7 min, one word over is not worth it.
        # Moteur V09: the lines of the source window (up to 4 turns, 3 voices), about 3 words a second.
        limit=max(engines.word_limit(j),int(3*engines.spec(j)['seconds']))+3
        for i,scene in enumerate(s['scenes']):
            lines=scene.get('dialogue',[]);words=sum(len(x['text'].split()) for x in lines)
            if len(lines)>4 or len({line['speaker'] for line in lines})>3 or words>limit:
                problems.append(f"Scène {i+1} : {len(lines)} réplique(s) et {words} mots, quatre répliques entre trois personnages et {limit} mots au plus pour tenir dans le clip de {engines.spec(j)['seconds']} secondes ; enlève des mots, n'allonge rien")
            ref=scene.get('ref')
            scene['ref']=_txt(ref,40) if isinstance(ref,str) and ref.strip() else None
            if not scene['ref']:scene.pop('ref')
        if problems:raise ValueError(' ; '.join(problems))
    else:
        if j.get('sheet_approved'):
            editorial.restore_approved_choices(s,j)
            validate_script(s,j['config']['scene_count'],word_limit=engines.word_limit(j))
        editorial.validate(s,j,STATE['jobs'])
    j.pop('editorial_feedback',None);j.pop('rejected_script',None)
    j['script']=s; j['characters']=copy.deepcopy(s['characters']); j['scenes']=copy.deepcopy(s['scenes']); j['title']=s['title']; j['stage']='characters'; j['status']='running'
    v=j.get('variant') or {}
    if v.get('kind')=='language':
        # Same boards and cast images: only the clips (voices) are made again.
        files=v.get('character_files',{})
        for c in j['characters']:
            if files.get(c['id']):c['file']=files[c['id']]
        if v.get('sheet'):j['character_sheet_file']=v['sheet']
        for scene,image in zip(j['scenes'],v.get('images',[])):
            if image:scene['image']=image
    previous=job_by(j.get('series',{}).get('previous')) if j.get('series') else None
    if previous:
        reused=series.inherit(j,previous,job_dir(previous),job_dir(j))
        if reused:event(j,'Série : images de référence reprises de la partie précédente pour '+', '.join(reused)+' (aucune image repayée).')
    d=job_dir(j); (d/'scenario.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),'utf-8'); (d/'description.txt').write_text(s['description'],'utf-8'); event(j,'Scénario structuré validé ; langue de création : '+j['config'].get('language','Deutsch (de-DE)')+'.')

def apply_research(j,rows):
    if j.get('filon_only'):
        # Filon refresh: keep the gallery, never start a story.
        candidates=rank_candidates(rows,j['config'].get('language','Deutsch (de-DE)'))[:60]
        if not candidates:
            j['status']='attention'
            event(j,'TikTok n’a renvoyé aucun lien vidéo exploitable. Ouvre TikTok dans la fenêtre FruchtDrama, vérifie la recherche puis actualise à nouveau.')
            return
        j['candidates']=candidates;j['stage']='done';j['status']='done'
        for c in j['candidates']:c['niche']=j['config'].get('filon_niche','Fruits')
        thumbs.warm([c['url'] for c in j['candidates']],DATA)
        STATE.setdefault('settings',{})['filon_refreshed']=now();event(j,'Filon actualisé : '+str(len(j['candidates']))+' vidéo(s).');return
    if j.get('editorial_version')!=2:
        ranked=rank_candidates(rows,j['config'].get('language','Deutsch (de-DE)'));j['candidates']=ranked
        measured=[r for r in ranked if any(r[k] is not None for k in ('views','likes','signal'))]
        if len(measured)<3:
            j['status']='waiting_research';event(j,'Moins de trois candidats chiffrés. Ajoutez des références vérifiables ou choisissez explicitement une référence.');return
        j['selected']=measured[0];j['stage']='script';j['status']='running';event(j,'Référence sélectionnée : '+measured[0]['url']+' — classement par '+measured[0]['basis']+' ; aucun top national affirmé.');return
    pool=j.get('research_pool',[])+rows[:40]
    ranked=rank_candidates(pool,j['config'].get('language','Deutsch (de-DE)'))[:60]
    j['candidates']=ranked
    j['research_pool']=ranked
    used={x.get('selected',{}).get('url') for x in editorial.recent(j,STATE['jobs'])}
    unused=[r for r in ranked if r['url'] not in used]
    views=[r for r in unused if r['views'] is not None]
    likes=[r for r in unused if r['likes'] is not None]
    measured=views if len(views)>=3 else sorted(likes,key=lambda r:r['likes']/(r['age_days'] or 30),reverse=True) if len(likes)>=3 else []
    if len(measured)<3:
        queries=j.get('research_queries',[]);round=j.get('research_round',0)
        if round+1<len(queries):
            j['research_round']=round+1;j['status']='running';j['stage']='research';event(j,'Recherche élargie automatiquement : références répétées ou moins de trois compteurs identifiés.');return
        j['status']='waiting_research'; event(j,'Moins de trois références inédites avec des compteurs identifiés et comparables. Les compteurs inconnus ne prouvent pas la viralité. Ajoutez des références vérifiables ou choisissez explicitement une référence.'); return
    j['selected']=measured[0]; j['stage']='script'; j['status']='running'; event(j,'Référence sélectionnée : '+measured[0]['url']+' — classement par '+measured[0]['basis']+' ; aucun top national affirmé.')

def accept_task_result(t,result):
    j=job_by(t['job'])
    was_paused=j['status']=='paused'
    if t.get('slot')=='cover_review' and j.get('stage')!='cover':
        t['status']='cancelled'
        return
    if not result.get('ok') and t.get('kind') in ('flow_video','engine_video') and result.get('dry_run') is True and t.get('payload',{}).get('dry_run') and result.get('generation_submitted') is False:
        t['status']='cancelled';t['dry_run_passed']=now();j['dry_run_passed']=now();j['status']='paused'
        event(j,str(result.get('error','Essai à blanc réussi.'))[:600]+' Désactivez l’essai à blanc puis cliquez sur Reprendre pour générer réellement.')
        return
    raw=result.get('raw') if not result.get('ok') else None
    if isinstance(raw,str) and t.get('slot')=='script' and t.get('kind') in ('chat_text','chat_collect') and t['id'] in raw:
        # The extension could not read the scenario: the studio keeps the raw reply and reads it itself (lenient JSON);
        # a defect then goes to the usual light correction with its exact reason, instead of « À vérifier ».
        name=f"script_raw_{t['id'][:8]}.txt";(job_dir(j)/name).write_text(raw[:400000],'utf-8')
        event(j,f'Réponse de ChatGPT relue par le studio ({len(raw)} caractères, copie {name}).')
        result={'ok':True,'text':repair_json(raw)}
    if not result.get('ok'):
        kind=errors.classify(result);t['error_kind']=kind
        if (not was_paused and j.get('autopilot') and t.get('slot')=='cover_review'
                and kind in errors.RETRYABLE and j.get('cover_file')
                and (t.get('payload') or {}).get('file')==j['cover_file']):
            t['status']='failed'
            j['cover_review_unavailable']=j['cover_file']
            alert(j,'auto','Revue automatique de la miniature indisponible. La miniature existante est conservée et le montage continue. Vérifie-la avant publication.')
            schedule(j)
            return
        if (not was_paused and j.get('autopilot') and t.get('kind') in ('chat_text','chat_image')
                and result.get('generation_submitted') is False and kind in errors.RETRYABLE
                and not any(old.get('retried_before_send') for old in STATE['tasks']
                            if old['job']==j['id'] and old.get('slot')==t.get('slot'))):
            t['status']='failed';t['retried_before_send']=True
            event(j,'Incident de connexion au navigateur avant l’envoi : nouvel essai automatique unique.')
            schedule(j)
            return
        j['last_error']={'kind':kind,'slot':t.get('slot'),'task':t.get('id'),'at':now()}
        reservation=t.get('reservation')
        if t.get('kind')=='flow_video' and result.get('generation_submitted') is False and reservation and not reservation.get('refunded'):
            p=profile_by(reservation['profile'])
            if p:p['balance']+=reservation['amount'];reservation['refunded']=True;event(j,'Réservation locale de crédits annulée : aucune génération n’a été envoyée à Flow.')
        elif t.get('kind')=='flow_video' and result.get('flow_failed') is True and reservation and not reservation.get('refunded'):
            # Flow showed its own failure message after the submission: a failed generation is not charged by Flow.
            p=profile_by(reservation['profile'])
            if p:p['balance']+=reservation['amount'];reservation['refunded']=True;event(j,'Flow a affiché un échec de génération : réservation locale annulée (Flow ne facture pas un clip échoué).')
        # 0.1.93: one try per engine and per clip (Flow, Arena, Vidogrid, Grok), then a softened prompt, then the owner.
        if not was_paused and clip_failed(j,t,result,kind):return
        t['status']='failed'; j['status']='paused' if was_paused else 'attention'; event(j,errors.message(kind,result.get('error')))
        name=quotas.service(t)
        if kind=='quota' and name and not was_paused:
            moment=time.time();quotas.note_wall(STATE,name,moment,errors.retry_after(result),result.get('error',''))
            j['status']='running';schedule(j)  # add_task sees the wall and sets waiting_quota
            return
        if kind=='refusal' and refusal.applies(t) and not was_paused:
            level=j.setdefault('refusal_levels',{}).get(t['slot'],0)+1
            if level<=refusal.MAX_LEVEL:
                j['refusal_levels'][t['slot']]=level;j['status']='running'
                event(j,'Image refusée par ChatGPT : reformulation automatique niveau '+str(level)+' sur '+str(refusal.MAX_LEVEL)+' (même style, vocabulaire adouci).');schedule(j);return
            k=int(t['slot'].split(':')[1]) if t['slot'].startswith('state:') else None
            if k is not None and k<len(state_changes(j)) and not state_entry(j,state_changes(j)[k]):
                # A state sheet is an extra: refused for good, the boards keep the reference sheet and production goes on.
                j.setdefault('state_sheets',[]).append({**state_changes(j)[k],'skipped':now()});j['status']='running'
                event(j,'Feuille d’état refusée par ChatGPT même reformulée : les planches gardent la feuille des personnages.');schedule(j);return
            event(j,'ChatGPT refuse cette image même reformulée (niveau '+str(refusal.MAX_LEVEL)+'). Corrigez la consigne avec « Refaire » ou importez l’image.')
            return
        if t.get('kind')=='engine_video' and kind=='quota' and not was_paused:
            # P5-08: the account reached its limit: remember it, then switch account or wait.
            moment=time.time();account=engine_accounts.by_id(STATE,j.get('engine_account'))
            if account:engine_accounts.wall(account,moment,errors.retry_after(result),result.get('error',''))
            if account or engine_accounts.accounts(STATE,t['payload']['engine']):j['status']='running';schedule(j)
            elif j.get('stage')=='images':
                # A clip sent ahead hit the limit: the boards go on, the clips wait for the clips stage (and its quota wait).
                j['early_clips_off']=True;j['status']='running'
                event(j,'Limite atteinte sur ce compte pendant les planches : les planches continuent, les clips attendront la fin des planches.');schedule(j)
            else:
                j['status']='waiting_quota';j['wait_until']=moment+(errors.retry_after(result) or engine_accounts.DEFAULT_WALL)
                event(j,'Limite atteinte sur ce compte. Reprise automatique vers '+clock_in(j['wait_until'])+'. Enregistrez d’autres comptes dans Connexions pour changer de compte.')
            return
        note_not_ready(t,result)
        if t.get('kind')=='flow_video' and result.get('generation_submitted') is False and result.get('flow_blocked') in ('credits','unavailable','not_ready') and t.get('payload',{}).get('flow_route'):
            # No credits, or no Flow access at all for this Google account: skip it, switch to the next one.
            p=profile_by(t.get('profile'))
            if p and result['flow_blocked']!='not_ready':p['blocked']=result['flow_blocked']
            if p and result['flow_blocked']=='not_ready' and isinstance(result.get('not_ready'),dict):
                # The account page opened but Flow did not work there: set aside 3 h, whatever the next opening check says.
                p['hold_until']=time.time()+3*3600;p['hold_reason']=str(result['not_ready'].get('reason',''))[:300]
            if not was_paused and STATE.get('settings',{}).get('flow_auto'):
                j['status']='running';schedule(j)
        if lane_of(t)=='video' and j.get('stage')=='images' and j['status']=='attention' and not was_paused:
            # A clip sent ahead failed: the boards go on (ChatGPT is not blocked by Flow); the clips wait for the clips
            # stage, where a possibly sent clip is checked by the owner before anything is sent again.
            j['early_clips_off']=True;j['status']='running'
            alert(j,'action','Clip '+str(int(t['slot'].split(':')[1])+1)+' en échec ('+str(result.get('error','')).split(' : ')[0][:120]+'). Les planches continuent ; vérifie le projet Flow avant que les clips reprennent.')
            j['alerts'][-1]['stage']='images'  # said for the boards stage only: dropped when the clips stage starts
            schedule(j)
        return
    slot=t['slot']
    if slot=='research': apply_research(j,result.get('candidates',[]))
    elif slot.startswith('flow_rewrite:'):apply_flow_rewrite(j,t,result)
    elif slot=='board_review':
        j['board_review']=board_check.validate(parse_json(result.get('text','')),j,t['id'])
    elif slot=='cover_review':
        answer=parse_json(result.get('text',''))
        if not isinstance(answer,dict) or answer.get('production_id')!=j['id'] or not isinstance(answer.get('ok'),bool):raise ValueError('Avis sur la miniature illisible : {"ok": true|false, "problem": "…"} attendu')
        j['cover_review']={'file':t['payload'].get('file'),'ok':answer['ok'],'problem':str(answer.get('problem') or '')[:300]}
    elif slot=='quality_review':
        if quality.fingerprint(j,job_dir(j))!=t['payload'].get('fingerprint'):raise ValueError('Médias changés pendant le contrôle : rapport non applicable')
        review=quality.validate_visual(parse_json(result.get('text','')),j,t['id'])
        j['quality_report']['visual']=review
        (job_dir(j)/'quality-report.json').write_text(json.dumps(j['quality_report'],ensure_ascii=False,indent=2),'utf-8')
        event(j,'Revue visuelle IA reçue ; lèvres et identité des voix restent non certifiées.')
    elif slot=='rewrite_meta':
        # Originality: new title, hook and description in the owner's own words, then a new score.
        data=parse_json(result.get('text',''))
        for key,limit in (('title',80),('cover_title',60),('hook_text',70),('description',2200)):
            if isinstance(data.get(key),str) and data[key].strip():j['script'][key]=' '.join(data[key].split())[:limit] if key!='description' else data[key].strip()[:limit]
        j['title']=j['script']['title'];d=job_dir(j);(d/'description.txt').write_text(j['script']['description'],'utf-8')
        if j.get('publication'):
            kit=series.kit(j);(d/'publication.json').write_text(json.dumps(kit,ensure_ascii=False,indent=2),'utf-8');(d/'publication.txt').write_text(series.kit_text(kit),'utf-8')
        event(j,'Titre, accroche et description réécrits pour s’éloigner de l’original.');check_originality(j)
    elif slot in ('ideas','sheet'):
        try:
            data=parse_json(result.get('text',''))
            if slot=='ideas':j['ideas']=ideas.validate_ideas(data)
            else:
                j['sheet']=ideas.validate_sheet(data);j.pop('sheet_approved',None);j.pop('sheet_previous',None);j.pop('sheet_note',None)
                if (j.get('selected') or {}).get('source')=='owner_link':j['sheet_precheck']=originality.precheck(j['sheet'],reference_text(j))
            j.pop('start_attempts',None)
        except ValueError as e:
            t['status']='failed';t['error']=str(e);j['start_attempts']=j.get('start_attempts',0)+1
            j['status']='paused' if was_paused else 'running' if j['start_attempts']<=2 else 'attention'
            event(j,('Histoires' if slot=='ideas' else 'Fiche')+' inexploitable : '+str(e)+(' Nouvelle demande envoyée.' if j['status']=='running' else ''))
            schedule(j);return
    elif slot=='script':
        draft=None
        try:
            draft=parse_json(result.get('text',''));store_script(j,draft);j.pop('rejected_script',None)
        except ValueError as e:
            # Kept for a light correction (Atelier-like): the next request sends this script and its defects only.
            if isinstance(draft,dict) and isinstance(draft.get('scenes'),list) and len(draft['scenes'])==j['config']['scene_count']:j['rejected_script']=copy.deepcopy(draft)
            # Editorial refusals and structurally invalid JSON share the same bounded rewrite.
            t['status']='failed';t['error']=str(e);j['editorial_attempts']=j.get('editorial_attempts',0)+1
            j['editorial_feedback']=[str(e)];j['stage']='script'
            j['status']='paused' if was_paused else 'running' if j['editorial_attempts']<=2 else 'attention'
            event(j,'Scénario refusé avant les images : '+str(e)+(' Réécriture automatique demandée.' if j['status']=='running' else ''))
            schedule(j);return
    else:
        file=result.get('file','')
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+',file) or not (job_dir(j)/file).is_file(): raise ValueError('Fichier média reçu absent')
        if slot.startswith('character:'): next(c for c in j['characters'] if c['id']==slot.split(':')[1])['file']=file
        elif slot=='characters':
            j['character_sheet_file']=file
            for c in j['characters']:c['file']=file
        elif slot.startswith('state:'):
            changes=state_changes(j);k=int(slot.split(':')[1])
            if k>=len(changes):raise ValueError('Feuille d’état inconnue')
            change=changes[k];base=state_base(j,change)
            if base and (job_dir(j)/base).is_file() and image_fingerprint(j,file)==image_fingerprint(j,base):raise ValueError('Feuille d’état rejetée : copie exacte de la feuille de référence. Attente de la feuille modifiée.')
            j['state_sheets']=[x for x in j.get('state_sheets') or [] if x is not state_entry(j,change)]+[{**change,'file':file}]
            j['state_sheets'].sort(key=lambda x:x['from_scene'])
        elif slot.startswith('image:'):
            index=int(slot.split(':')[1])
            if duplicate_scene_source(j,file,index):raise ValueError('Image rejetée : copie exacte d’une référence ou d’une autre scène. Attente de la véritable image générée.')
            j['scenes'][index]['image']=file
        elif slot.startswith('clip:'):
            sc=j['scenes'][int(slot.split(':')[1])];sc['clip']=file
            # The engine that made it (montage length, quality range) ; the next clip starts again from the first engine.
            if t.get('kind') in ('flow_video','engine_video'):sc['engine']='flow' if t['kind']=='flow_video' else t['payload'].get('engine')
            # And the account that made it (0.1.95): « Flow · compte 2 » under the clip.
            made_by=account_usage.clip_account(t,STATE['profiles']) if t.get('kind') in ('flow_video','engine_video') else None
            if made_by:sc['account']=made_by
            else:sc.pop('account',None)
            engine_chain.reset(sc)
            # The board the clip was animated from: a later board change shows « la planche a changé après le clip ».
            sc['clip_from']=sc.get('image');sc.pop('text_after_clip',None)
        elif slot=='cover':
            if duplicate_scene_source(j,file,-1) or ((job_dir(j)/'cover-style-reference.png').is_file() and image_fingerprint(j,file)==image_fingerprint(j,'cover-style-reference.png')):raise ValueError('Couverture rejetée : copie exacte d’une référence. Attente de la couverture composée.')
            j['cover_file']=file;j['cover']=asset_url(j,file)
        # Atelier-like progress line (« Planche 6 reçue ») instead of a file name (owner 09/11/2026, UI review).
        kind,_,num=slot.partition(':')
        label={'image':f'Planche {int(num)+1} reçue' if num.isdigit() else 'Planche reçue','clip':f'Clip {int(num)+1} reçu' if num.isdigit() else 'Clip reçu',
               'cover':'Miniature reçue','characters':'Feuille des personnages reçue','character':'Fiche personnage reçue',
               'state':'Feuille d’état reçue'}.get(kind,'Média reçu')
        event(j,label+(f" ({engines.ENGINES.get(sc.get('engine'),{}).get('label','')})" if kind=='clip' and num.isdigit() and (sc:=j['scenes'][int(num)]).get('engine') else '')+'.')
    t['status']='done'; t['result']=result;t['done_at']=now()  # done_at: Studio counts per 6 h
    if t.get('kind')=='flow_video' and profile_by(t.get('profile')):profile_by(t['profile'])['readiness']={'state':'ready','reason':'','at':now()}
    # A success clears the episode's last error only on its own lane: a board received does not erase a failed clip.
    failed=next((x for x in STATE['tasks'] if x.get('id')==(j.get('last_error') or {}).get('task')),None)
    if not failed or lane_of(failed)==lane_of(t):j.pop('last_error',None)
    if quotas.service(t) and t.get('kind') in ('chat_image','chat_text'):quotas.note_pass(STATE,quotas.service(t),time.time())
    j.get('refusal_levels',{}).pop(slot,None)
    if was_paused: j['status']='paused'
    schedule(j)

def note_not_ready(t,result):
    """A provider page that did not open (sign-in, anti-robot check, empty page): the account is marked « À régler » in
    Mes comptes with the exact reason, and the next ready Flow account takes the clip."""
    info=result.get('not_ready')
    if not isinstance(info,dict) or info.get('state') not in readiness.NOT_READY:return False
    kind=t.get('kind');payload=t.get('payload') or {}
    key=('flow:'+str(t.get('profile'))) if kind=='flow_video' else ('site:'+str(payload.get('engine'))) if kind=='engine_video' else ('site:'+str(payload.get('provider') or 'chatgpt')) if kind in ('chat_text','chat_image','chat_collect','chat_image_collect') else None
    return bool(key) and readiness.mark(STATE,key,info['state'],str(info.get('reason') or 'page du fournisseur indisponible'),now())

def run_command(args,cwd=None):
    r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240,cwd=cwd)
    if r.returncode: raise RuntimeError(r.stderr[-1800:])

def clip_duration(probe,src):
    try:
        out=subprocess.run([probe,'-v','error','-show_entries','format=duration','-of','csv=p=0',str(src)],capture_output=True,text=True,timeout=30).stdout.strip()
        return float(out)
    except (ValueError,OSError,subprocess.SubprocessError):return None

def make_variant(j,kind,language=''):
    # Atelier-like "Version horizontale 16:9" and "Langues": a new episode from this one (caller holds LOCK).
    if not j.get('script') or not any(x.get('image') for x in j['scenes']):raise ValueError('Il faut une histoire et ses planches')
    if kind not in ('horizontal','language'):raise ValueError('Version inconnue')
    cfg={**copy.deepcopy(j['config']),'dry_run':False,'also_horizontal':False}
    if kind=='horizontal':
        if horizontal(j):raise ValueError('Cet épisode est déjà horizontal')
        cfg['format']='horizontal'
    else:
        cfg['language']=creation_language(language)
        if cfg['language']==j['config'].get('language'):raise ValueError('Choisissez une autre langue')
        cfg['query']=RESEARCH_QUERIES[cfg['language']]
    nxt={'id':uid(),'title':j['title']+(' · 16:9' if kind=='horizontal' else ' · '+cfg['language'].split(' ')[0]),'brief':j.get('brief',''),'config':cfg,'selected':j.get('selected'),
         'variant':{'kind':kind,'of':j['id']},'flow_profile':j.get('flow_profile'),'status':'running','created':now(),'updated':now(),'events':[],'candidates':[],
         'characters':copy.deepcopy(j['characters']),'scenes':[],'character_sheet':j.get('character_sheet'),'cover_style':j.get('cover_style'),'quality_version':j.get('quality_version')}
    src,dst=job_dir(j),None
    STATE['jobs'].insert(0,nxt);dst=job_dir(nxt)
    # State sheets come along (« Au fil de l'histoire »): never paid twice for the same story.
    nxt['state_sheets']=[dict(x) for x in j.get('state_sheets') or [] if x.get('file')]
    names=[f for f in [j.get('character_sheet_file')]+[c.get('file') for c in j['characters']]+[x['file'] for x in nxt['state_sheets']]+([x.get('image') for x in j['scenes']] if kind=='language' else []) if f]
    for f in dict.fromkeys(names):
        if (src/f).is_file():shutil.copyfile(src/f,dst/f)
    if kind=='horizontal':
        # Same story and cast; boards drawn again in landscape, then clips and montage.
        nxt['script']=copy.deepcopy(j['script']);nxt['scenes']=[{k:v for k,v in x.items() if k not in ('image','clip')} for x in j['scenes']]
        if j.get('character_sheet_file'):nxt['character_sheet_file']=j['character_sheet_file']
        nxt['script_approved']=now();nxt['stage']='images';(dst/'scenario.json').write_text(json.dumps(nxt['script'],ensure_ascii=False,indent=2),'utf-8');(dst/'description.txt').write_text(nxt['script'].get('description',''),'utf-8')
        event(nxt,'Version horizontale 16:9 de « '+j['title']+' » : même histoire et mêmes personnages, planches redessinées en paysage.')
    else:
        nxt['variant'].update(script=j['script'],images=[x.get('image') for x in j['scenes']],character_files={c['id']:c.get('file') for c in j['characters'] if c.get('file')},sheet=j.get('character_sheet_file'))
        nxt['characters']=[];nxt['stage']='script'
        event(nxt,'Version '+cfg['language']+' de « '+j['title']+' » : mêmes planches, répliques et voix refaites.')
    schedule(nxt);return nxt

def render_job(id):
    try:
        with LOCK:
            current=job_by(id)
            if current is None:return
            j=copy.deepcopy(current); d=job_dir(j)
        ff=shutil.which('ffmpeg')
        if not ff: raise RuntimeError('ffmpeg introuvable. Installe ffmpeg et relance le studio.')
        aligned_count=0
        caption_size,caption_words=(48,4) if j.get('retention_version')==1 else (38,5)
        k=min(frame_size(j))/720;caption_size=round(caption_size*k);m=lambda v:round(v*k)
        hook_text=' '.join(str((j.get('script') or {}).get('hook_text') or (j.get('script') or {}).get('cover_title') or '').split())[:70]
        ass=['[Script Info]','ScriptType: v4.00+',f'PlayResX: {frame_size(j)[0]}',f'PlayResY: {frame_size(j)[1]}','[V4+ Styles]','Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',f'Style: Default,Arial,{caption_size},&H00FFFFFF,&H0000FFFF,&H00141414,&H70000000,-1,0,0,0,100,100,0,0,1,{m(3)},{m(1)},2,{m(55)},{m(55)},{m(160)},1',f'Style: Karaoke,Arial,{caption_size},&H0000FFFF,&H00FFFFFF,&H00141414,&H70000000,-1,0,0,0,100,100,0,0,1,{m(3)},{m(1)},2,{m(55)},{m(55)},{m(160)},1',
             # Hook written on screen during the first seconds (owner priority: the hook keeps viewers).
             f'Style: Hook,Arial,{round(caption_size*1.45)},&H00FFFFFF,&H0000E5FF,&H00101010,&H90000000,-1,0,0,0,100,100,0,0,1,{m(5)},{m(2)},8,{m(60)},{m(60)},{m(250)},1','[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
        def stamp(s): return f'{int(s//3600)}:{int(s//60)%60:02}:{int(s)%60:02}.{int(s%1*100):02}'
        if hook_text and j['config'].get('hook_overlay',True):
            words=hook_text.upper().replace('\\','').replace('{','').replace('}','').split()
            # Last word in yellow, like TikTok hooks.
            text=' '.join(words[:-1])+(' ' if len(words)>1 else '')+'{\\c&H0000E5FF&}'+words[-1] if words else ''
            ass.append('Dialogue: 1,'+stamp(0)+','+stamp(3.2)+',Hook,,0,0,0,,{\\fad(120,300)}'+text)
        start=0.0;mset=montage.of(j['config']);fade=montage.FADES[mset['transition']];lengths=[]
        subtitles=j['config'].get('subtitles',True)
        probe=shutil.which('ffprobe');plan=[]
        for i,s in enumerate(j['scenes']):
            src=safe_child(d,s['clip'])
            # Normalize silent imports too; every clip gets an audio stream.
            audio=True
            if probe:
                pr=subprocess.run([probe,'-v','error','-select_streams','a','-show_entries','stream=index','-of','csv=p=0',str(src)],capture_output=True,text=True,timeout=30); audio=bool(pr.stdout.strip())
            # P5-06: Flow clips stay 8 s; Grok/Arena clips keep their real, bounded duration.
            full=engines.clip_length(j,clip_duration(probe,src) if probe else None,s)
            speech=(j.get('quality_report',{}).get('clips',[])[i].get('speech') if j.get('quality_version')==1 and i<len(j.get('quality_report',{}).get('clips',[])) else None)
            # "Couper les silences": blanks before the first and after the last word, from the real word timings.
            plan.append([src,audio,full,speech,montage.trim(speech,full) if mset['cut_silences'] else (0.0,full)])
        # Durée garantie: trimmed silence is given back until the episode reaches its chosen duration.
        goal=montage.target(j['config'].get('duration'))
        fitted,expected=montage.fit([p[2] for p in plan],[p[4] for p in plan],goal,fade)
        for p,c in zip(plan,fitted):p[4]=c
        for i,s in enumerate(j['scenes']):
            src,audio,_,speech,(cut,length)=plan[i]; out=d/f'normalized_{i:02}.mp4'
            speech=montage.shift(speech,cut)
            args=[ff,'-y',*(['-ss',f'{cut:g}'] if cut else []),'-i',str(src),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-map','0:v:0','-map','0:a:0' if audio else '1:a:0','-vf',f'scale={frame_size(j)[0]}:{frame_size(j)[1]}:force_original_aspect_ratio=increase:flags=lanczos,crop={frame_size(j)[0]}:{frame_size(j)[1]},fps=30,'+(f"zoompan=z='{montage.zoom(i,length,mset['fast_cuts'])}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={frame_size(j)[0]}x{frame_size(j)[1]}:fps=30," if j['config'].get('dynamic',True) else '')+'unsharp=5:5:0.5:5:5:0,setsar=1,tpad=stop_mode=clone:stop_duration='+f'{length:g}','-af','apad','-t',f'{length:g}','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2',str(out)]
            run_command(args)
            # With a fade, the next clip starts while this one ends: captions move with it.
            offset=start;start+=length-(fade if i<len(j['scenes'])-1 else 0);lengths.append(length)
            karaoke=bool(j['config'].get('karaoke'))
            aligned=quality.caption_events(s,speech,offset,caption_words,30,length,karaoke) if speech and subtitles else None
            if aligned:
                aligned_count+=1
                for a,b,text in aligned:
                    if karaoke:
                        # Words are already cleaned by caption_events; the \\kf tags must survive.
                        ass.append(f'Dialogue: 0,{stamp(a)},{stamp(b)},Karaoke,,0,0,0,,{text}');continue
                    text=text.replace('\\','').replace('{','').replace('}','').replace('\n',' ')
                    ass.append(f'Dialogue: 0,{stamp(a)},{stamp(b)},Default,,0,0,0,,{text}')
                continue
            if not subtitles:continue  # "Sous-titres : Sans" keeps only the hook written at the start
            lines=s['dialogue']; count=sum(len(x['text'].split()) for x in lines); cursor=offset+.15
            for line in lines:
                duration=(length-.4)*len(line['text'].split())/max(count,1); words=line['text'].split()
                for k,chunk in captions.chunks(words,caption_words,30 if j.get('retention_version')==1 else None):
                    a=cursor+duration*k/len(words); b=cursor+duration*(k+len(chunk))/len(words)
                    text=' '.join(chunk).replace('\\','').replace('{','').replace('}','').replace('\n',' ')
                    ass.append(f'Dialogue: 0,{stamp(a)},{stamp(b)},Default,,0,0,0,,{text}')
                cursor+=duration
        (d/'subtitles.ass').write_text('\n'.join(ass),'utf-8-sig')
        (d/'concat.txt').write_text('\n'.join(f"file 'normalized_{i:02}.mp4'" for i in range(len(j['scenes']))),'utf-8')
        encode=['-c:v','libx264','-preset','slow','-crf','17','-profile:v','high','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','final.mp4']
        graph=montage.crossfade(lengths,fade)
        if graph:
            # "Fondu léger / long": each clip melts into the next, sound included.
            run_command([ff,'-y',*[x for i in range(len(lengths)) for x in ('-i',f'normalized_{i:02}.mp4')],'-filter_complex',graph,'-map','[v]','-map','[ao]',*encode],cwd=d)
        else:
            run_command([ff,'-y','-f','concat','-safe','0','-i','concat.txt','-vf','ass=subtitles.ass','-af','loudnorm=I=-14:TP=-1.5:LRA=11',*encode],cwd=d)
        # Owner rule (04/11/2026): whatever the clip resolution (Flow 720p, Grok 480p), the video to publish is 1080p.
        check_publish_size(shutil.which('ffprobe'),d/'final.mp4',frame_size(j))
        if j.get('cover_file'):
            if not safe_child(d,j['cover_file']).is_file():raise ValueError('Couverture générée absente')
            cover_file=j['cover_file']
        else:
            cover_path=d/'cover.jpg';cover_file='cover.jpg'
            first=j['scenes'][0].get('image')
            if first: make_cover(safe_child(d,first),cover_path,j['script']['cover_title'],frame_size(j))
            else:
                run_command([ff,'-y','-i',str(d/'final.mp4'),'-frames:v','1',str(d/'cover-frame.jpg')]);make_cover(d/'cover-frame.jpg',cover_path,j['script']['cover_title'],frame_size(j))
        with LOCK:
            actual=job_by(id)
            if actual is None:return
            actual['stage']='done'; actual['status']='done'; actual['rendered_at']=now(); actual['final']=asset_url(actual,'final.mp4'); actual['cover']=asset_url(actual,cover_file); actual['qc']={'export':'Réussi : MP4 '+('horizontal 1920 × 1080' if horizontal(j) else 'vertical 1080 × 1920')+', haute qualité, audio normalisé.','subtitles':f'{aligned_count}/{len(j["scenes"])} scènes calées sur reconnaissance vocale ; autres timings estimés. Contrôle à l’écoute nécessaire.','lips':'Synchronisation labiale non vérifiée automatiquement.','duration':round(sum(lengths)-fade*max(len(lengths)-1,0)),'duration_target':montage.target(j['config'].get('duration')),'montage':montage.summary({**mset,'karaoke':bool(j['config'].get('karaoke'))})+('' if subtitles else ' · sans sous-titres')}; event(actual,'Export terminé. Un contrôle visuel et audio reste nécessaire avant publication.')
            goal=montage.target(actual['config'].get('duration'));got=sum(lengths)-fade*max(len(lengths)-1,0)
            if goal and got<goal-0.05:event(actual,f'Durée finale {got:.1f} s, en dessous des {goal:g} s visés : il manque des plans. Ajoutez une scène ou reprenez avec une durée plus courte.'); check_originality(actual)
            backup_story(actual)
            if actual['config'].get('also_horizontal') and not horizontal(actual) and not any((x.get('variant') or {}).get('of')==actual['id'] and x['variant'].get('kind')=='horizontal' for x in STATE['jobs']):
                # Format "Les deux": the 16:9 version starts by itself once the vertical one is done.
                try:make_variant(actual,'horizontal')
                except Exception as e:log_error('Version horizontale automatique',e)
            save()
            try:
                kit=series.kit(actual);(d/'publication.json').write_text(json.dumps(kit,ensure_ascii=False,indent=2),'utf-8');(d/'publication.txt').write_text(series.kit_text(kit),'utf-8');actual['publication']=asset_url(actual,'publication.txt')
            except Exception as e:log_error('Kit de publication',e)
    except Exception as e:
        with LOCK:
            j=job_by(id)
            if j is not None:
                j['status']='attention'; event(j,'Montage : '+str(e)); save()
    finally: BUSY.discard(id)

def start_render(id):
    if not LICENCE.allowed(): return
    if id not in BUSY: BUSY.add(id); threading.Thread(target=render_job,args=(id,),daemon=True).start()

def make_cover(src,out,title,size=(720,1280)):
    from PIL import Image, ImageOps, ImageDraw, ImageFont
    im=ImageOps.fit(Image.open(src).convert('RGB'),size); draw=ImageDraw.Draw(im,'RGBA'); draw.rectangle((0,0,size[0],320*size[1]//1280),fill=(10,12,20,205))
    preferred=[]
    if re.search('[\u3040-\u30ff]',title): preferred=[r'C:/Windows/Fonts/YuGothB.ttc']
    elif re.search('[\uac00-\ud7af]',title): preferred=[r'C:/Windows/Fonts/malgunbd.ttf']
    elif re.search('[\u3400-\u9fff]',title): preferred=[r'C:/Windows/Fonts/msyhbd.ttc']
    font_path=next((p for p in preferred+[r'C:/Windows/Fonts/arialbd.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if pathlib.Path(p).exists()),None)
    k=min(size)/720
    font=ImageFont.truetype(font_path,round(58*k)) if font_path else ImageFont.load_default()
    words=title.upper().split(); separator=' '
    if len(words)==1 and len(title)>12: words=list(title); separator=''
    lines=[]; line=''
    for word in words:
        trial=(line+separator+word).strip()
        if draw.textbbox((0,0),trial,font=font)[2]>size[0]-80*k and line: lines.append(line); line=word
        else: line=trial
    lines.append(line)
    for i,line in enumerate(lines[:3]): draw.text((size[0]//2,round(55*k)+i*round(76*k)),line,font=font,anchor='mt',fill=(255,219,112,255),stroke_width=round(2*k),stroke_fill=(0,0,0,255))
    im.save(out,quality=94)

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def send_json(self,obj,status=200): self.send_bytes(json.dumps(obj,ensure_ascii=False).encode(),'application/json; charset=utf-8',status)
    def send_bytes(self,b,mime,status=200,download=None):
        self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(b))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('X-Frame-Options','DENY');
        if download: self.send_header('Content-Disposition', 'attachment; filename="'+re.sub(r'[^a-zA-Z0-9_.-]', '_', download)+'"')
        self.end_headers(); self.wfile.write(b)
    def local(self):
        host=self.headers.get('Host','').split(':')[0]
        if host not in ('127.0.0.1','localhost'): raise ValueError('Hôte interdit')
    def auth_bridge(self):
        return hmac.compare_digest(self.headers.get('Authorization',''), 'Bearer '+STATE['token'])
    def origin_ok(self):
        o=self.headers.get('Origin',''); return o in (f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}')
    def do_GET(self):
        try:
            self.local(); path=urllib.parse.urlparse(self.path).path
            if path=='/api/filon/figures':
                # Real figures read from each public video page (views, growth, engagement…).
                return self.send_json(thumbs.all_figures(DATA))
            if path=='/api/thumb':
                # Outside the lock: a network read must never block the studio.
                q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query);url=q.get('url',[''])[0]
                try:image=thumbs.get(url,DATA,kind='avatar' if q.get('kind',[''])[0]=='avatar' else 'cover')
                except ValueError as e:return self.send_json({'error':str(e)},400)
                if not image:return self.send_json({'error':'Miniature indisponible'},404)
                data=image.read_bytes();mime='image/png' if data[:4]==b'\x89PNG' else 'image/webp' if data[:4]==b'RIFF' else 'image/jpeg'
                return self.send_bytes(data,mime)
            with LOCK:
                if path=='/api/bridge/requests':
                    # Owner requests waiting for the browser gateway (open a site, re-check accounts).
                    if not self.auth_bridge():return self.send_json({'error':'Appairage requis'},401)
                    c=STATE['clients'].get(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('client',[''])[0])
                    if not c or c.get('disabled') or c.get('role') not in ('all','flow'):return self.send_json([])
                    pending=STATE.get('bridge_requests',[])
                    def addressed(request):
                        kind=request.get('type')
                        if kind=='show' and request.get('profile'):
                            owner=(profile_by(request['profile']['id']) or {}).get('flow_client')
                            return owner==c['id'] if owner else c['role']=='all'
                        if kind=='scan_flow' and request.get('profile'):
                            return (profile_by(request['profile']) or {}).get('flow_client')==c['id']
                        if kind in ('open','show','add_google','scan_flow'):
                            return c['role']=='all'
                        return True
                    if urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('light',[''])[0]=='1':
                        # A task is running: only the owner's clicks that show a tab are done now; checks wait for idle lanes.
                        quick=[r for r in pending if r.get('type') in ('open','show','add_google') and addressed(r)]
                        STATE['bridge_requests']=[r for r in pending if r not in quick];save();return self.send_json(quick)
                    ready_requests, remaining = [], []
                    for request in pending:
                        if not addressed(request):
                            remaining.append(request)
                            continue
                        if request['type'] != 'readiness':
                            ready_requests.append(request)
                            continue
                        sites = request.get('sites', [])
                        targets = request.get('profiles', [])
                        own_sites = sites if c['role'] == 'all' else []
                        own_targets = []
                        for target in targets:
                            profile = profile_by(target['id'])
                            if profile and profile.get('flow_client') == c['id']:
                                own_targets.append(readiness.profile_target(profile, flow_accounts.account_home))
                            elif not (profile or {}).get('flow_client') and c['role'] == 'all':
                                own_targets.append(target)
                        if own_sites or own_targets:
                            ready_requests.append({**request, 'sites': own_sites, 'profiles': own_targets})
                        claimed_profiles = {target['id'] for target in own_targets}
                        other_targets = [target for target in targets if target['id'] not in claimed_profiles]
                        other_sites = [] if own_sites else sites
                        if other_sites or other_targets:
                            remaining.append({**request, 'sites': other_sites, 'profiles': other_targets})
                    STATE['bridge_requests'] = remaining
                    save()
                    return self.send_json(ready_requests)
                if path=='/api/report':
                    # P4-1: copiable failure report, without token, pairing code or e-mail addresses.
                    if self.headers.get('Sec-Fetch-Site')=='cross-site': return self.send_json({'error':'Accès local requis'},403)
                    return self.send_bytes(maintenance.report(STATE,DATA,VERSION,now()).encode(),'text/plain; charset=utf-8')
                if path=='/api/version':
                    # The extension compares its running version with the copy installed next to the studio and
                    # reloads itself between two tasks (fetching its own manifest returns the loaded one, not the disk).
                    try:ext=json.loads((ROOT/'extension'/'manifest.json').read_text('utf-8')).get('version')
                    except (OSError,ValueError):ext=None
                    return self.send_json({'server':VERSION,'extension':ext})
                if path=='/api/state':
                    # Cross-origin fetches cannot read the pairing code.
                    if self.headers.get('Sec-Fetch-Site')=='cross-site': return self.send_json({'error':'Accès local requis'},403)
                    light=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('view')==['studio']
                    return self.send_json(public_state(light=light))
                if path=='/api/bridge/credit-check':
                    if not self.auth_bridge():return self.send_json({'error':'Appairage requis'},401)
                    client=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('client',[''])[0]
                    if client not in STATE['clients']:raise ValueError('Navigateur inconnu')
                    STATE['clients'][client]['seen']=now()
                    probe=flow_credits.claim(STATE,client,time.time());save();return self.send_json(probe)
                if path=='/api/bridge/task':
                    if not self.auth_bridge(): return self.send_json({'error':'Appairage requis'},401)
                    q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query); client=q.get('client',[''])[0]; c=STATE['clients'].get(client)
                    if not c: return self.send_json({'error':'Client inconnu'},400)
                    # lane=chat|video: the extension runs one task per lane at once; without lane (0.1.88 and older) any task, one at a time.
                    lane=q.get('lane',[''])[0]
                    if lane not in ('','chat','video'):return self.send_json({'error':'Voie inconnue'},400)
                    c['seen']=now();c['version']=q.get('v',[c.get('version')])[0]
                    if c.get('disabled') and c.get('auto') and take_over(c):event_all('Fenêtre FruchtDrama rechargée : elle reprend le travail de l’ancienne, hors ligne.')
                    # A gateway switched off by the owner never receives work (several browsers paired).
                    if c.get('disabled') or not LICENCE.allowed():save();return self.send_json(None)
                    # The working window takes what an old, gone pairing was holding or was meant to do (06/11/2026).
                    rebind_flow_routes();release_dead_chat(c)
                    for j in STATE['jobs']:
                        schedule(j)
                    for t in STATE['tasks']:
                        j=job_by(t['job'])
                        if t['status']!='queued' or not (j['status']=='running' or (j['status']=='waiting_quota' and j.get('quota_lane')=='chat' and lane_of(t)=='video')): continue
                        if not client_accepts(c,t) or (lane and lane_of(t)!=lane): continue
                        if lane_of(t)=='video':
                            # Several video tasks per window (parallel clips), each in its own tab: at most the setting, one Grok/Arena.
                            mine=[o for o in STATE['tasks'] if o['status']=='claimed' and lane_of(o)=='video' and o.get('client')==client]
                            if len(mine)>=(parallel_cap() if lane else 1):continue
                            # One tab per site: one clip at a time per engine (Grok, Arena, Vidogrid each in its tab).
                            if t['kind']=='engine_video' and any(o.get('kind')=='engine_video' and (o.get('payload') or {}).get('engine')==t['payload'].get('engine') for o in STATE['tasks'] if o['status']=='claimed'):continue
                        if t['kind']=='flow_video':
                            if normalize_flow_resolution(j['config']):event(j,'Ancien réglage 1080p corrigé en 720p avant attribution du clip Flow.')
                            if t.get('payload',{}).get('model') in engines.NATIVE_720 and t['payload'].get('resolution')=='1080p':
                                t['payload']['resolution']='720p';t['payload']['resolution_requested']='1080p'
                            # Never two clips on the same account at once: one reservation per account, one tab per project.
                            if any(other['kind'] in ('flow_video','flow_collect') and other['status']=='claimed' and (other.get('profile')==t.get('profile') or not lane) for other in STATE['tasks']):continue
                            p=profile_by(t['profile']); cost=t['payload']['cost']
                            if (not p or p['balance']<cost) and j['stage']=='images':
                                # Clip sent ahead during the boards: no wait now, the boards go on; the clips stage waits for credits.
                                t['status']='cancelled';j['early_clips_off']=True;event(j,'Clip anticipé annulé avant envoi : solde Flow insuffisant. Les planches continuent ; les clips attendront la fin des planches.');continue
                            if not p or p['balance']<cost:
                                # The balance moved since the clip was prepared: next account at once, no 3 s round trip, no click.
                                t['status']='cancelled';j['status']='running';schedule(j);continue
                            if t['payload'].get('dry_run'):
                                # A dry run never sends: nothing to reserve (P1-4).
                                t['status']='claimed'; t['client']=client; t['claimed']=now(); account_usage.touch(STATE,t,time.time()); event(j,'Essai à blanc : préparation de '+t['slot']+' dans Flow, sans envoi.'); save(); return self.send_json(t)
                            p['balance']-=cost;flow_refill.spent(p,time.time());t['reservation']={'profile':p['id'],'amount':cost,'refunded':False}; event(j,f"Réservation prudente de {cost} crédits sur {p['label']}. En cas d’échec, vérifier le solde réel avant de le réajuster.")
                        t['status']='claimed'; t['client']=client; t['claimed']=now(); account_usage.touch(STATE,t,time.time()); event(j,('Essai à blanc : préparation de '+t['slot']+' dans '+engines.ENGINES[t['payload']['engine']]['label']+', sans envoi.') if t['kind']=='engine_video' and t['payload'].get('dry_run') else account_usage.claim_line(STATE,t)); save(); return self.send_json(t)
                    save(); return self.send_json(None)
                if path=='/api/bridge/status':
                    if not self.auth_bridge():return self.send_json({'error':'Appairage requis'},401)
                    q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query);client=q.get('client',[''])[0];task=q.get('task',[''])[0]
                    t=next((t for t in STATE['tasks'] if t['id']==task and t.get('client')==client),None)
                    if not t:raise ValueError('Tâche non associée à ce navigateur')
                    STATE['clients'][client]['seen']=now();j=job_by(t['job']);return self.send_json({'task_status':t['status'],'job_stage':j['stage'],'job_status':j['status']})
                if path=='/api/bridge/recoverable-media':
                    if not self.auth_bridge():return self.send_json({'error':'Appairage requis'},401)
                    q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query);client=q.get('client',[''])[0];c=STATE['clients'].get(client)
                    if not c:raise ValueError('Navigateur inconnu')
                    rows=[];seen=set()
                    for t in reversed(STATE['tasks']):
                        if t.get('client')!=client or t['status']!='failed' or t['kind']!='chat_image':continue
                        j=job_by(t['job']);key=(j['id'],t['slot'])
                        if key in seen or j['status']!='attention' or j['stage'] not in ('characters','images','cover') or not client_accepts(c,t):continue
                        if lane_busy(j,'chat'):continue
                        if t['slot']=='characters':missing=not any(x.get('file') for x in j['characters'])
                        elif t['slot'].startswith('character:'):
                            item=next((x for x in j['characters'] if x['id']==t['slot'].split(':')[1]),None);missing=item and not item.get('file')
                        elif t['slot']=='cover':missing=not j.get('cover_file')
                        elif t['slot'].startswith('state:'):
                            k=int(t['slot'].split(':')[1]);missing=k<len(state_changes(j)) and not state_entry(j,state_changes(j)[k])
                        else:missing=t['slot'].startswith('image:') and not j['scenes'][int(t['slot'].split(':')[1])].get('image')
                        if missing:rows.append(t);seen.add(key)
                    return self.send_json(rows[:3])
                if path=='/api/bridge/recoverable-videos':
                    if not self.auth_bridge():return self.send_json({'error':'Appairage requis'},401)
                    q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query);client=q.get('client',[''])[0];c=STATE['clients'].get(client)
                    if not c:raise ValueError('Navigateur inconnu')
                    rows=[];seen=set()
                    for t in reversed(STATE['tasks']):
                        if t.get('client')!=client or t['status']!='failed' or t['kind']!='flow_video':continue
                        j=job_by(t['job']);key=(j['id'],t['slot'])
                        # A clip sent ahead during the boards is recovered the same way.
                        if key in seen or j['status']!='attention' or j['stage'] not in ('images','clips') or not client_accepts(c,t):continue
                        if lane_busy(j,'video'):continue
                        if not j['scenes'][int(t['slot'].split(':')[1])].get('clip'):rows.append(t);seen.add(key)
                    return self.send_json(rows[:3])
            m=re.fullmatch(r'/api/job/([a-f0-9]{16})/images\.zip',path)
            if m:
                # "Télécharger les images": character sheet, boards and cover in one archive.
                with LOCK:
                    j=job_by(m.group(1))
                    if not j:return self.send_json({'error':'Projet inconnu'},404)
                    files=[f for f in [j.get('character_sheet_file')]+[c.get('file') for c in j['characters']]+[x.get('file') for x in j.get('state_sheets') or []]+[x.get('image') for x in j['scenes']]+[j.get('cover_file')] if f]
                import io
                buf=io.BytesIO()
                with zipfile.ZipFile(buf,'w',zipfile.ZIP_STORED) as z:
                    for i,f in enumerate(dict.fromkeys(files)):
                        src=safe_child(job_dir(j),f)
                        if src.is_file():z.write(src,f'{i+1:02d}-{f}')
                return self.send_bytes(buf.getvalue(),'application/zip',download=re.sub(r'[^\w-]+','-',j['title'])[:40]+'-images.zip')
            if path.startswith('/media/'):
                parts=path.split('/')
                if len(parts)!=4 or not re.fullmatch('[a-f0-9]{16}',parts[2]): raise ValueError('Média invalide')
                file=safe_child(DATA/'jobs'/parts[2],urllib.parse.unquote(parts[3]))
            else:
                file=ROOT/'web'/'index.html' if path=='/' else safe_child(ROOT/'web',path.lstrip('/'))
            if not file.is_file(): return self.send_json({'error':'Introuvable'},404)
            mime=mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
            if mime.startswith('text/'): mime+='; charset=utf-8'
            download=path.startswith('/media/') and urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('download')==['1']
            self.send_bytes(file.read_bytes(),mime,download=file.name if download else None)
        except Exception as e: self.send_json({'error':str(e)},400)
    def do_POST(self):
        try:
            self.local(); path=urllib.parse.urlparse(self.path).path
            bridge=path.startswith('/api/bridge/') and path not in ('/api/bridge/pair','/api/bridge/auto-pair')
            if bridge and not self.auth_bridge(): return self.send_json({'error':'Appairage requis'},401)
            if not bridge and path not in ('/api/bridge/pair','/api/bridge/auto-pair') and not self.origin_ok(): return self.send_json({'error':'Origine interdite'},403)
            length=int(self.headers.get('Content-Length',0))
            if length>100*1024*1024: raise ValueError('Fichier limité à 100 Mo')
            raw=self.rfile.read(length)
            if path in ('/api/upload','/api/bridge/upload'):
                q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query); id=q['job'][0]; slot=q['slot'][0]
                with LOCK:
                    j=job_by(id)
                    if not j: raise ValueError('Projet inconnu')
                    ext=q.get('ext',[''])[0].lower()
                    if ext not in ('png','jpg','jpeg','webp','mp4','webm'): raise ValueError('Type média non accepté')
                    if not re.fullmatch(r'(?:cover|characters|character:[a-z][a-z0-9_]{0,24}|state:\d+|image:\d+|clip:\d+)',slot): raise ValueError('Emplacement média invalide')
                    if slot.startswith('character:') and not any(c['id']==slot.split(':')[1] for c in j['characters']): raise ValueError('Personnage inconnu')
                    if slot.startswith('state:') and int(slot.split(':')[1])>=len(state_changes(j)): raise ValueError('Feuille d’état inconnue')
                    if slot not in ('cover','characters') and not slot.startswith(('character:','state:')) and int(slot.split(':')[1])>=len(j['scenes']): raise ValueError('Scène inconnue')
                    if slot.startswith('clip:') and ext not in ('mp4','webm'): raise ValueError('Un clip doit être une vidéo MP4 ou WebM')
                    if not slot.startswith('clip:') and ext not in ('png','jpg','jpeg','webp'): raise ValueError('Une image est attendue')
                    name=re.sub('[^a-zA-Z0-9_-]','_',slot)+'_'+uid()+'.'+ext; (job_dir(j)/name).write_bytes(raw)
                    if path=='/api/upload':
                        t=next((t for t in STATE['tasks'] if t['job']==id and t['slot']==slot and t['status'] in ('queued','claimed')),None)
                        for other in STATE['tasks']:
                            # A generation running for another scene keeps its owner: its result stays acceptable.
                            if other['job']==id and (other['status']=='queued' or other['status']=='claimed' and other['slot']==slot): other['status']='cancelled'
                        if not t: t={'job':id,'slot':slot}
                        j['status']='running'; accept_task_result(t,{'ok':True,'file':name}); save()
                    return self.send_json({'file':name})
            b=json.loads(raw or b'{}')
            if path=='/api/licence':
                # Outside the studio lock: the key server may take a few seconds to answer.
                if b.get('action')=='check': LICENCE.refresh()
                else: LICENCE.activate(str(b.get('key','')))
                return self.send_json({'licence':LICENCE.view()})
            with LOCK:
                if path=='/api/bridge/auto-pair':
                    # Atelier-like hidden key: the local extension pairs itself once; the code is never shown or typed.
                    origin=self.headers.get('Origin','')
                    if not origin.startswith('chrome-extension://'):return self.send_json({'error':'Réservé à l’extension FruchtDrama'},403)
                    # The first extension that pairs is remembered; another one needs the owner's approval in Mes comptes.
                    # The official extension (fixed key, same ID on every computer) replaces an older unpacked copy (0.1.69).
                    if STATE.get('extension_origin') and STATE['extension_origin']!=origin and origin!=OFFICIAL_ORIGIN:return self.send_json({'error':'Une autre extension est déjà liée. Autorisez la nouvelle dans Mes comptes › Clé du studio.'},403)
                    STATE['extension_origin']=origin
                    # Still one working browser at a time, but the one pairing now takes over: it is the extension
                    # reinstalled or reloaded (key lost) or the official copy replacing an older one. Never while
                    # another browser is running a task.
                    if not any(t['status']=='claimed' and STATE['clients'].get(t.get('client'),{}).get('auto') for t in STATE['tasks']):
                        for c in STATE['clients'].values():
                            if c.get('auto'):c['disabled']=True
                    others=[c for c in STATE['clients'].values() if not c.get('disabled') and c.get('role') in ('all','flow') and time.time()-flow_credits.seconds(c.get('seen'))<75]
                    client=b.get('client') if b.get('client') in STATE['clients'] else uid()
                    STATE['clients'][client]={'id':client,'label':str(b.get('label','Fenêtre FruchtDrama'))[:60],'flow_profile':None,'role':'all','ai_provider':'both','seen':now(),'disabled':bool(others),'auto':True}
                    flow_accounts.follow_active_browser(STATE)
                    save();return self.send_json({'client':client,'token':STATE['token'],'enabled':not others})
                if path=='/api/bridge/pair':
                    if not hmac.compare_digest(str(b.get('code','')),STATE['pair_code']): return self.send_json({'error':'Code incorrect'},403)
                    role=b.get('role','all');provider=b.get('ai_provider','both')
                    if role not in ('all','creation','flow') or provider not in ('chatgpt','claude','both','none'):raise ValueError('Rôle ou fournisseur invalide')
                    client=b.get('client') if b.get('client') in STATE['clients'] else uid()
                    STATE['clients'][client]={'id':client,'label':str(b.get('label','Navigateur'))[:60],'flow_profile':b.get('flow_profile') if role in ('all','flow') else None,'role':role,'ai_provider':provider if role!='flow' else 'none','seen':now()}; save(); return self.send_json({'client':client,'token':STATE['token']})
                if path=='/api/bridge/register-flow':
                    if not self.auth_bridge():return self.send_json({'error':'Appairage requis'},401)
                    c=STATE['clients'].get(b.get('client'))
                    if not c or c.get('role') not in ('all','flow'):raise ValueError('Utilisez une passerelle autorisée pour Flow')
                    url=flow_accounts.project_url(b.get('url',''));email=str(b.get('email','')).strip().lower()
                    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):raise ValueError('Identité du compte Google non détectée')
                    p=next((p for p in STATE['profiles'] if p.get('flow_email',p.get('label','')).lower()==email),None)
                    if not p:raise ValueError('Ajoutez ce compte dans Connexions et renseignez son solde vérifié avant de le mémoriser')
                    if any(t['status']=='claimed' and t.get('profile')==p['id'] for t in STATE['tasks']):raise ValueError('Attendez la fin du clip en cours avant de modifier ce compte')
                    if p.get('flow_client') != c['id']:
                        p.pop('readiness', None)
                        p.pop('credit_probe', None)
                        if p.get('blocked') == 'unavailable':
                            p.pop('blocked', None)
                    p.pop('flow_url_home', None)
                    p.update(flow_url=url,flow_email=email,flow_client=c['id'],auto_enabled=True)
                    STATE['settings']['flow_auto']=True;save();return self.send_json({'ok':True,'profile':p['id']})
                if path=='/api/bridge/flow-slot':
                    # The Google account numbers moved (/u/N): the same account is found at another number by its address.
                    t=next((t for t in STATE['tasks'] if t['id']==b.get('task') and t.get('client')==b.get('client') and t['status']=='claimed' and t['kind']=='flow_video'),None)
                    if not t:raise ValueError('Tâche Flow non associée à cette passerelle')
                    slot=b.get('slot')
                    if isinstance(slot,bool) or not isinstance(slot,int) or not 0<=slot<=20:raise ValueError('Numéro de compte invalide')
                    move=lambda u:flow_accounts.at_slot(u,slot) if isinstance(u,str) else u
                    p=profile_by(t.get('profile'));j=job_by(t['job'])
                    if p:p['flow_url']=move(p.get('flow_url'));p['slot']=slot
                    for x in STATE['tasks']:
                        if x.get('profile')==t.get('profile') and x['status'] in ('queued','claimed') and (x.get('payload') or {}).get('flow_route'):x['payload']['flow_route']['url']=move(x['payload']['flow_route']['url'])
                    for jj in STATE['jobs']:
                        if t.get('profile') in (jj.get('flow_projects') or {}):jj['flow_projects'][t['profile']]=move(jj['flow_projects'][t['profile']])
                    event(j,'Compte Flow retrouvé au numéro '+str(slot)+' de ce Chrome (Google a renuméroté les comptes connectés).');save();return self.send_json({'ok':True})
                if path=='/api/bridge/flow-project':
                    t=next((t for t in STATE['tasks'] if t['id']==b.get('task') and t.get('client')==b.get('client') and t['status']=='claimed' and t['kind']=='flow_video'),None)
                    if not t:raise ValueError('Tâche Flow non associée à cette passerelle')
                    target=t['payload'].get('flow_route');url=flow_accounts.project_url(b.get('url',''))
                    if not target or flow_accounts.account_home(target['url'])!=flow_accounts.account_home(url):raise ValueError('Nouveau projet créé sous une autre session Flow')
                    if not target.get('new_project') and target['url']!=url:raise ValueError('Un projet est déjà associé à cette scène')
                    j=job_by(t['job']);j.setdefault('flow_projects',{})[t['profile']]=url
                    target['url']=url;target.pop('new_project',None);event(j,'Nouveau projet Flow créé et associé à cette production.');save();return self.send_json({'ok':True})
                if path=='/api/bridge/progress':
                    t=next((t for t in STATE['tasks'] if t['id']==b.get('task') and t.get('client')==b.get('client') and t['status']=='claimed'),None)
                    if not t:raise ValueError('Tâche non associée à ce navigateur')
                    j=job_by(t['job']);message=readable_progress(str(b.get('message','')),t.get('slot'))[:240]
                    if j['status']!='paused' and message and message!=t.get('progress'):
                        t['progress']=message;t['progress_at']=now();event(j,message);save()
                    return self.send_json({'ok':True})
                if path=='/api/bridge/retry-research':
                    client=b.get('client');c=STATE['clients'].get(client)
                    if not c or c.get('role') not in ('all','creation'):raise ValueError('Passerelle de recherche requise')
                    resumed=[]
                    for j in STATE['jobs']:
                        if j['stage']!='research' or j['status']!='attention' or j.get('research_reader_retries',0)>=3:continue
                        old=next((t for t in reversed(STATE['tasks']) if t['job']==j['id']),None)
                        if not old or old['kind']!='tiktok_search' or old['status']!='failed' or old.get('client')!=client:continue
                        if not j['events'] or not j['events'][-1]['text'].startswith('Suivi interrompu'):continue
                        j['research_reader_retries']=j.get('research_reader_retries',0)+1;j['status']='running'
                        event(j,'Reprise automatique de la recherche après actualisation du lecteur ; aucune génération de média.');schedule(j);resumed.append(j['id'])
                    save();return self.send_json({'resumed':resumed})
                if path=='/api/bridge/credit-report':
                    p=flow_credits.report(STATE,b.get('client'),b,time.time());save()
                    return self.send_json({'ok':True,'balance':p['balance'],'checked':p.get('checked'),'next_check':p.get('credit_next_check')})
                if path=='/api/bridge/import-download':
                    t=next((t for t in STATE['tasks'] if t['id']==b.get('task') and t.get('client')==b.get('client') and t['status']=='claimed' and t['kind'] in ('flow_video','flow_collect')),None)
                    if not t:raise ValueError('Téléchargement non associé à une tâche Flow active de ce navigateur')
                    j=job_by(t['job']);name=import_browser_download(j,t,b);save();return self.send_json({'file':name})
                if path=='/api/bridge/recover':
                    client=b.get('client');j=job_by(b.get('job'))
                    if client not in STATE['clients'] or not j or j['stage']!='script': raise ValueError('Choisissez une production à l’étape Scénario')
                    if not client_accepts(STATE['clients'][client],{'kind':'chat_collect','payload':{'provider':j['config']['provider']}}):raise ValueError('Ce navigateur est réservé à Flow ou à une autre IA. Utilisez le profil IA de cette production.')
                    if b.get('automatic'):
                        previous=next((t for t in STATE['tasks'] if t['id']==b.get('previous_task') and t['job']==j['id'] and t.get('client')==client and t['slot']=='script'),None)
                        if not previous:raise ValueError('Association de récupération automatique absente')
                        if j['status']=='paused':raise ValueError('Production en pause : récupération automatique suspendue')
                    for old in STATE['tasks']:
                        if old['job']==j['id'] and old['status'] in ('queued','claimed'):old['status']='cancelled'
                    t={'id':uid(),'job':j['id'],'kind':'chat_collect','slot':'script','status':'claimed','client':client,'created':now(),'claimed':now(),'payload':{'provider':j['config']['provider'],'scene_count':j['config']['scene_count'],'expected_job':j['id']}}
                    STATE['tasks'].append(t);j['status']='running';event(j,'Récupération de la réponse existante dans l’onglet choisi ; aucun nouveau prompt.');save();return self.send_json(t)
                if path=='/api/bridge/recover-video':
                    client=b.get('client');old=next((t for t in STATE['tasks'] if t['id']==b.get('previous_task') and t.get('client')==client and t['kind']=='flow_video' and t['status']=='failed'),None)
                    if not old or client not in STATE['clients'] or not client_accepts(STATE['clients'][client],old):raise ValueError('Clip non associé à ce navigateur Flow')
                    j=job_by(old['job'])
                    if j['status']!='attention' or j['stage'] not in ('images','clips') or j['scenes'][int(old['slot'].split(':')[1])].get('clip') or lane_busy(j,'video'):raise ValueError('Production déjà reprise ou en pause')
                    t={'id':uid(),'job':j['id'],'kind':'flow_collect','profile':old['profile'],'slot':old['slot'],'status':'claimed','client':client,'created':now(),'claimed':now(),'payload':old['payload']}
                    STATE['tasks'].append(t);j['status']='running';event(j,'Récupération du clip Flow existant après correspondance exacte du prompt ; aucune génération ni réservation supplémentaire.');save();return self.send_json(t)
                if path=='/api/bridge/recover-media':
                    client=b.get('client');old=next((t for t in STATE['tasks'] if t['id']==b.get('previous_task') and t.get('client')==client and t['kind']=='chat_image' and t['status']=='failed'),None)
                    if not old or client not in STATE['clients'] or not client_accepts(STATE['clients'][client],old):raise ValueError('Image non associée à ce navigateur IA')
                    j=job_by(old['job'])
                    if j['status']!='attention' or j['stage'] not in ('characters','images','cover') or lane_busy(j,'chat'):raise ValueError('Production déjà reprise ou en pause')
                    t={'id':uid(),'job':j['id'],'kind':'chat_image_collect','slot':old['slot'],'status':'claimed','client':client,'created':now(),'claimed':now(),'payload':old['payload']}
                    STATE['tasks'].append(t);j['status']='running';event(j,'Récupération automatique de l’image existante après correspondance exacte du prompt ; aucune nouvelle génération.');save();return self.send_json(t)
                if path=='/api/bridge/result':
                    t=next((t for t in STATE['tasks'] if t['id']==b.get('task')),None)
                    if t and t['status']=='done' and t.get('client')==b.get('client'):
                        digest=hashlib.sha256(json.dumps(b.get('result',{}),ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                        if t.get('result_digest')==digest:return self.send_json({'ok':True,'already_received':True})
                    if not t or t['status']!='claimed' or t.get('client')!=b.get('client'): raise ValueError('Tâche expirée ou remplacée')
                    try:
                        accept_task_result(t,b.get('result',{}))
                        if t['status']=='done':t['result_digest']=hashlib.sha256(json.dumps(b.get('result',{}),ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                    except Exception as e:
                        t['status']='failed'; j=job_by(t['job']); j['status']='attention'; event(j,'Réponse invalide : '+str(e))
                        j['last_error']={'kind':'other','slot':t.get('slot'),'task':t.get('id'),'at':now()}
                    save();j=job_by(t['job']);return self.send_json({'ok':True,'task_status':t['status'],'job_status':j['status'],'error':j['events'][-1]['text'] if t['status']=='failed' else None})
                elif path=='/api/profile/check':
                    p=flow_credits.request(STATE,b.get('id'),time.time())
                elif path=='/api/profile/delete':
                    delete_profile(b.get('id'))
                elif path=='/api/profile':
                    p=profile_by(b.get('id'))
                    balance=int(b.get('balance',0))
                    if not 0<=balance<=100000: raise ValueError('Solde invalide')
                    if p:
                        p.update(label=str(b.get('label',p['label']))[:60],balance=balance,checked=now())
                        p.pop('credit_probe',None);p.pop('credit_next_check',None);p['credit_source']='manual'
                        if p.get('blocked')=='credits':p.pop('blocked',None)
                        if 'auto_enabled' in b:p['auto_enabled']=bool(b['auto_enabled'])
                        if 'chrome_profile' in b:p['chrome_profile']=flow_accounts.chrome_profile(b['chrome_profile'])
                    else: STATE['profiles'].append({'id':uid(),'label':str(b.get('label','Flow'))[:60],'balance':balance,'checked':now()})
                elif path=='/api/account':
                    if b.get('delete_all'):
                        # Never delete without a backup: copy the state before removing every account.
                        backup=DATA/'sauvegardes'/('comptes-avant-tout-retirer-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json');backup.parent.mkdir(exist_ok=True)
                        backup.write_text(json.dumps(STATE,ensure_ascii=False,indent=2),'utf-8')
                        removed,kept=identities.delete_all(STATE,delete_profile);save()
                        return self.send_json({**public_state(),'removed':removed,'kept':kept,'backup':backup.name})
                    elif b.get('remove_all_service'):
                        # « Tout supprimer » of one service in Mes comptes: a backup first; accounts busy with a clip are kept.
                        service=b['remove_all_service']
                        if service not in identities.SERVICES:raise ValueError('Service inconnu')
                        backup=DATA/'sauvegardes'/('comptes-'+service+'-avant-suppression-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json');backup.parent.mkdir(exist_ok=True)
                        backup.write_text(json.dumps(STATE,ensure_ascii=False,indent=2),'utf-8')
                        removed,kept=remove_service_accounts(service);save()
                        return self.send_json({**public_state(),'removed':removed,'kept':kept,'backup':backup.name})
                    elif b.get('delete'):identities.delete(STATE,b.get('email'),delete_profile)
                    elif b.get('remove_service'):identities.remove_service(STATE,b.get('email'),b.get('remove_service'),delete_profile)
                    else:identities.add(STATE,b.get('email'),b.get('services'),b.get('label',''),b.get('balance',0),uid)
                elif path=='/api/key/reset':
                    # Owner allows a reinstalled extension (new identifier) to pair itself again.
                    STATE.pop('extension_origin',None)
                elif path=='/api/engine-account':
                    if b.get('delete'):
                        a=engine_accounts.by_id(STATE,b.get('id'))
                        if not a:raise ValueError('Compte inconnu')
                        if engine_accounts.busy(STATE,a):raise ValueError('Ce compte génère un clip : attendez la fin')
                        STATE['engine_accounts'].remove(a)
                    elif b.get('forget_wall'):
                        a=engine_accounts.by_id(STATE,b.get('id'))
                        if not a:raise ValueError('Compte inconnu')
                        engine_accounts.forget(a)
                        for j in STATE['jobs']:
                            if j.get('status')=='waiting_quota' and engines.of(j)==a['engine']:j['wait_until']=0
                    else:
                        engine=engines.validate(b.get('engine'))
                        if engine=='flow':raise ValueError('Les comptes Flow se gèrent avec leurs crédits ci-dessus')
                        engine_accounts.add(STATE,engine,b.get('label'),b.get('email'))
                elif path=='/api/quota/forget':
                    name=str(b.get('service',''))
                    if name not in quotas.SERVICES:raise ValueError('Service inconnu')
                    quotas.forget(STATE,name)
                    for j in STATE['jobs']:
                        # Re-checked on wake: a production still blocked elsewhere simply waits again.
                        if j.get('status')=='waiting_quota':j['wait_until']=0
                elif path=='/api/night':
                    action=b.get('action');n=night()
                    if action in ('add','remove'):
                        j=job_by(b.get('job'))
                        if not j:raise ValueError('Projet inconnu')
                        night_add(j) if action=='add' else night_remove(j)
                    elif action=='start':
                        if not n['ids']:raise ValueError('Ajoutez d’abord des productions à la file de nuit')
                        n['active']=True;night_log('File de nuit démarrée ('+str(len(n['ids']))+' production(s)).')
                    elif action=='stop':
                        n['active']=False;night_log('File de nuit arrêtée : la production en cours continue, les suivantes attendent.')
                    else:raise ValueError('Action inconnue')
                elif path=='/api/maintenance/purge':
                    maintenance.backup_state(DATA,STATE);result=maintenance.purge(STATE,time.time());save()
                    return self.send_json({**public_state(),'purge':result})
                elif path=='/api/filon':
                    if 'auto' in b:STATE['settings']['filon_auto']=bool(b['auto'])
                    if 'niches' in b:
                        names=list(dict.fromkeys(niche_name(x) for x in b['niches']))
                        if not 1<=len(names)<=8:raise ValueError('Entre une et huit niches')
                        STATE['settings']['filon_niches']=names
                        if STATE['settings'].get('filon_niche') not in names:STATE['settings']['filon_niche']=names[0]
                    if 'niche' in b:STATE['settings']['filon_niche']=niche_name(b['niche'])
                    if b.get('refresh'):filon_refresh(b.get('language'),b.get('niche'))
                elif path=='/api/client':
                    c=STATE['clients'].get(b.get('id'))
                    if not c:raise ValueError('Passerelle inconnue')
                    if any(t['status']=='claimed' and t.get('client')==b.get('id') for t in STATE['tasks']) and b.get('disabled'):raise ValueError('Cette passerelle exécute une tâche : attendez sa fin')
                    if b.get('forget'):
                        # Only an offline browser can be forgotten; it would have to pair again.
                        if time.time()-flow_credits.seconds(c.get('seen'))<75:raise ValueError('Ce navigateur est en ligne : désactivez-le plutôt')
                        if any(t['status']=='claimed' and t.get('client')==c['id'] for t in STATE['tasks']):raise ValueError('Cette passerelle exécute une tâche : attendez sa fin')
                        del STATE['clients'][c['id']]
                    else:c['disabled']=bool(b.get('disabled'))
                elif path=='/api/sites':
                    action=b.get('action')
                    if action=='open' and b.get('site') not in SITES:raise ValueError('Site inconnu')
                    if action in ('prepare','fix','recheck'):
                        # « Préparer mes comptes », « Régler maintenant » (shows the tab: the owner clicked), « C'est fait ».
                        target=str(b.get('target') or '')
                        if action=='prepare':
                            full=readiness.full_targets(STATE);request_readiness(full['sites'],full['profiles'])
                        else:
                            kind,_,name=target.partition(':')
                            if kind=='site' and name in readiness.SITE_LABELS and name!='flow':sites,profiles=[name],[]
                            elif kind=='flow' and profile_by(name) and profile_by(name).get('flow_url'):sites,profiles=[],[name]
                            else:raise ValueError('Compte inconnu')
                            if action=='recheck':request_readiness(sites,profiles)
                            else:
                                item={'type':'show','site':name} if kind=='site' else {'type':'show','profile':readiness.profile_target(profile_by(name),flow_accounts.account_home)}
                                STATE.setdefault('bridge_requests',[]).append(item)
                        save();return self.send_json(public_state())
                    if action not in ('open','check','register_flow','tidy','recover','scan_flow','add_google'):raise ValueError('Action inconnue')
                    if action=='recover' and not job_by(b.get('job')):raise ValueError('Production inconnue')
                    queue=STATE.setdefault('bridge_requests',[])
                    item={'type':action,'site':b.get('site')} if action=='open' else {'type':action,'job':b.get('job')} if action=='recover' else {'type':action}
                    if action=='scan_flow' and b.get('check'):item['then_check']=True  # Mes comptes › Google Flow › Vérifier
                    if action=='scan_flow' and b.get('check_all') is True:item.update(then_check=True,check_all=True)
                    if action=='scan_flow' and b.get('profile'):
                        profile=profile_by(b['profile'])
                        if not profile or not client_online(STATE['clients'].get(profile.get('flow_client'))):
                            raise ValueError('Ouvre d’abord le profil Chrome de ce compte Flow.')
                        item['profile']=profile['id']
                    if item not in queue:queue.append(item)
                    if action in ('open','register_flow','tidy','recover','scan_flow','add_google'):STATE['bridge_notice']={'at':now(),'action':action,'pending':True,'text':'Demande en attente du connecteur FruchtDrama…'}
                    if action=='check':STATE.setdefault('sites',{})['_requested']=now()
                elif path=='/api/bridge/flow-scan':
                    c=STATE['clients'].get(b.get('client'))
                    if not c:raise ValueError('Passerelle inconnue')
                    only_profile=profile_by(b.get('profile') or c.get('flow_profile'))
                    if (b.get('profile') or c.get('role')=='flow') and (not only_profile or only_profile.get('flow_client')!=c['id']):
                        raise ValueError('Ce compte Flow est associé à un autre profil Chrome.')
                    STATE['bridge_notice']={'at':now(),'action':'scan_flow','ok':True,'text':''}
                    message=flow_scan(STATE,c,b.get('accounts') or [],only_profile)
                    detected=not message.startswith('Aucun compte')
                    STATE['bridge_notice'].update(text=message,ok=detected)
                    save();return self.send_json({'ok':True,'detected':detected,'message':message})
                elif path=='/api/bridge/notice':
                    if b.get('client') not in STATE['clients']:raise ValueError('Passerelle inconnue')
                    STATE['bridge_notice']={'at':now(),'action':str(b.get('action',''))[:20],'ok':bool(b.get('ok')),'text':str(b.get('text',''))[:300]}
                    save();return self.send_json({'ok':True})
                elif path=='/api/bridge/readiness':
                    c=STATE['clients'].get(b.get('client'))
                    if not c:raise ValueError('Passerelle inconnue')
                    c['seen']=now()
                    b['profiles'] = {pid: result for pid, result in (b.get('profiles') or {}).items()
                                     if (profile_by(pid) or {}).get('flow_client') in (None, c['id'])}
                    if c.get('role') == 'flow':
                        b['sites'] = {}
                    busy={t.get('profile') for t in STATE['tasks'] if t['status']=='claimed' and t.get('kind') in ('flow_video','flow_collect')}
                    readiness.apply_report(STATE,b,now(),time.time(),busy,int(STATE.get('settings',{}).get('flow_daily',flow_refill.DAILY)))
                    # A service found signed in with a readable address joins Mes comptes by itself (address only, no password).
                    for name in (b.get('sites') or {}):
                        entry=(STATE.get('readiness') or {}).get('sites',{}).get(name) or {}
                        if name in ('chatgpt','claude','grok','arena','vidogrid') and entry.get('state')=='ready' and entry.get('email'):
                            try:identities.add(STATE,entry['email'],[name],new_id=uid)
                            except ValueError:pass
                    completed = {'site:' + name for name in b.get('sites', {})}
                    completed.update('flow:' + pid for pid in b['profiles'])
                    for j in STATE['jobs']:
                        check = j.get('accounts_check')
                        if not check or (b.get('id') and check['id'] != b['id']):
                            continue
                        check['pending'] = [key for key in check.get('pending', []) if key not in completed]
                        if not check['pending']:
                            end_check(j)
                    rows=[v for v in list((b.get('sites') or {}).values())+list((b.get('profiles') or {}).values()) if isinstance(v,dict)]
                    ready=sum(1 for v in rows if v.get('state')=='ready')
                    STATE['bridge_notice']={'at':now(),'action':'readiness','ok':ready==len(rows),'text':f'Comptes vérifiés : {ready} prêt(s) sur {len(rows)}.'}
                    save();return self.send_json({'ok':True})
                elif path=='/api/bridge/readiness-request':
                    # The FruchtDrama window was just opened: every account is checked in the background.
                    if b.get('client') not in STATE['clients']:raise ValueError('Passerelle inconnue')
                    full=readiness.full_targets(STATE)
                    sites=[] if b.get('flow_only') is True else full['sites']
                    profiles=full['profiles']
                    if b.get('profile'):
                        profile=profile_by(b['profile'])
                        if not profile or profile.get('flow_client')!=b['client']:raise ValueError('Compte Flow associé à un autre profil Chrome.')
                        sites,profiles=[],[profile['id']]
                    request_readiness(sites,profiles,background=b.get('background',True) is not False)
                    save();return self.send_json({'ok':True})
                elif path=='/api/bridge/sites':
                    c=STATE['clients'].get(b.get('client'))
                    if not c:raise ValueError('Passerelle inconnue')
                    sites={k:{'connected':bool(v.get('connected')),'email':str(v.get('email') or '')[:120] or None,'challenge':bool(v.get('challenge')),'checked':now()} for k,v in (b.get('sites') or {}).items() if k in SITES}
                    # partial: one site re-read after « Se connecter » ; the others keep their last state.
                    if b.get('partial'):
                        STATE.setdefault('sites',{}).update(sites)
                        if c.get('role','all')=='all':
                            for name, session in sites.items():
                                if name in identities.SERVICES and name!='flow' and session['connected'] and not session['challenge']:
                                    entry=readiness.clean_entry({'state':'ready','email':session['email']},session['checked'])
                                    readiness.store(STATE)['sites'][name]=entry
                                    if entry.get('email'):identities.add(STATE,entry['email'],[name],new_id=uid)
                    else:STATE['sites']=sites
                    save();return self.send_json({'ok':True})
                elif path=='/api/settings':
                    if 'language' in b:STATE['settings']['language']=creation_language(b['language'])
                    for k in CLAUDE_DEFAULTS:
                        if k in b:STATE['settings'][k]=claude_choice(k,b[k])
                    if 'controls' in b:
                        if b['controls'] not in ('redo','report','none'):raise ValueError('Réglage de contrôle inconnu')
                        STATE['settings']['controls']=b['controls']
                    if 'board_controls' in b:
                        if b['board_controls'] not in ('redo','report','none'):raise ValueError('Réglage des planches inconnu')
                        STATE['settings']['board_controls']=b['board_controls']
                    if 'clip_look' in b:
                        if b['clip_look'] not in ('look','ear'):raise ValueError('Réglage du regard sur les clips inconnu')
                        STATE['settings']['clip_look']=b['clip_look']
                    if 'cover_controls' in b:
                        if b['cover_controls'] not in ('fix','report','none'):raise ValueError('Réglage de la miniature inconnu')
                        STATE['settings']['cover_controls']=b['cover_controls']
                    if 'engine_chain' in b:
                        # 0.1.93: order of the clip engines (one try each per clip); an engine left out is never used.
                        STATE['settings']['engine_chain']=engine_chain.validate(b['engine_chain'])
                    if 'clip_routing' in b:
                        if b['clip_routing'] not in (engine_chain.V09,'flow_grok_per_clip','chain'):raise ValueError('Mode de bascule inconnu')
                        target=job_by(b.get('job')) if b.get('job') else None
                        if b.get('job') and not target:raise ValueError('Production inconnue')
                        if target and any(t['job']==target['id'] and t['status'] in ('queued','claimed') for t in STATE['tasks']):raise ValueError('Attendez la fin de la tâche avant de changer de bascule')
                        STATE['settings']['clip_routing']=b['clip_routing']
                        if b['clip_routing']=='flow_grok_per_clip':STATE['settings']['engine_chain']=['flow','grok']
                        if target:
                            target['config']['clip_routing']=b['clip_routing']
                            for sc in target.get('scenes') or []:
                                if not sc.get('clip'):engine_chain.reset(sc)
                            event(target,'Moteur V09 : Grok pour le clip 1 (Flow s’il n’est pas disponible), Flow pour les clips 2 à la fin.' if b['clip_routing']==engine_chain.V09 else 'Bascule par clip : Flow en premier, Grok seulement après un refus confirmé, puis retour à Flow pour le clip suivant.')
                    if 'follow' in b:
                        # Followed TikTok accounts in Le Filon (star), like the Atelier.
                        name=str(b['follow']).strip().lstrip('@')[:60];followed=STATE['settings'].setdefault('filon_follow',[])
                        if not re.fullmatch(r'[\w.\-]+',name):raise ValueError('Compte TikTok invalide')
                        followed.remove(name) if name in followed else followed.append(name)
                elif path=='/api/flow-auto':
                    STATE['settings']['flow_auto']=bool(b.get('enabled'))
                elif path=='/api/montage':
                    STATE['settings']['montage']=montage.validate(b.get('montage',{}),STATE['settings'].get('montage'))
                elif path=='/api/backups':
                    # Atelier "Mes sauvegardes": save every story now, or bring back the missing ones (paused).
                    if b.get('action')=='save':
                        for j in STATE['jobs']:backup_story(j)
                    elif b.get('action')=='restore':
                        back=story_backup.restore(backups_root(),{x['id'] for x in STATE['jobs']},job_dir,now())
                        STATE['jobs'][0:0]=back;save();return self.send_json({**public_state(),'restored':len(back)})
                    else:raise ValueError('Action de sauvegarde inconnue')
                elif path=='/api/job':
                    LICENCE.require()
                    cfg={**STATE['settings'],**b.get('config',{})}; cfg['scene_count']=int(cfg['scene_count']); cfg['flow_cost']=int(cfg['flow_cost'])
                    cfg['flow_model']=b.get('config',{}).get('flow_model',engines.DEFAULT_FLOW_MODEL)
                    if cfg['flow_model'] not in engines.FLOW_MODELS:raise ValueError('Modèle Flow non pris en charge')
                    # Moteur V09 for every new episode: Grok for clip 1, Flow (Omni 1.2 Flash, 10 s) for the rest.
                    cfg['clip_routing']=engine_chain.V09 if b.get('config',{}).get('clip_routing') in (None,'',engine_chain.V09) else b['config']['clip_routing']
                    if cfg['clip_routing'] not in (engine_chain.V09,'flow_grok_per_clip','chain'):raise ValueError('Mode de bascule inconnu')
                    cfg['video_engine']=engines.validate(b.get('config',{}).get('video_engine','flow'))
                    if cfg['video_engine'] not in engines.AVAILABLE:raise ValueError('Connecteur '+engines.ENGINES[cfg['video_engine']]['label']+' pas encore livré : choisissez Google Flow.')
                    cfg['flow_resolution']='1080p' if b.get('config',{}).get('flow_resolution')=='1080p' else '720p';cfg['clip_seconds']=engines.seconds({'config':cfg},cfg['video_engine'])
                    normalize_flow_resolution(cfg)
                    duration=b.get('config',{}).get('duration')
                    if duration is not None:
                        # Atelier-like fixed durations (TikTok monetisation needs more than one minute).
                        if int(duration) not in (30,60,120,180,240):raise ValueError('Durée inconnue')
                        cfg['duration']=int(duration)
                        # Durée garantie: enough plans for the target (more than 60 s for "1 min"), fades included.
                        fade=montage.FADES[montage.validate({},STATE['settings'].get('montage'))['transition']]
                        cfg['scene_count']=montage.scenes_for(int(duration),cfg['clip_seconds'],fade)
                    cfg['flow_cost']=int(b.get('config',{}).get('flow_cost',engines.FLOW_MODELS[cfg['flow_model']]['costs'][0]))
                    if cfg['flow_cost'] not in engines.FLOW_MODELS[cfg['flow_model']]['costs']:raise ValueError('Coût incompatible avec le modèle Flow choisi. Le coût réel sera vérifié avant tout envoi.')
                    cfg['language']=creation_language(cfg.get('language','Deutsch (de-DE)'))
                    # Claude model and effort: request first, then the last choice kept in the settings.
                    for k in CLAUDE_DEFAULTS:cfg[k]=claude_choice(k,cfg.get(k))
                    cfg['review_script']=bool(b.get('config',{}).get('review_script',False))
                    cfg['dry_run']=bool(b.get('config',{}).get('dry_run',False))
                    req=b.get('config',{})
                    # Montage chosen once in Mes comptes; each episode keeps its own copy.
                    cfg['montage']=montage.validate({},STATE['settings'].get('montage'))
                    cfg['karaoke']=bool(req['karaoke']) if 'karaoke' in req else cfg['montage']['karaoke']
                    cfg['subtitles']=bool(req.get('subtitles',True))
                    # Atelier "Qualité" (Économie: clips signalés, jamais refaits), "Format" and "Personnages".
                    if req.get('quality','normal') not in ('normal','economy'):raise ValueError('Qualité inconnue')
                    cfg['quality']=req.get('quality','normal')
                    if cfg['quality']=='economy':
                        # Like the Atelier: in Économie the checks only report, and nobody looks at the clips.
                        cfg['controls']='report';cfg['clip_look']='ear'
                        if cfg.get('board_controls')=='redo':cfg['board_controls']='report'
                        if cfg.get('cover_controls','fix')=='fix':cfg['cover_controls']='report'
                    if req.get('format','vertical') not in ('vertical','horizontal','both'):raise ValueError('Format inconnu')
                    fmt=req.get('format','vertical');cfg['format']='horizontal' if fmt=='horizontal' else None;cfg['also_horizontal']=fmt=='both'
                    if req.get('characters','simple') not in ('simple','detailed'):raise ValueError('Niveau de personnages inconnu')
                    cfg['characters_detail']=cfg.pop('characters',None) or 'simple'
                    # Owner 09/11/2026: the character style changes from one video to the next (chosen, or least used lately).
                    cfg['character_style']=character_styles.pick(req.get('character_style'),[x.get('config',{}).get('character_style') for x in STATE['jobs']])
                    source=str(b.get('source_url','')).strip()
                    captures=source_video.decode_captures(b.get('captures')) if source else []
                    if source:
                        # Atelier-like "create from a link": the given TikTok video replaces the research step.
                        u=urllib.parse.urlparse(source)
                        if u.scheme!='https' or u.hostname not in ('www.tiktok.com','tiktok.com','vm.tiktok.com','m.tiktok.com') or u.username or u.password:raise ValueError('Lien TikTok attendu (https://www.tiktok.com/@compte/video/…)')
                    requested_query=str(b.get('config',{}).get('query','')).strip()
                    # An omitted or untouched German default follows the chosen language.
                    cfg['query']=RESEARCH_QUERIES[cfg['language']] if not requested_query or requested_query in RESEARCH_QUERIES.values() else requested_query[:200]
                    if not 3<=cfg['scene_count']<=40 or not 1<=cfg['flow_cost']<=100 or cfg['provider'] not in ('chatgpt','claude'): raise ValueError('Réglages invalides')
                    if cfg['provider']=='claude':STATE['settings'].update({k:cfg[k] for k in CLAUDE_DEFAULTS})
                    j={'id':uid(),'title':'Nouvel épisode','brief':str(b.get('brief',''))[:4000], 'config':cfg,'editorial_version':2,'retention_version':1,'hook_version':1,'quality_version':1,'cover_style':'family_poster_v3','character_sheet':1,'flow_profile':b.get('flow_profile'),'status':'running','stage':'research','created':now(),'updated':now(),'events':[],'candidates':[],'characters':[],'scenes':[]}
                    # Créer / Recréer: accounts first (owner 06/11/2026); nothing is created while one is known « À régler ».
                    found=gate_blockers(j)
                    if found:raise AccountsNotReady(found)
                    STATE['jobs'].insert(0,j)
                    if source:
                        j['selected']={'title':'Vidéo fournie par le propriétaire','url':urllib.parse.urlunparse(('https',u.hostname,u.path,'','','')),'source':'owner_link'};thumbs.warm([j['selected']['url']],DATA);j['stage']='script'
                        j['config']['recreate']='identical' if req.get('recreate')=='identical' else 'inspired'
                        j['source_captures']=source_video.save_captures(captures,job_dir(j))
                        # The video is fetched and analysed first (key frames, transcription): the AI sees it, not only its link.
                        j['status']='waiting_source';threading.Thread(target=prepare_source,args=(j['id'],),daemon=True).start()
                        event(j,'Projet créé d’après le lien fourni : recherche sautée. '+('Copie fidèle (moteur V09) : même histoire, mêmes répliques traduites, seuls les personnages changent.' if j['config']['recreate']=='identical' else 'Histoire originale inspirée de cette vidéo (sans copier dialogues ni plans).')+(f" {len(j['source_captures'])} capture(s) jointe(s)." if j['source_captures'] else ''))
                    mode=b.get('mode')
                    if mode not in (None,'','link','ideas','idea','research'):raise ValueError('Option de création inconnue')
                    cfg['auto_sheet']=bool(b.get('config',{}).get('auto_sheet',False));cfg['niche']=str(b.get('config',{}).get('niche','Fruits'))[:40]
                    if mode=='ideas' and not source:
                        # Atelier "Pas d'idée": ten stories first, nothing paid before the sheet is validated.
                        j['stage']='ideas';j['selected']={'title':'Histoire originale choisie parmi dix propositions','source':'ideas'};event(j,'Projet créé : dix histoires demandées à '+('Claude' if cfg['provider']=='claude' else 'ChatGPT')+'.')
                    elif mode=='idea' and not source:
                        if len(j['brief'].strip())<15:raise ValueError('Décrivez votre idée en quelques phrases')
                        j['stage']='sheet';j['selected']={'title':'Idée du propriétaire','source':'owner_idea'};event(j,'Projet créé d’après votre idée : fiche de décision en cours.')
                    elif not source:event(j,'Projet créé. Recherche préalable et comparaison de cinq concepts obligatoires.')
                    if start_check(j):schedule(j)
                elif path.startswith('/api/job/'):
                    id=path.split('/')[-1]; j=job_by(id)
                    if not j: raise ValueError('Projet inconnu')
                    action=b.get('action')
                    if action=='pause':
                        j['status']='paused';j['autopilot']=False
                        # Real case 09/11/2026: a paused episode kept the ChatGPT lane of the window (« association conservée ») and every
                        # other episode waited 19 min. Its waiting tasks and its texts/boards in progress are released (nothing paid:
                        # chat lane only); a clip already sent keeps its follow-up (Flow credits).
                        freed=release_job_chat(j,'Épisode en pause')
                        event(j,'Pause demandée.'+(f' {freed} tâche(s) ChatGPT libérée(s) pour les autres épisodes ; elles seront refaites à la reprise.' if freed else '')+' Un clip déjà envoyé peut continuer chez le fournisseur.')
                    elif action=='resume':
                        # "Boucle complète": the studio decides alone at the quality checks and keeps going.
                        if j.get('stage')=='done' and j.get('final'):
                            j['status']='done';save();return self.send_json(public_state())
                        j['autopilot']=True;j['alerts']=[a for a in j.get('alerts',[]) if a['level']!='action']
                        active=next((t for t in STATE['tasks'] if t['job']==id and t['status']=='claimed'),None)
                        if active:
                            if b.get('flow_profile') and b['flow_profile']!=j.get('flow_profile'):raise ValueError('Un clip est déjà suivi : attendez sa récupération avant de changer de compte')
                            j['status']='running';event(j,'Suivi de la tâche en cours conservé ; aucun nouvel envoi.');save();return self.send_json(public_state())
                        # A clip whose Flow submission is uncertain waits for the owner; the other clips may go on (0.1.93).
                        uncertain={int(t['slot'].split(':')[1]) for t in uncertain_clip_tasks(j)}
                        if j.get('stage')=='clips' and uncertain and not any(not x.get('clip') and k not in uncertain for k,x in enumerate(j['scenes'])):raise ValueError(uncertain_message(j))
                        # Reprendre after « aucun moteur n'a pu faire ce clip »: every engine may try it again (the owner fixed something).
                        # Reprendre / Boucle complète: nothing is relaunched while a needed account is known « À régler ».
                        found=gate_blockers(j)
                        if found:raise AccountsNotReady(found)
                        if j.get('stage')=='script' and j.get('rejected_script'):
                            try:store_script(j,copy.deepcopy(j['rejected_script']))
                            except ValueError:pass
                            else:
                                for task in STATE['tasks']:
                                    if task['job']==id and task['status']=='queued':task['status']='cancelled'
                                event(j,'Brouillon existant réparé et réutilisé sans nouvelle demande de scénario.')
                                schedule(j);save();return self.send_json(public_state())
                        for index, scene in enumerate(j.get('scenes') or []):
                            if scene.get('clip'):
                                continue
                            if scene.get('engine_exhausted'):
                                attempts=scene.get('engine_tries') or []
                                last=attempts[-1] if attempts else {}
                                if (engine_chain.flow_grok_policy(STATE.get('settings'),j['config'])
                                        and last.get('engine')=='grok' and last.get('kind')=='interface'
                                        and re.search(r'image introuvable|image non importée',last.get('reason',''),re.I)):
                                    attempts.pop()
                                    scene.pop('engine_exhausted',None)
                                else:engine_chain.reset(scene)
                            if (not scene.get('engine_tries')
                                    and engine_chain.flow_grok_policy(STATE.get('settings'), j['config'])):
                                previous = next((t for t in reversed(STATE['tasks'])
                                                 if t['job'] == id and t.get('slot') == f'clip:{index}'
                                                 and t.get('kind') == 'flow_video' and t['status'] == 'failed'), None)
                                if previous and previous.get('error_kind') == 'refusal':
                                    engine_chain.record(scene, 'flow', 'refusal', 'Refus Flow déjà constaté', now())
                                    scene['flow_rewrite_pending']=True
                        if j.get('stage')=='clips' and any(scene.get('flow_rewrite_pending') for scene in j['scenes']):
                            j['stage']='images'
                        for t in STATE['tasks']:
                            if t['job']==id and t['status'] in ('queued','claimed'): t['status']='cancelled'
                        if b.get('flow_profile'): j['flow_profile']=b['flow_profile']
                        j.pop('last_error',None);j.pop('editorial_attempts',None);j.pop('accounts_check',None);j['status']='running'; event(j,'Reprise demandée ; passage automatique limité aux comptes Flow enregistrés.' if STATE.get('settings',{}).get('flow_auto') else 'Reprise demandée ; compte Flow sélectionné conservé.')
                        if start_check(j):schedule(j)
                    elif action=='allow_grok':
                        j['grok_ok']=True;j['alerts']=[a for a in j.get('alerts',[]) if a.get('command')!='allow_grok']
                        for sc in j['scenes']:
                            if sc.get('engine_exhausted') and not sc.get('clip'):engine_chain.reset(sc)
                        j['status']='running';event(j,'Grok autorisé par le propriétaire pour cet épisode.');schedule(j)
                    elif action=='retry_step':
                        # « Relancer cette étape » from the blocked banner: the stuck task is dropped and the step asked again.
                        info=stall_info(j)
                        if not info or not info.get('retry'):raise ValueError('Cette étape avance encore : rien à relancer.')
                        # Only the lane that does not move: a clip generating beside a stuck board keeps going.
                        blocked=next((t for t in STATE['tasks'] if t['id']==info.get('task')),None)
                        stuck=[t for t in STATE['tasks'] if t['job']==id and t['status'] in ('queued','claimed') and (not blocked or lane_of(t)==lane_of(blocked))]
                        if any(t['kind'] in ('flow_video','engine_video') for t in stuck) and not b.get('confirm_paid'):
                            raise ValueError('Un clip est peut-être déjà en cours chez le fournisseur : vérifie dans Flow, puis confirme la relance.')
                        for t in stuck:t['status']='failed';t['error']='Relancée par le propriétaire : étape bloquée ('+info['reason'][:120]+')'
                        if any(t['kind'] in ('flow_video','engine_video') for t in stuck):
                            for t in stuck:t['acknowledged']=now()
                        j.pop('last_error',None);event(j,'Étape relancée par le propriétaire : '+info['reason']);schedule(j)
                    elif action=='confirm_no_clip':
                        slot=str(b.get('slot',''))
                        pending=[t for t in uncertain_clip_tasks(j) if t['slot']==slot]
                        if not pending:raise ValueError('Aucun envoi Flow incertain pour cette scène')
                        for t in pending:t['acknowledged']=now()
                        event(j,'Le propriétaire confirme qu’aucun clip n’existe dans Flow pour la scène '+str(int(slot.split(':')[1])+1)+'. Nouvelle génération autorisée ; vérifiez le solde réel du compte Flow.')
                    elif action=='approve_quality':
                        if j.get('stage')!='quality' or not j.get('quality_report'):raise ValueError('Aucun contrôle qualité à valider')
                        report=j['quality_report'];key=quality.fingerprint(j,job_dir(j))
                        if report.get('hard_errors') or report.get('fingerprint')!=key:raise ValueError('Corrigez ou remplacez les médias techniquement invalides avant de poursuivre')
                        if not report.get('visual'):raise ValueError('La revue visuelle doit encore être effectuée ; utilisez la validation des paroles')
                        j['quality_approval']=key;j['status']='running';event(j,'Réserves du rapport acceptées explicitement par le propriétaire après vérification.');schedule(j)
                    elif action=='approve_speech':
                        if j.get('stage')!='quality' or not j.get('quality_report'):raise ValueError('Aucun contrôle des paroles à valider')
                        report=j['quality_report'];key=quality.fingerprint(j,job_dir(j))
                        if report.get('hard_errors') or report.get('fingerprint')!=key:raise ValueError('Médias invalides ou rapport périmé')
                        j['quality_speech_approval']=key;j['status']='running';event(j,'Paroles vérifiées et acceptées explicitement par le propriétaire.');schedule(j)
                    elif action=='research':
                        for t in STATE['tasks']:
                            if t['job']==id and t['slot']=='research' and t['status'] in ('queued','claimed'): t['status']='cancelled'
                        apply_research(j,b.get('candidates',[])); schedule(j)
                    elif action=='select':
                        source=next((r for r in j['candidates'] if r['url']==b.get('url')),None)
                        if not source: raise ValueError('Référence inconnue')
                        for t in STATE['tasks']:
                            if t['job']==id and t['status'] in ('queued','claimed'): t['status']='cancelled'
                        j['selected']=source; j['stage']='script'; j['status']='running'; event(j,'Référence choisie manuellement ; viralité non garantie.'); schedule(j)
                    elif action=='script':
                        for t in STATE['tasks']:
                            if t['job']==id and t['status'] in ('queued','claimed'): t['status']='cancelled'
                        store_script(j,b['script']); schedule(j)
                    elif action=='set_dry_run':
                        if any(t['job']==id and t['status']=='claimed' for t in STATE['tasks']):raise ValueError('Une tâche est en cours : attendez sa fin avant de changer de mode')
                        j['config']['dry_run']=bool(b.get('enabled'))
                        for t in STATE['tasks']:
                            # Queued Flow payloads were built for the previous mode.
                            if t['job']==id and t['status']=='queued' and t['kind'] in ('flow_video','engine_video'):t['status']='cancelled'
                        event(j,'Essai à blanc activé : les clips seront préparés dans Flow sans être envoyés.' if j['config']['dry_run'] else 'Production réelle : les prochains clips seront envoyés à Flow et consommeront des crédits.')
                    elif action=='flow_resolution':
                        if any(t['job']==id and t['status'] in ('queued','claimed') for t in STATE['tasks']):raise ValueError('Attendez la fin de la tâche avant de changer la résolution')
                        resolution=b.get('resolution')
                        if resolution not in ('720p','1080p'):raise ValueError('Résolution Flow inconnue')
                        j['config']['flow_resolution']=resolution;j.pop('dry_run_passed',None)
                        normalize_flow_resolution(j['config']);resolution=j['config']['flow_resolution']
                        event(j,'Résolution de génération Flow : '+resolution+'. Dimensions du montage final conservées.')
                    elif action=='rerender':
                        # "Remonter…": same clips, new montage (new hook, subtitles or resolution).
                        if not all(x.get('clip') for x in j['scenes']):raise ValueError('Il manque des clips')
                        if j['id'] in BUSY:raise ValueError('Montage déjà en cours')
                        for task in STATE['tasks']:
                            if task['job']==id and task['slot']=='cover_review' and task['status'] in ('queued','claimed'):
                                task['status']='cancelled'
                                event(j,'Revue automatique de la miniature interrompue par la demande de montage.')
                        j.pop('final',None);j.pop('montage_stale',None);j['stage']='edit';j['status']='rendering';event(j,'Remontage demandé avec les clips existants.');start_render(j['id'])
                    elif action=='rename':
                        title=' '.join(str(b.get('title','')).split())[:80]
                        if not title:raise ValueError('Titre vide')
                        j['title']=title
                        if j.get('script'):j['script']['title']=title
                        event(j,'Titre changé : '+title)
                    elif action=='distance':
                        # "Réécrire pour s'éloigner": before payment the sheet, after the montage the texts.
                        o=j.get('originality') or {};pre=j.get('sheet_precheck') or {}
                        ref=reference_text(j)
                        if j.get('stage')=='sheet' and j.get('sheet'):
                            j['sheet_previous']=j['sheet'];j['sheet']=None
                            j['sheet_note']='Éloigne-toi nettement de la vidéo d’origine (« '+ref[:300]+' ») : nouveau titre, nouvelle première réplique, autre décor, autre twist, autres prénoms. '+' '.join(pre.get('advice',[]))
                            j['status']='running';event(j,'Fiche renvoyée pour s’éloigner de l’original.');schedule(j)
                        elif j.get('script'):
                            schema={'production_id':j['id'],'title':'Nouveau titre','cover_title':'3 à 5 mots','hook_text':'Accroche écrite à l’écran, 4 à 7 mots','description':'Nouvelle description avec hashtags, mention de la création par IA'}
                            prompt=f"Réécris le titre, la couverture, l’accroche écrite et la description de cette vidéo dans la langue {j['config'].get('language')}, avec des mots entièrement nouveaux, pour qu’elle ne ressemble pas à la vidéo d’origine (« {ref[:400]} ») ni aux vidéos tendance. Ne reprends aucune phrase ni hashtag de l’original. Histoire : {j['script'].get('title')} — {j.get('brief','')[:500]}. Conseils : {' '.join(o.get('advice',[]))} Réponds UNIQUEMENT en JSON : {json.dumps(schema,ensure_ascii=False)}"
                            add_task(j,'chat_text',{'provider':j['config']['provider'],'prompt':prompt,'response_kind':'meta'},'rewrite_meta')
                        else:raise ValueError('Rien à réécrire pour l’instant')
                    elif action=='originality':
                        if not j.get('scenes') or not any(x.get('image') for x in j['scenes']):raise ValueError('Rien à contrôler : aucune planche')
                        check_originality(j)
                    elif action=='cover_base':
                        i=int(b.get('index',-1))
                        if not 0<=i<len(j['scenes']) or not j['scenes'][i].get('image'):raise ValueError('Scène sans planche')
                        j['cover_base']=i;event(j,'Miniature : base choisie, scène '+str(i+1)+'.')
                        if b.get('make') and j.get('cover_file'):redo(j,'cover',b.get('note',''),False)
                        elif b.get('make'):event(j,'La miniature sera faite après les clips, depuis cette scène.')
                    elif action=='redo':
                        redo(j,b.get('slot',''),b.get('note',''),bool(b.get('include_clip')))
                    elif action=='redo_clips':
                        done=redo_clips(j,[int(x) for x in b.get('scenes') or []])
                        event(j,f'{len(done)} clip(s) refait(s) d’après leur nouvelle planche : scène(s) '+', '.join(str(i+1) for i in done)+'.')
                    elif action=='edit_scene':
                        edit_scene(j,b.get('index'),b.get('texts'))
                    elif action=='restore_version':
                        restore_version(j,b.get('slot',''),str(b.get('file','')))
                    elif action=='edit_script':
                        edit_script(j,b.get('script',{}))
                    elif action=='approve_script':
                        if not review_pending(j) or j.get('stage')!='characters':raise ValueError('Aucune histoire en attente de validation')
                        j['script_approved']=now();j['status']='running';event(j,'Histoire validée par le propriétaire : création des images lancée.');schedule(j)
                    elif action=='pick_idea':
                        if j.get('stage')!='ideas' or not j.get('ideas'):raise ValueError('Aucune histoire à choisir')
                        i=int(b.get('index',-1))
                        if not 0<=i<len(j['ideas']):raise ValueError('Histoire inconnue')
                        idea=j['ideas'][i];j['idea_choice']=i;j['brief']=idea['title']+' : '+idea['pitch']+(' '+str(b.get('note',''))[:500] if b.get('note') else '')
                        j['stage']='sheet';j['status']='running';event(j,'Histoire choisie : « '+idea['title']+' ». Fiche de décision en cours.');schedule(j)
                    elif action=='more_ideas':
                        if j.get('stage')!='ideas':raise ValueError('Étape terminée')
                        j['ideas']=[];j['status']='running';event(j,'Dix autres histoires demandées.');schedule(j)
                    elif action=='approve_sheet':
                        if j.get('stage')!='sheet' or not j.get('sheet'):raise ValueError('Aucune fiche à valider')
                        sheet=ideas.apply_edits(j['sheet'],b.get('sheet') or {})
                        ti,hi,ci=int(b.get('title',0)),int(b.get('hook',0)),int(b.get('call',0))
                        if not (0<=ti<len(sheet['titles']) and 0<=hi<len(sheet['hooks']) and 0<=ci<max(1,len(sheet.get('end_calls') or []))):raise ValueError('Titre, réplique ou appel de fin inconnu')
                        approve_sheet(j,sheet,ti,hi,'Fiche validée : « '+sheet['titles'][ti]+' ». Écriture des plans en cours.',ci)
                    elif action=='revise_sheet':
                        if j.get('stage')!='sheet' or not j.get('sheet'):raise ValueError('Aucune fiche à revoir')
                        note=str(b.get('note','')).strip()[:800]
                        if not note:raise ValueError('Écrivez vos remarques')
                        j['sheet_previous']=ideas.apply_edits(j['sheet'],b.get('sheet') or {});j['sheet_note']=note;j['sheet']=None
                        j['status']='running';event(j,'Fiche renvoyée avec vos remarques.');schedule(j)
                    elif action=='account_switched':
                        if j['status']!='waiting_account':raise ValueError('Aucun changement de compte en attente')
                        switch=j.pop('account_switch',{});j['status']='running'
                        event(j,'Changement de compte confirmé ('+str(switch.get('to'))+'). Le connecteur vérifie l’identité affichée avant tout envoi.');schedule(j)
                    elif action=='continue_series':
                        LICENCE.require()
                        # P3-1: next part with the same cast; research is skipped (the story continues).
                        if j['status']!='done':raise ValueError('Terminez d’abord cet épisode')
                        part=series.part_of(j)+1;cfg={**copy.deepcopy(j['config']),'dry_run':False}
                        nxt={'id':uid(),'title':j.get('title','Épisode')+' — partie '+str(part),'brief':series.brief(j,str(b.get('note',''))[:500]),'config':cfg,
                             'series':{'id':j.get('series',{}).get('id',j['id']),'part':part,'previous':j['id']},'selected':j.get('selected') or {'title':j.get('title'),'url':''},
                             'flow_profile':j.get('flow_profile'),'status':'running','stage':'script','created':now(),'updated':now(),'events':[],'candidates':[],'characters':[],'scenes':[]}
                        for key in ('editorial_version','retention_version','hook_version','quality_version','cover_style','character_sheet'):
                            if key in j:nxt[key]=j[key]
                        STATE['jobs'].insert(0,nxt);event(nxt,'Partie '+str(part)+' créée à partir de « '+str(j.get('title'))+' » : mêmes personnages, scénario en cours.');schedule(nxt)
                        save();return self.send_json({**public_state(),'created':nxt['id']})
                    elif action=='variant':
                        nxt=make_variant(j,b.get('kind'),b.get('language',''));save();return self.send_json({**public_state(),'created':nxt['id']})
                    elif action=='delete':
                        # P4-1: never a silent loss: the folder goes to data/corbeille, the state is backed up first.
                        if any(t['job']==id and t['status']=='claimed' for t in STATE['tasks']):raise ValueError('Une tâche est en cours : attendez sa fin')
                        if j['status']=='rendering':raise ValueError('Montage en cours : attendez sa fin')
                        if uncertain_clip_tasks(j):raise ValueError(uncertain_message(j))
                        maintenance.backup_state(DATA,STATE)
                        if id in night()['ids']:night_drop(j,'supprimée')
                        target=maintenance.trash_job(DATA,id)
                        STATE['jobs'].remove(j);STATE['tasks']=[t for t in STATE['tasks'] if t['job']!=id]
                        save();return self.send_json({**public_state(),'trashed':target.name})
                    elif action=='characters_detail':
                        # Personnages Simple | Détaillé on the episode page: only while nothing is drawn yet.
                        level=b.get('level')
                        if level not in ('simple','detailed'):raise ValueError('Niveau de personnages inconnu')
                        if j.get('character_sheet_file') or any(c.get('file') for c in j.get('characters',[])):raise ValueError('Personnages déjà dessinés : utilisez Refaire')
                        if any(t['job']==id and t['status'] in ('queued','claimed') and str(t.get('slot','')).startswith('character') for t in STATE['tasks']):raise ValueError('Personnages en cours de dessin : attendez la fin')
                        j['config']['characters_detail']=level;event(j,'Personnages : niveau '+('Détaillé' if level=='detailed' else 'Simple')+'.')
                    elif action=='provider':
                        if b.get('provider') not in ('chatgpt','claude'): raise ValueError('IA inconnue')
                        j['config']['provider']=b['provider']; event(j,'IA de scénario modifiée ; médias conservés.')
                    else: raise ValueError('Action inconnue')
                else: return self.send_json({'error':'Route inconnue'},404)
                save(); self.send_json(public_state())
        except AccountsNotReady as e: self.send_json({'error':str(e),'blockers':e.blockers},409)
        except Exception as e: self.send_json({'error':str(e)},400)

def recover_after_restart():
    with LOCK:
        try:
            # P4-1: bounded state, with a copy kept before any cleanup.
            maintenance.backup_state(DATA,STATE);maintenance.purge(STATE,time.time())
        except Exception as e:log_error('Purge au démarrage',e)
        # Never automatically resend an ambiguous generation after a restart.
        for t in STATE['tasks']:
            if t['status']=='claimed':
                if client_online(STATE['clients'].get(t.get('client'))):
                    event(job_by(t['job']),'Redémarrage : suivi de la tâche '+t['slot']+' conservé dans la fenêtre connectée ; aucun nouvel envoi.')
                    continue
                t['status']='failed'; j=job_by(t['job']); j['status']='attention'; event(j,'Redémarrage : génération précédente à vérifier avant de réessayer.')
                j['last_error']={'kind':'restart','slot':t.get('slot'),'task':t.get('id'),'at':now()}
        for j in STATE['jobs']:
            if j.get('status')=='waiting_source':threading.Thread(target=prepare_source,args=(j['id'],),daemon=True).start()
        for j in STATE['jobs']:
            if j.get('stage') in ('images','clips'):
                try:repair_duplicate_scenes(j)
                except Exception as e:
                    j['status']='attention';event(j,'Vérification des images impossible : '+str(e))
        for j in STATE['jobs']:
            # The render thread died with the previous process: restart the local montage only.
            if j.get('stage')=='edit' and j.get('status')=='rendering' and not j.get('final'):
                j['status']='running';event(j,'Redémarrage pendant le montage : reprise locale sans nouvelle génération.');schedule(j)
        save()

def licence_loop():
    # A fresh signed verdict once a day; without internet the current one lasts the 3-day grace period.
    while True:
        try:
            if licence.REQUIRED and LICENCE.due():LICENCE.refresh()
        except Exception as e:log_error('Vérification de la clé',e)
        time.sleep(3600)

if __name__=='__main__':
    recover_after_restart()
    print(f'FruchtDrama Studio : http://127.0.0.1:{PORT}',flush=True)
    threading.Thread(target=flow_dispatch_loop,daemon=True).start()
    threading.Thread(target=licence_loop,daemon=True).start()
    http.server.ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
