"""Local studio. Python 3.10+, Pillow for covers, ffmpeg for exports."""
from __future__ import annotations
import base64, copy, datetime as dt, hashlib, hmac, http.server, json, mimetypes, os, pathlib, re, secrets, shutil, subprocess, threading, time, urllib.parse, uuid, zipfile
import flow_accounts
import flow_credits
import editorial
import captions
import covers
import quality
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
DATA = pathlib.Path(os.environ.get('FRUCHT_DATA', ROOT / 'data')).resolve()
PORT = int(os.environ.get('FRUCHT_PORT', '8840'))
LOCK = threading.RLock()
BUSY = set()
QUALITY_BUSY = set()
DOWNLOADS_ROOT = pathlib.Path(os.environ.get('FRUCHT_DOWNLOADS',pathlib.Path.home()/'Downloads')).resolve()
STEPS = ['research', 'script', 'characters', 'images', 'clips', 'quality', 'cover', 'edit', 'done']
LABELS = {'research':'Recherche', 'script':'Scénario', 'characters':'Personnages', 'images':'Scènes', 'clips':'Animation Flow', 'quality':'Contrôle qualité', 'cover':'Couverture', 'edit':'Montage', 'done':'Terminé'}
CREATION_LANGUAGES=('Deutsch (de-DE)','Français (fr-FR)','English (en-US)')
# Default research query per creation language (same values as the web form).
RESEARCH_QUERIES={'Deutsch (de-DE)':'KI Früchte Geschichten deutsch','Français (fr-FR)':'histoires fruits IA français','English (en-US)':'AI fruit drama stories English'}

def creation_language(value):
    value=str(value).strip()
    if value not in CREATION_LANGUAGES:raise ValueError('Choisissez Deutsch, Français ou English')
    return value

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def uid(): return uuid.uuid4().hex[:16]
def fresh():
    return {'version':1, 'token':secrets.token_urlsafe(32), 'pair_code':secrets.token_hex(4), 'jobs':[], 'profiles':[], 'clients':{}, 'tasks':[], 'settings':{'provider':'chatgpt','language':'Deutsch (de-DE)','scene_count':4,'clip_seconds':8,'flow_model':'gemini_omni_flash','flow_resolution':'720p','flow_cost':12,'query':'KI Früchte Geschichten deutsch','daily_budget':50}}
def read_state():
    DATA.mkdir(parents=True, exist_ok=True)
    p=DATA/'state.json'
    state=json.loads(p.read_text('utf-8')) if p.exists() else fresh()
    if 'flow_model' not in state['settings']:
        state['settings'].update(flow_model='gemini_omni_flash',flow_resolution='720p',flow_cost=12)
    return state
STATE=read_state()
def save():
    p=DATA/'state.tmp'
    p.write_text(json.dumps(STATE, ensure_ascii=False, indent=2),'utf-8'); p.replace(DATA/'state.json')
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
def client_accepts(client,task):
    role=client.get('role','all')
    if task['kind'] in ('flow_video','flow_collect'):
        target=task.get('payload',{}).get('flow_route')
        if target and not profile_by(task.get('profile')):return False
        return role in ('all','flow') and (target.get('client')==client.get('id') if target else task.get('profile')==client.get('flow_profile'))
    if role not in ('all','creation'):return False
    if task['kind'] in ('chat_text','chat_collect','chat_image','chat_image_collect'):
        provider=task.get('payload',{}).get('provider','chatgpt')
        return client.get('ai_provider','both') in ('both',provider)
    return task['kind']=='tiktok_search'
def event(j, text): j['events'].append({'at':now(),'text':text}); j['updated']=now()
def public_state():
    s=copy.deepcopy(STATE); s.pop('token',None)
    for t in s['tasks']: t.pop('result',None)
    for public,j in zip(s['jobs'],STATE['jobs']):
        public['uncertain_clips']=sorted({int(t['slot'].split(':')[1]) for t in uncertain_clip_tasks(j)})
    s['ffmpeg']=bool(shutil.which('ffmpeg')); return s
def safe_child(parent, name):
    target=(parent/name).resolve()
    if target==parent.resolve() or parent.resolve() not in target.parents: raise ValueError('Chemin interdit')
    return target
def job_dir(j):
    d=safe_child(DATA/'jobs',j['id']); d.mkdir(parents=True,exist_ok=True); return d
def asset_url(j, file): return f"/media/{j['id']}/{file}"

def flow_dispatch_tick():
    """Wake only the one browser needed for the next queued Flow clip."""
    pending=None
    with LOCK:
        if not STATE.get('settings',{}).get('flow_auto'):return
        if any(t['kind'] in ('flow_video','flow_collect') and t['status']=='claimed' for t in STATE['tasks']):return
        for j in STATE['jobs']:
            if j['stage']=='clips' and j['status']=='waiting_credit':
                if flow_accounts.choose(STATE,j.get('flow_profile'),j['config']['flow_cost']):j['status']='running'
            if j['status']=='running':schedule(j)
        task=next((t for t in STATE['tasks'] if t['kind']=='flow_video' and t['status']=='queued' and job_by(t['job'])['status']=='running'),None)
        if not task:
            p=flow_credits.prepare(STATE,time.time())
            if not p:return
            probe=p['credit_probe'];client=STATE['clients'].get(probe['client'],{})
            if time.time()-flow_credits.seconds(client.get('seen'))<75:save();return
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
        client=STATE['clients'].get(target['client'],{})
        try:online=time.time()-dt.datetime.fromisoformat(client.get('seen','')).timestamp()<75
        except ValueError:online=False
        if online:return
        if task.get('browser_opened'):
            if time.time()-dt.datetime.fromisoformat(task['browser_opened']).timestamp()>180:
                j=job_by(task['job']);j['status']='attention';event(j,'Navigateur ouvert mais passerelle absente. Vérifiez le profil Chrome enregistré, la connexion Google et l’extension.');save()
            return
        task['browser_opened']=now();pending=copy.deepcopy(p);event(job_by(task['job']),'Ouverture automatique de Chrome et du compte Flow enregistré.');save()
    try:flow_accounts.launch(pending)
    except Exception as e:
        with LOCK:
            j=job_by(task['job']);j['status']='attention';event(j,'Ouverture Flow impossible : '+str(e));save()

LAST_ERRORS={}
def log_error(context,error,interval=60):
    """Write a traceback to stderr (data/server-errors.log), at most once per interval for the same error."""
    key=(context,type(error).__name__,str(error));moment=time.time()
    if moment-LAST_ERRORS.get(key,0)<interval:return False
    LAST_ERRORS[key]=moment
    print(f'[{now()}] {context} : '+''.join(traceback.format_exception(type(error),error,error.__traceback__)),file=sys.stderr,flush=True)
    return True

def dispatch_once():
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
            'Each character appears exactly once, clearly separated, with a small plain name label under each one. '
            'No other text, no scene, no props unless part of the outfit.\n'+cast)

def image_fingerprint(j,file):
    from PIL import Image
    with Image.open(safe_child(job_dir(j),file)) as image:
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
    if not 4<=float(metadata.get('format',{}).get('duration',0))<=12 or video.get('height',0)<=video.get('width',0) or not any(x.get('codec_type')=='audio' for x in streams):raise ValueError('Le clip doit être vertical, durer environ huit secondes et contenir de l’audio')
    name=t['slot'].replace(':','_')+'_'+uid()+source.suffix.lower();shutil.copyfile(source,job_dir(j)/name)
    t['download_import']={'id':download_id,'file':name};return name

def duplicate_scene_source(j,file,index):
    fingerprint=image_fingerprint(j,file)
    sources=[c.get('file') for c in j.get('characters',[])]+[s.get('image') for i,s in enumerate(j.get('scenes',[])) if i!=index]
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
        age=None
        try: age=max(1,(dt.datetime.now(dt.timezone.utc).date()-dt.date.fromisoformat(item['date'][:10])).days)
        except ValueError: pass
        item['age_days']=age
        text=item['title'].lower()
        words={'Deutsch (de-DE)':['deutsch','frücht','frucht','ki','story','geschichte'], 'Français (fr-FR)':['français','francais','fruit','histoire','ia','drame'], 'English (en-US)':['english','fruit','story','stories','ai','drama']}.get(language,[])
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

def validate_script(s, n):
    if not isinstance(s,dict): raise ValueError('Objet JSON attendu')
    chars=s.get('characters',[]); scenes=s.get('scenes',[])
    if not 1<=len(chars)<=3 or len(scenes)!=n: raise ValueError(f'Il faut 1–3 personnages et exactement {n} scènes')
    ids=[c.get('id') for c in chars]
    if len(set(ids))!=len(ids) or any(not re.fullmatch('[a-z][a-z0-9_]{0,24}',str(x)) for x in ids): raise ValueError('Identifiants personnages invalides')
    for c in chars:
        if not all(isinstance(c.get(k),str) and c[k].strip() for k in ['name','appearance','voice','image_prompt']): raise ValueError('Fiche personnage incomplète')
    for scene in scenes:
        if not all(isinstance(scene.get(k),str) and scene[k].strip() for k in ['image_prompt','video_prompt','meaning']): raise ValueError('Prompt ou sens de scène manquant')
        lines=scene.get('dialogue',[])
        if not lines or any(x.get('speaker') not in ids or not isinstance(x.get('text'),str) or not x['text'].strip() for x in lines): raise ValueError('Dialogue ou locuteur invalide')
        if not set(scene.get('characters',[])).issubset(ids) or not scene.get('characters'): raise ValueError('Distribution de scène invalide')
        if any(x['speaker'] not in scene['characters'] for x in lines): raise ValueError('Locuteur absent de la scène')
        if sum(len(x['text'].split()) for x in lines)>25: raise ValueError('Dialogue trop long pour un clip de huit secondes (25 mots maximum)')
    for k in ['title','cover_title','description']:
        if not isinstance(s.get(k),str) or not s[k].strip(): raise ValueError('Titre, couverture ou description manquant')
    return s

def parse_json(text):
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',str(text).strip())
    start=text.find('{'); end=text.rfind('}')
    if start<0 or end<start: raise ValueError('La réponse ne contient pas de JSON')
    return json.loads(text[start:end+1])

def script_prompt(j):
    ref=j['selected']; n=j['config']['scene_count']
    language=j['config'].get('language','Deutsch (de-DE)')
    schema={'production_id':j['id'],'title':'Titre dans la langue choisie','cover_title':'Question courte dans la langue choisie','description':'Description TikTok dans la langue choisie, mentionnant la création par IA','characters':[{'id':'fruit_a','name':'Prénom dans la langue choisie','appearance':'Design de fruit et vêtements cohérents','voice':'Voix native de la langue choisie, âge, timbre','image_prompt':'Prompt de référence dans la langue choisie'}],'scenes':[{'characters':['fruit_a'],'meaning':'Action compréhensible sans le son','image_prompt':'Prompt d’image dans la langue choisie, 9:16','video_prompt':'Animation, caméra, action, position des locuteurs, lèvres et personnages silencieux','dialogue':[{'speaker':'fruit_a','text':'Réplique courte dans la langue choisie'}]}]}
    guidance=''
    # Announce the limit the validators actually enforce (editorial.validate: 20 for retention productions).
    word_limit=20 if j.get('editorial_version')==2 and j.get('retention_version')==1 else 25
    if j.get('editorial_version')==2:
        schema['creative_selection']={'candidates':[{'title':'Titre du concept','hook':'Première réplique','conflict':'Conflit','setting':'Décor','twist':'Retournement','ending':'Fin','scores':{'hook':4,'clarity':4,'emotion':4,'novelty':5}} for _ in range(5)],'selected_index':0,'reason':'Justification éditoriale, pas une prédiction de vues'}
        if j.get('hook_version')==1:
            schema['opening_plan']={'visible_detail':'Objet ou geste visible dès la première image','question':'Question laissée ouverte par la première réplique','payoff_scene':n,'payoff':'Explication concrète apportée dans cette scène'}
        schema['story_signature']={'relationship':'short English relationship','setting':'short English setting','central_object':'short English object','twist_mechanism':'short English plot mechanism'}
        guidance=editorial.instructions(j,STATE['jobs'])+'\nRéférences comparées : '+json.dumps(j.get('candidates',[])[:6],ensure_ascii=False)+'\nCorrections demandées : '+json.dumps(j.get('editorial_feedback',[]),ensure_ascii=False)
    return f'''Crée une mini-fiction de fruits entièrement ORIGINALE. Langue demandée pour les dialogues, les voix, les textes de couverture, la description et les prompts (sauf les clés techniques et la signature narrative) : {language}. La langue demandée prime sur la langue française des instructions et des descriptions du schéma. Aucune traduction ni réplique dans une autre langue. Les personnages parlent avec des voix natives de la langue demandée. Réponds UNIQUEMENT avec du JSON valide, sans explication. Conserve les clés techniques du schéma en anglais. Référence comme indice de tendance seulement, jamais copier les répliques ou les plans : {json.dumps(ref,ensure_ascii=False)}. Idée : {j['brief']}. Exactement {n} scènes de 8 secondes, au maximum 3 personnages. Au plus {word_limit} mots parlés par scène pour les langues avec espaces ; pour les autres, une réplique assez courte pour être prononcée naturellement en moins de 7 secondes. Maximum 2 locuteurs par scène. Accroche dès la première phrase, retournement visible, conclusion satisfaisante. Pas de présentation comme fait réel. Animation 3D premium, fruits anthropomorphes avec peau de fruit aussi sur les mains, vêtements couvrants sans logos, grands visages expressifs, décor cohérent avec l’intrigue choisie et différent des épisodes récents, vertical 9:16. Même identité et tenue partout, aucune voix de narrateur, personnages parlant à l'écran, caméra continue par clip. Sous-titres ajoutés au montage. {guidance} Le champ cover_title doit être une accroche de couverture de 3 à 5 mots maximum dans la langue demandée, sans révéler la fin. Schéma : {json.dumps(schema,ensure_ascii=False)}'''

def add_task(j, kind, payload, slot):
    if any(t['job']==j['id'] and t['slot']==slot and t['status'] in ('queued','claimed') for t in STATE['tasks']): return
    t={'id':uid(),'job':j['id'],'kind':kind,'payload':payload,'slot':slot,'status':'queued','created':now(),'profile':j.get('flow_profile') if kind=='flow_video' else None}
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

def schedule(j):
    if j['status'] in ('paused','attention','done','rendering','waiting_research','waiting_script','waiting_credit','waiting_review'): return
    if any(t['job']==j['id'] and t['status'] in ('queued','claimed') for t in STATE['tasks']): return
    step=j['stage']
    if step=='research':
        query=j['config']['query']
        if j.get('editorial_version')==2:
            j.setdefault('research_queries',editorial.queries(j,STATE['jobs']))
            index=min(j.get('research_round',0),len(j['research_queries'])-1);query=j['research_queries'][index]
        add_task(j,'tiktok_search',{'query':query},'research')
    elif step=='script':
        if j.get('editorial_version')==2:editorial.direction(j,STATE['jobs'])
        add_task(j,'chat_text',{'provider':j['config']['provider'],'prompt':script_prompt(j),'scene_count':j['config']['scene_count']},'script')
    elif step=='characters':
        if review_pending(j):
            # Nothing is paid before the owner has read the story (P1-1).
            j['status']='waiting_review';event(j,'Histoire prête : relisez et corrigez les dialogues, puis validez pour lancer les images.');return
        if j.get('character_sheet')==1 and len(j['characters'])>1 and not any(c.get('file') for c in j['characters']):
            # P1-2: one image for the whole cast instead of one paid image per character.
            add_task(j,'chat_image',{'provider':'chatgpt','prompt':sheet_prompt(j)+correction(j.get('corrections',{}).get('characters')),'attachments':[]},'characters');return
        for c in j['characters']:
            if not c.get('file'):
                add_task(j,'chat_image',{'provider':'chatgpt','prompt':c['image_prompt']+' Create one full-body character reference image. No text. Premium 3D animation, 9:16.'+correction(j.get('corrections',{}).get('character:'+c['id'])),'attachments':[]},f"character:{c['id']}"); return
        j['stage']='images'; schedule(j)
    elif step=='images':
        for i,s in enumerate(j['scenes']):
            if not s.get('image'):
                add_task(j,'chat_image',{'provider':'chatgpt','prompt':s['image_prompt']+' Use attached character references. Same identity and outfit, no text, 9:16.'+correction(j.get('corrections',{}).get(f'image:{i}')),'attachments':image_assets(j)},f'image:{i}'); return
        j['stage']='clips'; schedule(j)
    elif step=='clips':
        for i,s in enumerate(j['scenes']):
            if not s.get('clip'):
                if any(t['slot']==f'clip:{i}' for t in uncertain_clip_tasks(j)):
                    j['status']='attention';event(j,uncertain_message(j));return
                cost=j['config']['flow_cost'];p=flow_accounts.choose(STATE,j.get('flow_profile'),cost)
                if not p or p['balance']<cost:
                    j['status']='waiting_credit'; event(j,'Solde insuffisant ou profil Flow absent. Choisis un profil et vérifie son solde.'); return
                if p['id']!=j.get('flow_profile'):
                    j['flow_profile']=p['id'];event(j,'Passage automatique au prochain compte Flow enregistré ; clips reçus conservés.')
                cast='\n'.join(c['id']+': '+c['appearance']+' Voice: '+c['voice'] for c in j['characters'])
                dialog='\n'.join(x['speaker']+': '+x['text'] for x in s['dialogue'])
                language=j['config'].get('language','Deutsch (de-DE)')
                prompt=f"One continuous shot, 8 seconds, portrait 9:16. No text, no music. Spoken language ONLY: {language}. Natural native voices in the requested language, no translation or extra narration. Preserve identity.\n{cast}\n{s['video_prompt']}\nExact dialogue in this order; only the named speaker moves their lips, all others stay silent:\n{dialog}"+correction(j.get('corrections',{}).get(f'clip:{i}'))
                payload={'prompt':prompt,'attachments':[asset_url(j,flow_reference(j,s['image']))],'cost':cost,'balance':p['balance'],'seconds':8,**({'model':j['config']['flow_model'],'resolution':j['config'].get('flow_resolution','720p')} if j['config'].get('flow_model') else {})}
                if j['config'].get('dry_run'):payload['dry_run']=True
                target=flow_accounts.route(p) if STATE.get('settings',{}).get('flow_auto') else None
                if target:
                    existing=j.get('flow_projects',{}).get(p['id'])
                    if existing:target['url']=existing
                    else:target['new_project']=True
                    payload['flow_route']=target
                add_task(j,'flow_video',payload,f'clip:{i}'); return
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
            reference=next((scene['image'] for scene in j['scenes'] if scene.get('image')),None)
            attachments=[asset_url(j,reference)] if reference else image_assets(j)
            template=ROOT/('cover-reference-grid.png' if j.get('cover_style')=='family_poster_v3' else 'cover-proposal-v2.png')
            if template.is_file():
                style_file=job_dir(j)/'cover-style-reference.png'
                if not style_file.exists():shutil.copyfile(template,style_file)
                attachments.append(asset_url(j,style_file.name))
            add_task(j,'chat_image',{'provider':'chatgpt','prompt':cover_prompt(j)+correction(j.get('corrections',{}).get('cover')),'attachments':attachments},'cover');return
        j['stage']='edit';j['status']='rendering';event(j,'Montage local démarré.');start_render(j['id'])
    elif step=='edit':
        # A failed or interrupted montage is retried locally; no media is regenerated.
        if not j.get('final'):
            j['status']='rendering';event(j,'Montage local relancé avec les médias existants.');start_render(j['id'])

def uncertain_clip_tasks(j):
    """Flow submissions that may have been charged but whose clip was never received."""
    scenes=j.get('scenes',[])
    def missing(t):
        index=int(t['slot'].split(':')[1])
        return index<len(scenes) and not scenes[index].get('clip')
    return [t for t in STATE['tasks'] if t.get('job')==j['id'] and t.get('kind')=='flow_video' and t.get('status')=='failed'
            and t.get('reservation') and not t['reservation'].get('refunded') and not t.get('acknowledged')
            and str(t.get('slot','')).startswith('clip:') and missing(t)]

def uncertain_message(j):
    scenes=sorted({int(t['slot'].split(':')[1])+1 for t in uncertain_clip_tasks(j)})
    return ('Envoi Flow incertain pour la scène '+', '.join(map(str,scenes))+' : le clip a peut-être déjà été généré et facturé. '
            'Laissez la passerelle le récupérer, importez-le, ou confirmez qu’il n’existe pas dans Flow avant toute nouvelle génération.')

def correction(note):
    return f'\nOwner correction for this new attempt (apply it, keep everything else unchanged): {note}' if note else ''

REDO_STAGES={'characters':'characters','character':'characters','image':'images','clip':'clips','cover':'cover'}

def redo(j,slot,note='',include_clip=False):
    """P1-3: regenerate one media with an owner correction; earlier media and files are kept."""
    slot=str(slot);note=' '.join(str(note or '').split())[:500]
    kind=slot.split(':')[0]
    if kind not in REDO_STAGES or not re.fullmatch(r'(?:cover|characters|character:[a-z][a-z0-9_]{0,24}|image:\d+|clip:\d+)',slot):raise ValueError('Élément à refaire inconnu')
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
    elif kind=='image':
        if not scene.get('image'):raise ValueError('Rien à refaire : image pas encore créée')
        if scene.get('clip') and not include_clip:raise ValueError('Le clip de cette scène a été animé depuis cette image : refaites l’image et le clip ensemble')
        remember(slot,scene.pop('image'))
        if scene.get('clip'):remember(f'clip:{index}',scene.pop('clip'))
        if include_clip:j.setdefault('corrections',{})[f'clip:{index}']=note
    elif kind=='clip':
        if not scene.get('clip'):raise ValueError('Rien à refaire : clip pas encore créé')
        remember(slot,scene.pop('clip'))
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
    schedule(j)

def schedule_quality(j):
    folder=job_dir(j);key=quality.fingerprint(j,folder);report=j.get('quality_report',{})
    if report.get('fingerprint')!=key:
        if j['id'] not in QUALITY_BUSY:
            QUALITY_BUSY.add(j['id']);event(j,'Contrôle local des clips, transcription et préparation des images de revue démarrés.')
            threading.Thread(target=run_quality,args=(j['id'],key),daemon=True).start()
        return
    if report.get('hard_errors'):
        j['status']='attention';event(j,'Contrôle qualité bloquant : '+report['hard_errors'][0]+' Les clips sont conservés.');return
    if report.get('warnings') and j.get('quality_speech_approval')!=key and j.get('quality_approval')!=key:
        j['status']='attention';event(j,'Contrôle des paroles à vérifier : '+report['warnings'][0]+' Aucun clip ne sera régénéré automatiquement.');return
    visual=report.get('visual')
    if not visual:
        attachments=image_assets(j)
        attachments += [asset_url(j,c['sheet']) for c in report['clips'] if c.get('sheet')]
        add_task(j,'chat_text',{'provider':'chatgpt','prompt':quality.visual_prompt(j),'attachments':attachments,'response_kind':'quality_review','scene_count':len(j['scenes']),'fingerprint':key},'quality_review');return
    issues=[x for x in [*visual['scenes'],visual['continuity']] if x['status']!='pass']
    if issues and j.get('quality_approval')!=key:
        j['status']='attention';event(j,'Cohérence visuelle à vérifier : '+issues[0]['detail']+' Médias conservés, aucun nouvel envoi Flow.');return
    report['status']='approved_with_reservations' if report.get('warnings') or issues else 'checked'
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
    validate_script(draft,j['config']['scene_count'])
    if j.get('editorial_version')==2 and j.get('retention_version')==1:
        for i,scene in enumerate(draft['scenes']):
            if len(scene['dialogue'])>2 or sum(len(x['text'].split()) for x in scene['dialogue'])>20:
                raise ValueError(f'Scène {i+1} : deux répliques et 20 mots au plus pour tenir dans le clip de huit secondes')
    j['script']=draft;j['title']=draft['title']
    for scene,source in zip(j['scenes'],draft['scenes']):scene['dialogue']=copy.deepcopy(source['dialogue'])
    d=job_dir(j);(d/'scenario.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2),'utf-8');(d/'description.txt').write_text(draft['description'],'utf-8')
    event(j,'Histoire corrigée par le propriétaire avant les images.')
    return True

def store_script(j,s):
    if s.get('production_id') and s['production_id']!=j['id']:raise ValueError('Ce scénario appartient à une autre production')
    validate_script(s,j['config']['scene_count']);editorial.validate(s,j,STATE['jobs'])
    j['script']=s; j['characters']=copy.deepcopy(s['characters']); j['scenes']=copy.deepcopy(s['scenes']); j['title']=s['title']; j['stage']='characters'; j['status']='running'
    d=job_dir(j); (d/'scenario.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),'utf-8'); (d/'description.txt').write_text(s['description'],'utf-8'); event(j,'Scénario structuré validé ; langue de création : '+j['config'].get('language','Deutsch (de-DE)')+'.')

def apply_research(j,rows):
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
    if not result.get('ok') and t.get('kind')=='flow_video' and result.get('dry_run') is True and t.get('payload',{}).get('dry_run') and result.get('generation_submitted') is False:
        t['status']='cancelled';t['dry_run_passed']=now();j['dry_run_passed']=now();j['status']='paused'
        event(j,str(result.get('error','Essai à blanc réussi.'))[:600]+' Désactivez l’essai à blanc puis cliquez sur Reprendre pour générer réellement.')
        return
    if not result.get('ok'):
        reservation=t.get('reservation')
        if t.get('kind')=='flow_video' and result.get('generation_submitted') is False and reservation and not reservation.get('refunded'):
            p=profile_by(reservation['profile'])
            if p:p['balance']+=reservation['amount'];reservation['refunded']=True;event(j,'Réservation locale de crédits annulée : aucune génération n’a été envoyée à Flow.')
        t['status']='failed'; j['status']='paused' if was_paused else 'attention'; event(j,str(result.get('error','Connecteur interrompu'))[:1200])
        if t.get('kind')=='flow_video' and result.get('generation_submitted') is False and result.get('flow_blocked')=='credits' and t.get('payload',{}).get('flow_route'):
            p=profile_by(t.get('profile'))
            if p:p['blocked']='credits'
            if not was_paused and STATE.get('settings',{}).get('flow_auto'):
                j['status']='running';schedule(j)
        return
    slot=t['slot']
    if slot=='research': apply_research(j,result.get('candidates',[]))
    elif slot=='quality_review':
        if quality.fingerprint(j,job_dir(j))!=t['payload'].get('fingerprint'):raise ValueError('Médias changés pendant le contrôle : rapport non applicable')
        review=quality.validate_visual(parse_json(result.get('text','')),j,t['id'])
        j['quality_report']['visual']=review
        (job_dir(j)/'quality-report.json').write_text(json.dumps(j['quality_report'],ensure_ascii=False,indent=2),'utf-8')
        event(j,'Revue visuelle IA reçue ; lèvres et identité des voix restent non certifiées.')
    elif slot=='script':
        try:store_script(j,parse_json(result.get('text','')))
        except ValueError as e:
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
        elif slot.startswith('image:'):
            index=int(slot.split(':')[1])
            if duplicate_scene_source(j,file,index):raise ValueError('Image rejetée : copie exacte d’une référence ou d’une autre scène. Attente de la véritable image générée.')
            j['scenes'][index]['image']=file
        elif slot.startswith('clip:'): j['scenes'][int(slot.split(':')[1])]['clip']=file
        elif slot=='cover':
            if duplicate_scene_source(j,file,-1) or ((job_dir(j)/'cover-style-reference.png').is_file() and image_fingerprint(j,file)==image_fingerprint(j,'cover-style-reference.png')):raise ValueError('Couverture rejetée : copie exacte d’une référence. Attente de la couverture composée.')
            j['cover_file']=file;j['cover']=asset_url(j,file)
        event(j,'Média reçu : '+file)
    t['status']='done'; t['result']=result
    if was_paused: j['status']='paused'
    schedule(j)

def run_command(args,cwd=None):
    r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=240,cwd=cwd)
    if r.returncode: raise RuntimeError(r.stderr[-1800:])

def render_job(id):
    try:
        with LOCK: j=copy.deepcopy(job_by(id)); d=job_dir(j)
        ff=shutil.which('ffmpeg')
        if not ff: raise RuntimeError('ffmpeg introuvable. Installe ffmpeg et relance le studio.')
        aligned_count=0
        caption_size,caption_words=(48,4) if j.get('retention_version')==1 else (38,5)
        ass=['[Script Info]','ScriptType: v4.00+','PlayResX: 720','PlayResY: 1280','[V4+ Styles]','Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',f'Style: Default,Arial,{caption_size},&H00FFFFFF,&H0000FFFF,&H00141414,&H70000000,-1,0,0,0,100,100,0,0,1,3,1,2,55,55,160,1','[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
        def stamp(s): return f'{int(s//3600)}:{int(s//60)%60:02}:{int(s)%60:02}.{int(s%1*100):02}'
        for i,s in enumerate(j['scenes']):
            src=safe_child(d,s['clip']); out=d/f'normalized_{i:02}.mp4'
            # Normalize silent imports too; every clip gets an audio stream.
            probe=shutil.which('ffprobe'); audio=True
            if probe:
                pr=subprocess.run([probe,'-v','error','-select_streams','a','-show_entries','stream=index','-of','csv=p=0',str(src)],capture_output=True,text=True,timeout=30); audio=bool(pr.stdout.strip())
            args=[ff,'-y','-i',str(src),'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-map','0:v:0','-map','0:a:0' if audio else '1:a:0','-vf','scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=30,tpad=stop_mode=clone:stop_duration=8','-af','apad','-t','8','-c:v','libx264','-preset','fast','-crf','21','-c:a','aac','-ar','48000','-ac','2',str(out)]
            run_command(args)
            speech=(j.get('quality_report',{}).get('clips',[])[i].get('speech') if j.get('quality_version')==1 and i<len(j.get('quality_report',{}).get('clips',[])) else None)
            aligned=quality.caption_events(s,speech,i*8,caption_words,30) if speech else None
            if aligned:
                aligned_count+=1
                for a,b,text in aligned:
                    text=text.replace('\\','').replace('{','').replace('}','').replace('\n',' ')
                    ass.append(f'Dialogue: 0,{stamp(a)},{stamp(b)},Default,,0,0,0,,{text}')
                continue
            lines=s['dialogue']; count=sum(len(x['text'].split()) for x in lines); cursor=i*8+.15
            for line in lines:
                duration=7.6*len(line['text'].split())/max(count,1); words=line['text'].split()
                for k,chunk in captions.chunks(words,caption_words,30 if j.get('retention_version')==1 else None):
                    a=cursor+duration*k/len(words); b=cursor+duration*(k+len(chunk))/len(words)
                    text=' '.join(chunk).replace('\\','').replace('{','').replace('}','').replace('\n',' ')
                    ass.append(f'Dialogue: 0,{stamp(a)},{stamp(b)},Default,,0,0,0,,{text}')
                cursor+=duration
        (d/'subtitles.ass').write_text('\n'.join(ass),'utf-8-sig')
        (d/'concat.txt').write_text('\n'.join(f"file 'normalized_{i:02}.mp4'" for i in range(len(j['scenes']))),'utf-8')
        run_command([ff,'-y','-f','concat','-safe','0','-i','concat.txt','-vf','ass=subtitles.ass','-af','loudnorm=I=-14:TP=-1.5:LRA=11','-c:v','libx264','-preset','fast','-crf','20','-c:a','aac','-movflags','+faststart','final.mp4'],cwd=d)
        if j.get('cover_file'):
            if not safe_child(d,j['cover_file']).is_file():raise ValueError('Couverture générée absente')
            cover_file=j['cover_file']
        else:
            cover_path=d/'cover.jpg';cover_file='cover.jpg'
            first=j['scenes'][0].get('image')
            if first: make_cover(safe_child(d,first),cover_path,j['script']['cover_title'])
            else:
                run_command([ff,'-y','-i',str(d/'final.mp4'),'-frames:v','1',str(d/'cover-frame.jpg')]);make_cover(d/'cover-frame.jpg',cover_path,j['script']['cover_title'])
        with LOCK:
            actual=job_by(id); actual['stage']='done'; actual['status']='done'; actual['final']=asset_url(actual,'final.mp4'); actual['cover']=asset_url(actual,cover_file); actual['qc']={'export':'Réussi : MP4 vertical 720 × 1280, audio normalisé.','subtitles':f'{aligned_count}/{len(j["scenes"])} scènes calées sur reconnaissance vocale ; autres timings estimés. Contrôle à l’écoute nécessaire.','lips':'Synchronisation labiale non vérifiée automatiquement.','duration':len(j['scenes'])*8}; event(actual,'Export terminé. Un contrôle visuel et audio reste nécessaire avant publication.'); save()
    except Exception as e:
        with LOCK:
            j=job_by(id); j['status']='attention'; event(j,'Montage : '+str(e)); save()
    finally: BUSY.discard(id)

def start_render(id):
    if id not in BUSY: BUSY.add(id); threading.Thread(target=render_job,args=(id,),daemon=True).start()

def make_cover(src,out,title):
    from PIL import Image, ImageOps, ImageDraw, ImageFont
    im=ImageOps.fit(Image.open(src).convert('RGB'),(720,1280)); draw=ImageDraw.Draw(im,'RGBA'); draw.rectangle((0,0,720,320),fill=(10,12,20,205))
    preferred=[]
    if re.search('[\u3040-\u30ff]',title): preferred=[r'C:/Windows/Fonts/YuGothB.ttc']
    elif re.search('[\uac00-\ud7af]',title): preferred=[r'C:/Windows/Fonts/malgunbd.ttf']
    elif re.search('[\u3400-\u9fff]',title): preferred=[r'C:/Windows/Fonts/msyhbd.ttc']
    font_path=next((p for p in preferred+[r'C:/Windows/Fonts/arialbd.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if pathlib.Path(p).exists()),None)
    font=ImageFont.truetype(font_path,58) if font_path else ImageFont.load_default()
    words=title.upper().split(); separator=' '
    if len(words)==1 and len(title)>12: words=list(title); separator=''
    lines=[]; line=''
    for word in words:
        trial=(line+separator+word).strip()
        if draw.textbbox((0,0),trial,font=font)[2]>640 and line: lines.append(line); line=word
        else: line=trial
    lines.append(line)
    for i,line in enumerate(lines[:3]): draw.text((360,55+i*76),line,font=font,anchor='mt',fill=(255,219,112,255),stroke_width=2,stroke_fill=(0,0,0,255))
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
            with LOCK:
                if path=='/api/state':
                    # Cross-origin fetches cannot read the pairing code.
                    if self.headers.get('Sec-Fetch-Site')=='cross-site': return self.send_json({'error':'Accès local requis'},403)
                    return self.send_json(public_state())
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
                    c['seen']=now()
                    for j in STATE['jobs']:
                        schedule(j)
                    for t in STATE['tasks']:
                        j=job_by(t['job'])
                        if t['status']!='queued' or j['status']!='running': continue
                        if not client_accepts(c,t): continue
                        if t['kind']=='flow_video':
                            if any(other['kind'] in ('flow_video','flow_collect') and other['status']=='claimed' for other in STATE['tasks']):continue
                            p=profile_by(t['profile']); cost=t['payload']['cost']
                            if not p or p['balance']<cost: t['status']='cancelled'; j['status']='waiting_credit'; continue
                            if t['payload'].get('dry_run'):
                                # A dry run never sends: nothing to reserve (P1-4).
                                t['status']='claimed'; t['client']=client; t['claimed']=now(); event(j,'Essai à blanc : préparation de '+t['slot']+' dans Flow, sans envoi.'); save(); return self.send_json(t)
                            p['balance']-=cost;t['reservation']={'profile':p['id'],'amount':cost,'refunded':False}; event(j,f"Réservation prudente de {cost} crédits sur {p['label']}. En cas d’échec, vérifier le solde réel avant de le réajuster.")
                        t['status']='claimed'; t['client']=client; t['claimed']=now(); event(j,'Connecteur en cours : '+t['slot']); save(); return self.send_json(t)
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
                        if any(x['job']==j['id'] and x['status'] in ('queued','claimed') for x in STATE['tasks']):continue
                        if t['slot']=='characters':missing=not any(x.get('file') for x in j['characters'])
                        elif t['slot'].startswith('character:'):
                            item=next((x for x in j['characters'] if x['id']==t['slot'].split(':')[1]),None);missing=item and not item.get('file')
                        elif t['slot']=='cover':missing=not j.get('cover_file')
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
                        if key in seen or j['status']!='attention' or j['stage']!='clips' or not client_accepts(c,t):continue
                        if any(x['job']==j['id'] and x['status'] in ('queued','claimed') for x in STATE['tasks']):continue
                        if not j['scenes'][int(t['slot'].split(':')[1])].get('clip'):rows.append(t);seen.add(key)
                    return self.send_json(rows[:3])
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
            bridge=path.startswith('/api/bridge/') and path!='/api/bridge/pair'
            if bridge and not self.auth_bridge(): return self.send_json({'error':'Appairage requis'},401)
            if not bridge and path!='/api/bridge/pair' and not self.origin_ok(): return self.send_json({'error':'Origine interdite'},403)
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
                    if not re.fullmatch(r'(?:cover|characters|character:[a-z][a-z0-9_]{0,24}|image:\d+|clip:\d+)',slot): raise ValueError('Emplacement média invalide')
                    if slot.startswith('character:') and not any(c['id']==slot.split(':')[1] for c in j['characters']): raise ValueError('Personnage inconnu')
                    if slot not in ('cover','characters') and not slot.startswith('character:') and int(slot.split(':')[1])>=len(j['scenes']): raise ValueError('Scène inconnue')
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
            with LOCK:
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
                    p.update(flow_url=url,flow_email=email,flow_client=c['id'],auto_enabled=True)
                    STATE['settings']['flow_auto']=True;save();return self.send_json({'ok':True,'profile':p['id']})
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
                    j=job_by(t['job']);message=str(b.get('message',''))[:240]
                    if j['status']!='paused' and message and message!=t.get('progress'):
                        t['progress']=message;event(j,message);save()
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
                    t={'id':uid(),'job':j['id'],'kind':'chat_collect','slot':'script','status':'claimed','client':client,'created':now(),'claimed':now(),'payload':{'provider':j['config']['provider'],'scene_count':j['config']['scene_count']}}
                    STATE['tasks'].append(t);j['status']='running';event(j,'Récupération de la réponse existante dans l’onglet choisi ; aucun nouveau prompt.');save();return self.send_json(t)
                if path=='/api/bridge/recover-video':
                    client=b.get('client');old=next((t for t in STATE['tasks'] if t['id']==b.get('previous_task') and t.get('client')==client and t['kind']=='flow_video' and t['status']=='failed'),None)
                    if not old or client not in STATE['clients'] or not client_accepts(STATE['clients'][client],old):raise ValueError('Clip non associé à ce navigateur Flow')
                    j=job_by(old['job'])
                    if j['status']!='attention' or j['stage']!='clips' or j['scenes'][int(old['slot'].split(':')[1])].get('clip') or any(t['job']==j['id'] and t['status'] in ('queued','claimed') for t in STATE['tasks']):raise ValueError('Production déjà reprise ou en pause')
                    t={'id':uid(),'job':j['id'],'kind':'flow_collect','profile':old['profile'],'slot':old['slot'],'status':'claimed','client':client,'created':now(),'claimed':now(),'payload':old['payload']}
                    STATE['tasks'].append(t);j['status']='running';event(j,'Récupération du clip Flow existant après correspondance exacte du prompt ; aucune génération ni réservation supplémentaire.');save();return self.send_json(t)
                if path=='/api/bridge/recover-media':
                    client=b.get('client');old=next((t for t in STATE['tasks'] if t['id']==b.get('previous_task') and t.get('client')==client and t['kind']=='chat_image' and t['status']=='failed'),None)
                    if not old or client not in STATE['clients'] or not client_accepts(STATE['clients'][client],old):raise ValueError('Image non associée à ce navigateur IA')
                    j=job_by(old['job'])
                    if j['status']!='attention' or j['stage'] not in ('characters','images','cover') or any(t['job']==j['id'] and t['status'] in ('queued','claimed') for t in STATE['tasks']):raise ValueError('Production déjà reprise ou en pause')
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
                    except Exception as e: t['status']='failed'; j=job_by(t['job']); j['status']='attention'; event(j,'Réponse invalide : '+str(e))
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
                elif path=='/api/flow-auto':
                    STATE['settings']['flow_auto']=bool(b.get('enabled'))
                elif path=='/api/job':
                    cfg={**STATE['settings'],**b.get('config',{})}; cfg['scene_count']=int(cfg['scene_count']); cfg['flow_cost']=int(cfg['flow_cost'])
                    cfg['flow_model']=b.get('config',{}).get('flow_model','gemini_omni_flash')
                    if cfg['flow_model'] not in ('gemini_omni_flash','veo_3_1_lite','veo_3_1_fast','veo_3_1_quality'):raise ValueError('Modèle Flow non pris en charge')
                    cfg['flow_resolution']='720p';cfg['clip_seconds']=8
                    cfg['flow_cost']=int(b.get('config',{}).get('flow_cost',{'gemini_omni_flash':12,'veo_3_1_lite':10,'veo_3_1_fast':20,'veo_3_1_quality':100}[cfg['flow_model']]))
                    if cfg['flow_cost'] not in {'gemini_omni_flash':(12,), 'veo_3_1_lite':(10,5), 'veo_3_1_fast':(20,10), 'veo_3_1_quality':(100,)}[cfg['flow_model']]:raise ValueError('Coût incompatible avec le modèle Flow choisi. Le coût réel sera vérifié avant tout envoi.')
                    cfg['language']=creation_language(cfg.get('language','Deutsch (de-DE)'))
                    cfg['review_script']=bool(b.get('config',{}).get('review_script',False))
                    cfg['dry_run']=bool(b.get('config',{}).get('dry_run',False))
                    requested_query=str(b.get('config',{}).get('query','')).strip()
                    # An omitted or untouched German default follows the chosen language.
                    cfg['query']=RESEARCH_QUERIES[cfg['language']] if not requested_query or requested_query in RESEARCH_QUERIES.values() else requested_query[:200]
                    if cfg['scene_count'] not in (3,4,6,8) or not 1<=cfg['flow_cost']<=100 or cfg['provider'] not in ('chatgpt','claude'): raise ValueError('Réglages invalides')
                    j={'id':uid(),'title':'Nouvel épisode','brief':str(b.get('brief',''))[:4000], 'config':cfg,'editorial_version':2,'retention_version':1,'hook_version':1,'quality_version':1,'cover_style':'family_poster_v3','character_sheet':1,'flow_profile':b.get('flow_profile'),'status':'running','stage':'research','created':now(),'updated':now(),'events':[],'candidates':[],'characters':[],'scenes':[]}; STATE['jobs'].insert(0,j); event(j,'Projet créé. Recherche préalable et comparaison de cinq concepts obligatoires.'); schedule(j)
                elif path.startswith('/api/job/'):
                    id=path.split('/')[-1]; j=job_by(id)
                    if not j: raise ValueError('Projet inconnu')
                    action=b.get('action')
                    if action=='pause': j['status']='paused'; event(j,'Pause demandée. Une génération déjà envoyée peut continuer chez le fournisseur.')
                    elif action=='resume':
                        active=next((t for t in STATE['tasks'] if t['job']==id and t['status']=='claimed'),None)
                        if active:
                            if b.get('flow_profile') and b['flow_profile']!=j.get('flow_profile'):raise ValueError('Un clip est déjà suivi : attendez sa récupération avant de changer de compte')
                            j['status']='running';event(j,'Suivi de la tâche en cours conservé ; aucun nouvel envoi.');save();return self.send_json(public_state())
                        if j.get('stage')=='clips' and uncertain_clip_tasks(j):raise ValueError(uncertain_message(j))
                        for t in STATE['tasks']:
                            if t['job']==id and t['status'] in ('queued','claimed'): t['status']='cancelled'
                        if b.get('flow_profile'): j['flow_profile']=b['flow_profile']
                        j['status']='running'; event(j,'Reprise demandée ; passage automatique limité aux comptes Flow enregistrés.' if STATE.get('settings',{}).get('flow_auto') else 'Reprise demandée ; compte Flow sélectionné conservé.'); schedule(j)
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
                            if t['job']==id and t['status']=='queued' and t['kind']=='flow_video':t['status']='cancelled'
                        event(j,'Essai à blanc activé : les clips seront préparés dans Flow sans être envoyés.' if j['config']['dry_run'] else 'Production réelle : les prochains clips seront envoyés à Flow et consommeront des crédits.')
                    elif action=='redo':
                        redo(j,b.get('slot',''),b.get('note',''),bool(b.get('include_clip')))
                    elif action=='edit_script':
                        edit_script(j,b.get('script',{}))
                    elif action=='approve_script':
                        if not review_pending(j) or j.get('stage')!='characters':raise ValueError('Aucune histoire en attente de validation')
                        j['script_approved']=now();j['status']='running';event(j,'Histoire validée par le propriétaire : création des images lancée.');schedule(j)
                    elif action=='provider':
                        if b.get('provider') not in ('chatgpt','claude'): raise ValueError('IA inconnue')
                        j['config']['provider']=b['provider']; event(j,'IA de scénario modifiée ; médias conservés.')
                    else: raise ValueError('Action inconnue')
                else: return self.send_json({'error':'Route inconnue'},404)
                save(); self.send_json(public_state())
        except Exception as e: self.send_json({'error':str(e)},400)

def recover_after_restart():
    with LOCK:
        # Never automatically resend an ambiguous generation after a restart.
        for t in STATE['tasks']:
            if t['status']=='claimed':
                t['status']='failed'; j=job_by(t['job']); j['status']='attention'; event(j,'Redémarrage : génération précédente à vérifier avant de réessayer.')
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

if __name__=='__main__':
    recover_after_restart()
    print(f'FruchtDrama Studio : http://127.0.0.1:{PORT}',flush=True)
    threading.Thread(target=flow_dispatch_loop,daemon=True).start()
    http.server.ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
