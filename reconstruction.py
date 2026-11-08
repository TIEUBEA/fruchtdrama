"""Rebuild a user-supplied video from its approved local storyboard, without research."""
import copy
import json
import pathlib
import re
import shutil


def load(data, key):
    if not re.fullmatch(r'[a-z0-9_-]{1,60}', str(key)):
        raise ValueError('Référence invalide')
    folder = pathlib.Path(data) / 'reference-presets' / key
    manifest = json.loads((folder / 'manifest.json').read_text('utf-8'))
    if manifest.get('source_kind') != 'user_supplied_video':
        raise ValueError('Une vidéo fournie par le propriétaire est requise')
    script = manifest['script']
    ids = {c['id'] for c in script['characters']}
    if not 1 <= len(ids) <= 10 or len(ids) != len(script['characters']):
        raise ValueError('Distribution invalide')
    if not 1 <= len(script['scenes']) <= 40:
        raise ValueError('Découpage invalide')
    for scene in script['scenes']:
        if manifest.get('generation_mode') == 'description_only':
            if not str(scene.get('image_prompt','')).strip():
                raise ValueError('Description visuelle manquante')
        else:
            image = scene['reference_image']
            if not re.fullmatch(r'[a-zA-Z0-9_-]+\.(?:png|jpg)', image) or not (folder / image).is_file():
                raise ValueError('Image de référence absente ou invalide')
        if not 0 < scene['source_end'] - scene['source_start'] <= 8.1:
            raise ValueError('Plan source trop long : découpez-le sans perdre les répliques')
        if not set(scene['characters']).issubset(ids):
            raise ValueError('Personnage inconnu')
        for line in scene['dialogue']:
            if line['speaker'] not in scene['characters'] or not str(line['text']).strip():
                raise ValueError('Locuteur ou dialogue invalide')
    return folder, manifest


def available(data):
    rows = []
    root = pathlib.Path(data) / 'reference-presets'
    if root.is_dir():
        for folder in sorted(root.iterdir()):
            if not folder.is_dir():
                continue
            try:
                _, m = load(data, folder.name)
                rows.append({'id': folder.name, 'title': m['script']['title'],
                             'language': m['language'], 'scenes': len(m['script']['scenes']),
                             'source_seconds': m['source_seconds']})
            except (OSError, KeyError, ValueError, TypeError):
                continue
    return rows


def create(data, state, key, job_id, stamp, profile=None):
    folder, manifest = load(data, key)
    if manifest.get('depends_on'):
        parent=next((j for j in state['jobs'] if j.get('reference_preset')==manifest['depends_on']),None)
        if not parent or parent.get('status')!='done':
            raise ValueError('Terminez et regardez la partie 1 avant de préparer la partie 2')
    if profile and not any(p['id'] == profile for p in state['profiles']):
        raise ValueError('Compte Flow inconnu')
    # Idempotent preparation: repeated clicks must not create duplicate paid work.
    existing = next((j for j in state['jobs'] if j.get('reference_preset') == key), None)
    if existing:
        if manifest.get('generation_mode')=='description_only' and not existing['config'].get('generated_from_description'):
            if any(t['job']==existing['id'] and t['status'] in ('queued','claimed') for t in state.get('tasks',[])):
                raise ValueError('Une tâche de ce projet est en cours ; attendez avant de remplacer les références')
            if any(s.get('clip') for s in existing['scenes']):
                raise ValueError('Des clips existent déjà : conservez-les avant de changer le mode')
            script=copy.deepcopy(manifest['script'])
            for scene in script['scenes']:
                for field in ('image','reference_image','reference_time'):
                    scene.pop(field,None)
            for character in script['characters']:
                character.pop('file',None)
            existing.update(script=script,characters=script['characters'],scenes=script['scenes'],
                            title=script['title'],reconstruction=copy.deepcopy(manifest['source']),
                            stage='characters',status='paused',character_sheet=1,updated=stamp)
            existing.pop('character_sheet_file',None)
            existing['config']['generated_from_description']=True
            existing['config']['generation_mode']='description_only'
            existing['config']['scene_count']=len(script['scenes'])
            (pathlib.Path(data)/'jobs'/existing['id']/'scenario.json').write_text(json.dumps(script,ensure_ascii=False,indent=2),'utf-8')
        return existing, False
    script = copy.deepcopy(manifest['script'])
    output = pathlib.Path(data) / 'jobs' / job_id
    output.mkdir(parents=True, exist_ok=False)
    description_only=manifest.get('generation_mode')=='description_only'
    for scene in script['scenes']:
        if description_only:
            for field in ('image','reference_image','reference_time'):
                scene.pop(field,None)
        else:
            image = scene['reference_image']
            shutil.copy2(folder / image, output / image)
            scene['image'] = image
    # Character designs come from supplied boards; no new casting or sheets are paid for.
    for character in script['characters']:
        if description_only:
            character.pop('file',None)
        else:
            scene = next(s for s in script['scenes'] if character['id'] in s['characters'])
            character['file'] = scene['image']
    config = copy.deepcopy(state.get('settings', {}))
    config.update(language=manifest['language'], video_engine='flow', clip_seconds=8,
                  scene_count=len(script['scenes']), niche='Fruits',
                  narrative_model='supplied_video_reconstruction', smooth_transitions=False,
                  dynamic=False, hook_overlay=False, karaoke=True,
                  flow_model='veo_3_1_lite', flow_resolution='720p', flow_cost=10,
                  generated_from_description=description_only,
                  generation_mode='description_only' if description_only else 'source_boards')
    job = {'id': job_id, 'title': script['title'], 'brief': 'Reconstruction fidèle de la vidéo fournie, en allemand.',
           'reference_preset': key, 'reconstruction': copy.deepcopy(manifest['source']),
           'config': config, 'script': script, 'characters': script['characters'], 'scenes': script['scenes'],
           'stage': 'characters' if description_only else 'clips', 'status': 'paused', 'created': stamp, 'updated': stamp,
           'events': [], 'candidates': [], 'flow_profile': profile,
           'quality_version': 1, 'retention_version': 1}
    if description_only:job['character_sheet']=1
    (output / 'scenario.json').write_text(json.dumps(script, ensure_ascii=False, indent=2), 'utf-8')
    (output / 'reference-source.json').write_text(json.dumps(manifest['source'], ensure_ascii=False, indent=2), 'utf-8')
    state['jobs'].insert(0, job)
    return job, True


def duration(scene, speech, full_length):
    """Keep reference rhythm where possible, but never knowingly cut translated speech."""
    target = min(full_length, scene['source_end'] - scene['source_start'])
    if not scene.get('dialogue'):
        return target
    words = speech.get('words', []) if isinstance(speech, dict) else []
    if not words:
        return full_length  # no timing evidence: retain the complete generated clip
    end = max(float(w.get('end', 0)) for w in words)
    return min(full_length, max(target, end + .2))


def instruction(job, index):
    scene = job['scenes'][index]
    dialogue = '\n'.join(x['speaker'] + ': ' + x['text'] for x in scene['dialogue'])
    base=(
        '\nTEXT-DESCRIBED VIDEO RECONSTRUCTION. The attached image is newly generated from the '
        'written storyboard, not a capture of the source video. Preserve its cast and setting. '
        'The written character designs and shot description determine identity, wardrobe and action. '
        'No social-media logos, watermark, player controls or burned-in captions. '
    ) if job['config'].get('generated_from_description') else (
        '\nUSER-SUPPLIED VIDEO RECONSTRUCTION. The attached source frame is authoritative for '
        'the exact cast, fruit shapes, clothing, set, props, camera angle and screen positions. '
    )
    return base + (
        'Recreate this shot, not a new story. Keep the original shot order. '
        'Preserve intentional costume changes explicitly described in the written storyboard. '
        'Render a clean animated scene, not a frozen screenshot. Source captions and player '
        'controls are reference overlays, not objects in the scene; do not turn them into scenery. '
        f'Only German speech. Deliver all specified dialogue naturally within approximately '
        f'{scene["source_end"]-scene["source_start"]:.2f} seconds if possible; never truncate words. '
        'Only the named speaker moves their lips. No invented lines or narrator. '
        + ('This is a silent action shot: no speech.\n' if not dialogue else 'Exact German dialogue:\n' + dialogue + '\n')
    )


def sheet_prompt(job):
    cast='\n'.join(c['id']+': '+c['appearance'] for c in job['characters'])
    return ('Create an original standalone image from this text. Draw a cinematic 3D cast lineup '
            'on a neutral off-white background, with each fictional character shown once, full body '
            'in a front three-quarter view. Portrait composition, balanced spacing and sharp faces. '
            'Use believable human anatomy, expressive sculpted fruit faces, realistic clothing '
            "and warm studio lighting. Use each character's default outfit, the first outfit listed. "
            'Wardrobe variants belong to later scenes. Respect adult and child proportions. '
            'Plain unlettered background; no names, words, logos, watermark or interface. '
            'No source screenshot or captured frame may be copied into this image. '
            'Generate the finished image now.\nCHARACTERS TO DRAW:\n'+cast)


def image_prompt(job,index):
    scene=job['scenes'][index]
    cast='\n'.join(c['id']+': '+c['appearance'] for c in job['characters'] if c['id'] in scene['characters'])
    return ('Generate a completely NEW cinematic 3D scene from the written shot description. '
            'Only the newly generated cast sheet may be attached. No source-video capture is used. '
            'Near-photoreal settings, believable human anatomy, expressive fruit faces as described. '
            'Match the described composition, wardrobe, prop positions and lighting precisely. '
            'The scene-specific wardrobe description overrides the default outfit on the cast sheet, '
            'while face, age, body, fruit shape and leaf remain identical. '
            'No text, logos, watermark, captions, interface, play icon or poster headline. '
            'Portrait 9:16, at least 1024x1536, detailed natural materials.\nCAST:\n'+cast+
            '\nSHOT:\n'+scene['image_prompt'])
