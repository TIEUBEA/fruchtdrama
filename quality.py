"""Evidence-based clip QC. No regeneration and no paid API calls."""
import difflib, hashlib, json, pathlib, re, shutil, subprocess, sys, unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import engines

# Owner decision (02/11/2026): automatic continuation only with >= 85 % speech match per clip,
# no technical defect and a visual review passing everywhere (uncertain = stop).
MIN_MATCH=.85
THRESHOLDS={'speech_match_min':MIN_MATCH,'technical':'aucun défaut','visual':'pass partout (uncertain = arrêt)'}

def decision(report,visual_issues=()):
    """Automatic decision recorded in the report, with its reasons."""
    reasons=[*report.get('hard_errors',[]),*report.get('warnings',[]),*[x.get('detail','') for x in visual_issues]]
    return {'decision':'continue' if not reasons else 'review','reasons':reasons[:20],'thresholds':THRESHOLDS}

def words(text):
    return re.findall(r"[^\W_]+",unicodedata.normalize('NFKC',str(text)).casefold(),re.UNICODE)

def fingerprint(j,folder):
    h=hashlib.sha256(json.dumps({'scenes':j['scenes'],'characters':j['characters'],'language':j['config'].get('language')},sort_keys=True,ensure_ascii=False).encode())
    for scene in j['scenes']:
        for key in ('clip','image'):
            name=scene.get(key)
            if name:
                file=(folder/name).resolve()
                if folder.resolve() not in file.parents:raise ValueError('Média hors production')
                with file.open('rb') as f:
                    for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def compare(expected,transcript,language,probability):
    a,b=words(expected),words(transcript)
    ratio=difflib.SequenceMatcher(None,a,b,autojunk=False).ratio()
    issues=[]
    if not b:issues.append('Aucune parole reconnue : écoute nécessaire.')
    elif ratio<MIN_MATCH:issues.append(f'Les paroles reconnues correspondent à {round(ratio*100)} % du scénario (seuil {round(MIN_MATCH*100)} %) ; vérifier les répliques avant le montage.')
    if language and probability>=.8 and language not in ('de','fr','en','es','pt'):issues.append('La langue détectée ne correspond à aucune langue de création autorisée.')
    return round(ratio,3),issues

MIN_CLIP,MAX_CLIP=2.0,16.0

def technical(path,expected=(7.5,8.5),horizontal=False):
    p=subprocess.run([shutil.which('ffprobe') or 'ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height,duration,start_time','-of','json',str(path)],capture_output=True,text=True,timeout=30)
    if p.returncode:raise ValueError('Clip illisible par ffprobe')
    data=json.loads(p.stdout);streams=data.get('streams',[]);video=next((x for x in streams if x['codec_type']=='video'),{})
    errors=[];duration=float(data.get('format',{}).get('duration',0))
    # 0.1.99: a clip replaced by hand (10 s instead of 8 s) never stops the episode; only an unusable length does.
    notes=[]
    if not MIN_CLIP<=duration<=MAX_CLIP:errors.append(f'Durée inutilisable ({duration:.1f} s ; {MIN_CLIP:g} à {MAX_CLIP:g} s acceptées).')
    elif not expected[0]<=duration<=expected[1]:notes.append(f'Durée {duration:.1f} s au lieu de {expected[0]:g} à {expected[1]:g} s : clip gardé tel quel au montage.')
    if (video.get('height',0)>video.get('width',0))==horizontal or not video:errors.append('Vidéo absente ou mauvaise orientation ('+('horizontale' if horizontal else 'verticale')+' attendue).')
    audio=next((x for x in streams if x['codec_type']=='audio'),None)
    if not audio:errors.append('Piste audio absente.')
    if audio and abs(float(audio.get('start_time',0))-float(video.get('start_time',0)))>.2:errors.append('Décalage initial audio/vidéo supérieur à 200 ms : vérifier la synchronisation.')
    if audio and audio.get('duration') and float(audio['duration'])<duration-.5:errors.append('Piste audio plus courte que la vidéo : risque de décalage ou coupure.')
    scan=subprocess.run([shutil.which('ffmpeg') or 'ffmpeg','-hide_banner','-i',str(path),'-af','silencedetect=noise=-45dB:d=1','-f','null','-'],capture_output=True,text=True,timeout=90)
    if scan.returncode:errors.append('Erreur de décodage audio/vidéo.')
    if re.search(r'silence_start: 0(?:\.0+)?\s',scan.stderr) and any(float(x)>duration-.3 for x in re.findall(r'silence_duration: ([0-9.]+)',scan.stderr)):errors.append('Audio pratiquement entièrement silencieux.')
    return {'duration':duration,'hard_errors':errors,'notes':notes}

def transcribe_all(j,folder):
    sys.path.insert(0,str(ROOT/'.qc-runtime'))
    from faster_whisper import WhisperModel
    model=WhisperModel('base',download_root=str(ROOT/'.qc-models'),device='cpu',compute_type='int8',cpu_threads=4,local_files_only=True)
    output=[];target={'Deutsch (de-DE)':'de','Français (fr-FR)':'fr','English (en-US)':'en','Español (es-ES)':'es','Português (pt-BR)':'pt'}[j['config']['language']]
    for scene in j['scenes']:
        segments,info=model.transcribe(str(folder/scene['clip']),beam_size=5,word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
        segments=list(segments);tokens=[{'word':w.word.strip(),'start':round(w.start,3),'end':round(w.end,3),'probability':round(w.probability,3)} for seg in segments for w in (seg.words or [])]
        text=' '.join(seg.text.strip() for seg in segments)
        score,issues=compare(' '.join(x['text'] for x in scene['dialogue']),text,info.language,info.language_probability)
        if info.language!=target and info.language_probability>=.8:issues.append('Langue détectée différente de la langue demandée.')
        if tokens and sum(w['probability'] for w in tokens)/len(tokens)<.65:issues.append('Reconnaissance vocale incertaine : écoute nécessaire.')
        output.append({'text':text,'words':tokens,'match':score,'language':info.language,'language_probability':round(info.language_probability,3),'warnings':issues})
    return output

def analyse(j,folder):
    report={'fingerprint':fingerprint(j,folder),'hard_errors':[],'warnings':[],'clips':[],
            'limits':['La transcription peut se tromper, surtout sur les noms propres.','Identité du locuteur et synchronisation des lèvres non certifiées automatiquement.']}
    for i,scene in enumerate(j['scenes']):
        result=technical(folder/scene['clip'],engines.clip_range(j,scene),(j.get('config') or {}).get('format')=='horizontal');report['clips'].append(result)
        report['hard_errors'] += [f"Scène {i+1} : {x}" for x in result['hard_errors']]
        report.setdefault('notes',[]).extend(f"Scène {i+1} : {x}" for x in result.get('notes',[]))
        # Actual sampled frames, never the generated input still presented as clip evidence.
        sheet=f'quality-scene-{i:02}.jpg'
        run=subprocess.run([shutil.which('ffmpeg') or 'ffmpeg','-v','error','-y','-i',str(folder/scene['clip']),'-vf','fps=1/2,scale=288:-1,tile=4x1','-frames:v','1',str(folder/sheet)],capture_output=True,text=True,timeout=60)
        if run.returncode:report['hard_errors'].append(f'Scène {i+1} : extraction des images de contrôle impossible.')
        else:result['sheet']=sheet
    if not report['hard_errors']:
        try:
            speech=transcribe_all(j,folder)
            for i,result in enumerate(speech):
                # 0.1.101 (owner 06/11/2026: « annule cette vérification »): the transcription only places the subtitles;
                # a gap with the script is never a warning any more (it was mostly transcription errors).
                report['clips'][i]['speech']=result
        except Exception as e:
            report.setdefault('notes',[]).append('Transcription locale indisponible : '+type(e).__name__+'. Sous-titres placés sans elle.')
    report['status']='review_required' if report['hard_errors'] or report['warnings'] else 'pass'
    return report

def caption_events(scene,speech,offset,max_words=4,max_chars=30,length=8,karaoke=False):
    """Anchor script words to ASR matches, interpolating unmatched words explicitly.

    karaoke=True (P4-2): each caption carries ASS \\kf tags so every word lights up when it is spoken."""
    if not speech or speech.get('match',0)<.8:return None
    import captions
    original=' '.join(x['text'] for x in scene['dialogue']).split()
    heard=speech.get('words',[])
    expected_tokens=[];owners=[];heard_tokens=[];heard_owners=[]
    for i,w in enumerate(original):
        tokens=words(w);expected_tokens+=tokens;owners += [i]*len(tokens)
    for i,w in enumerate(heard):
        tokens=words(w['word']);heard_tokens+=tokens;heard_owners += [i]*len(tokens)
    anchors={}
    for a,b,size in difflib.SequenceMatcher(None,expected_tokens,heard_tokens,autojunk=False).get_matching_blocks():
        for k in range(size):
            i=owners[a+k];word=heard[heard_owners[b+k]]
            start,end=float(word['start']),float(word['end'])
            if not 0<=start<end<=length:return None
            if i in anchors:start,end=min(start,anchors[i][0]),max(end,anchors[i][1])
            anchors[i]=(start,end)
    if not original or len(anchors)/len(original)<.8:return None
    # Unmatched words use the gap between adjacent reliable words, not an invented voice check.
    spans=[]
    for i in range(len(original)):
        if i in anchors:spans.append(anchors[i]);continue
        previous=max((x for x in anchors if x<i),default=-1)
        following=min((x for x in anchors if x>i),default=len(original))
        left=anchors[previous][1] if previous>=0 else 0
        right=anchors[following][0] if following<len(original) else length-.1
        if right<=left:return None
        step=(right-left)/(following-previous-1)
        spans.append((left+step*(i-previous-1),left+step*(i-previous)))
    if any(spans[i][0]<spans[i-1][1]-.05 for i in range(1,len(spans))):return None
    if not karaoke:
        return [(offset+spans[start][0],offset+spans[start+len(chunk)-1][1],' '.join(chunk))
                for start,chunk in captions.chunks(original,max_words,max_chars)]
    clean=lambda w:re.sub(r'[\\{}\n]','',w)
    events=[]
    for start,chunk in captions.chunks(original,max_words,max_chars):
        tagged=[];cursor=spans[start][0]
        for k,word in enumerate(chunk):
            a,b=spans[start+k]
            pause='{\\k%d}'%round((a-cursor)*100) if a>cursor+.01 else ''  # silence before the word
            tagged.append(pause+'{\\kf%d}%s'%(max(1,round((b-a)*100)),clean(word)));cursor=b
        events.append((offset+spans[start][0],offset+spans[start+len(chunk)-1][1],' '.join(tagged)))
    return events


def visual_prompt(j):
    return """Review the attached ACTUAL VIDEO FRAME CONTACT SHEETS against the script and character references. Do not generate an image. Output JSON only, with exact production_id and generation_task_id supplied in this request, and quality_review containing scenes (one per clip, index starting at 0, status pass/issue/uncertain, detail), plus continuity (status pass/issue/uncertain, detail). Every detail must state observable evidence or a limitation. Attachments are ordered: existing character-reference images first, then one contact sheet per scene in script order (quality-scene-00.jpg is scene index 0). You have sampled stills at approximately 0,2,4,6 seconds per clip, NOT continuous video or audio. Never claim to hear voices, verify lip sync, identify a speaker by voice, or certify unobserved movements. Check fruit identity, age, clothing, setting, important props, progression matching the script and contradictions between clips. Ignore typography on reference images. Use uncertain when the supplied evidence cannot settle a material question. Do not treat a deliberate story transition or change of setting as an error. Do not mark limitations inherent to still frames alone as scene failures. No overall perfection score.
Script and cast: """+json.dumps({'title':j['title'],'characters':j['characters'],'scenes':j['scenes']},ensure_ascii=False)

def validate_visual(value,j,task):
    if value.get('production_id')!=j['id'] or value.get('generation_task_id')!=task:raise ValueError('Rapport qualité non associé à cette tâche')
    q=value.get('quality_review',{});scenes=q.get('scenes',[])
    if len(scenes)!=len(j['scenes']) or [x.get('index') for x in scenes]!=list(range(len(j['scenes']))):raise ValueError('Rapport visuel incomplet ou scènes désordonnées')
    for item in [*scenes,q.get('continuity',{})]:
        if item.get('status') not in ('pass','issue','uncertain') or not isinstance(item.get('detail'),str) or not item['detail'].strip():raise ValueError('Conclusion qualité invalide')
    return q

if __name__=='__main__':
    config=pathlib.Path(sys.argv[1]).resolve();job=json.loads(config.read_text(encoding='utf-8'))
    result=analyse(job,config.parent)
    (config.parent/'quality-local.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
