from unittest.mock import patch
import copy, importlib.util, os, pathlib, tempfile, unittest, threading, urllib.request, urllib.error, json, subprocess, shutil

TEMP=tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA']=TEMP.name
SPEC=importlib.util.spec_from_file_location('studio',pathlib.Path(__file__).parents[1]/'server.py')
s=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
from tests import accounts_ready; accounts_ready.install(s)  # 0.1.91: accounts ready before starting

def script(n=4):
    return {'title':'Omas Reise','cover_title':'MUSS OMA GEHEN?','description':'Eine originelle KI-Geschichte.','characters':[{'id':'orange','name':'Oma','appearance':'Orange, cremefarbener Cardigan','voice':'Warme ältere Stimme','image_prompt':'Figurenreferenz, Orange'}], 'scenes':[{'characters':['orange'],'meaning':'Ein Koffer steht neben Oma.','image_prompt':'Oma mit Koffer','video_prompt':'Ein ruhiger Plan.','dialogue':[{'speaker':'orange','text':'Wir fahren heute gemeinsam ans Meer.'}]} for _ in range(n)]}

def job():
    j={'id':s.uid(),'stage':'research','status':'running','events':[],'config':{'scene_count':4,'provider':'chatgpt','flow_cost':10,'query':'früchte deutsch'},'brief':'Omas Reise','characters':[],'scenes':[],'candidates':[],'flow_profile':None}
    s.STATE['jobs'].append(j);return j

def scene_images(j):
    from PIL import Image
    for i,scene in enumerate(j['scenes']):
        name=f'scene{i}.png';Image.new('RGB',(32,64),(i*50,100,200)).save(s.job_dir(j)/name);scene['image']=name

class StudioTests(unittest.TestCase):
    def test_review_progress_names_the_actual_control(self):
        raw='Lecture du scénario : {"hasJob":true,"hasTask":true}'
        self.assertIn('miniature',s.readable_progress(raw,'cover_review'))
        self.assertIn('clips',s.readable_progress(raw,'quality_review'))
        self.assertIn('planches',s.readable_progress(raw,'board_review'))
        self.assertNotIn('scénario',s.readable_progress(raw,'cover_review'))
    def test_render_stops_cleanly_if_episode_was_removed(self):
        s.STATE=s.fresh();s.BUSY.add('removed')
        s.render_job('removed')
        self.assertNotIn('removed',s.BUSY)
    def test_render_error_does_not_crash_if_episode_disappeared(self):
        s.STATE=s.fresh();episode=job();s.BUSY.add(episode['id'])
        with patch.object(s,'job_by',side_effect=[episode,None]),patch.object(s.shutil,'which',return_value=None):
            s.render_job(episode['id'])
        self.assertNotIn(episode['id'],s.BUSY)
    def setUp(self):
        s.STATE=s.fresh();s.DOWNLOADS_ROOT=pathlib.Path(TEMP.name)/'downloads';s.DOWNLOADS_ROOT.mkdir(exist_ok=True)
    def test_omni_clip_budget_and_model_are_passed_to_the_extension(self):
        j=job();s.store_script(j,script());s.STATE['tasks']=[];j['stage']='clips'
        j['config'].update(flow_model='gemini_omni_flash',flow_resolution='720p',flow_cost=12)
        s.STATE['profiles'].append({'id':'flow','label':'Flow','balance':12})
        j['flow_profile']='flow';scene_images(j);s.schedule(j)
        task=s.STATE['tasks'][0]
        self.assertEqual(task['payload']['model'],'gemini_omni_flash')
        self.assertEqual(task['payload']['resolution'],'720p');self.assertEqual(task['payload']['seconds'],8)
        self.assertEqual(task['payload']['cost'],12)
        s.STATE['tasks']=[];s.STATE['profiles'][0]['balance']=11;s.schedule(j)
        self.assertEqual(j['status'],'waiting_credit');self.assertEqual(s.STATE['tasks'],[])

    def test_new_cover_style_adds_one_image_task_after_clips(self):
        j=job();s.store_script(j,script());s.STATE['tasks']=[];j['cover_style']='dramatic_v2';j['stage']='clips'
        for i,scene in enumerate(j['scenes']):scene.update(image=f'scene{i}.png',clip=f'clip{i}.mp4')
        s.schedule(j);s.schedule(j)
        self.assertEqual(j['stage'],'cover');self.assertEqual(len(s.STATE['tasks']),1)
        t=s.STATE['tasks'][0];self.assertEqual(t['slot'],'cover');self.assertEqual(t['kind'],'chat_image')
        self.assertEqual(t['payload']['attachments'][0],s.asset_url(j,'scene0.png'))
        self.assertIn('ONLY the approved layout/style template',t['payload']['prompt'])
        self.assertIn('3 to 5 words',t['payload']['prompt']);self.assertIn('Deutsch',t['payload']['prompt'])
    def test_shared_family_poster_uses_own_scene_without_private_style_capture(self):
        j=job();s.store_script(j,script());s.STATE['tasks']=[];j['stage']='clips';j['cover_style']='family_poster_v3'
        for scene in j['scenes']:scene.update(image='scene.png',clip='existing.mp4')
        before=copy.deepcopy(j['scenes'])
        with patch.object(s,'ROOT',pathlib.Path(TEMP.name)/'shared-distribution'):
            s.schedule(j)
        self.assertEqual(j['stage'],'cover');self.assertEqual(j['scenes'],before)
        task=s.STATE['tasks'][0];prompt=task['payload']['prompt']
        self.assertIn('PHONE SCREENSHOT OF A GRID',prompt)
        self.assertIn('display serif',prompt);self.assertIn('UPPER',prompt)
        self.assertIn('Deutsch',prompt);self.assertEqual(len(task['payload']['attachments']),1)
        self.assertFalse(any('cover-reference-grid' in url for url in task['payload']['attachments']))
        j['cover_style']='dramatic_v2'
        self.assertIn('lower middle BELOW faces',s.cover_prompt(j))

    def test_cover_result_keeps_existing_clips_and_starts_montage(self):
        from PIL import Image
        j=job();s.store_script(j,script());s.STATE['tasks']=[];j['cover_style']='dramatic_v2';j['stage']='cover';scene_images(j);j['config']['cover_controls']='none'
        for i,scene in enumerate(j['scenes']):scene['clip']=f'clip{i}.mp4'
        original=copy.deepcopy(j['scenes']);Image.new('RGB',(64,128),'yellow').save(s.job_dir(j)/'generated-cover.png')
        t={'id':s.uid(),'job':j['id'],'slot':'cover','kind':'chat_image','status':'claimed'};s.STATE['tasks'].append(t)
        previous=s.start_render;s.start_render=lambda id:None
        try:s.accept_task_result(t,{'ok':True,'file':'generated-cover.png'})
        finally:s.start_render=previous
        self.assertEqual(j['cover_file'],'generated-cover.png');self.assertEqual(j['scenes'],original)
        self.assertEqual(j['stage'],'edit');self.assertEqual(j['status'],'rendering');self.assertEqual(t['status'],'done')
    def test_legacy_job_does_not_generate_new_cover(self):
        j=job();s.store_script(j,script());s.STATE['tasks']=[];j['stage']='clips'
        for scene in j['scenes']:scene['clip']='existing.mp4'
        previous=s.start_render;s.start_render=lambda id:None
        try:s.schedule(j)
        finally:s.start_render=previous
        self.assertEqual(j['stage'],'edit');self.assertEqual(s.STATE['tasks'],[])

    def test_downloaded_clip_import_is_validated_and_idempotent(self):
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):self.skipTest('ffmpeg required')
        j=job();source=s.DOWNLOADS_ROOT/(s.uid()+'.mp4')
        subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=red:s=320x568:r=1','-f','lavfi','-i','anullsrc=r=16000:cl=mono','-t','8','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac',str(source)],check=True,capture_output=True)
        t={'slot':'clip:1','claimed':s.now()};info={'download_id':7,'filename':str(source),'size':source.stat().st_size}
        result=s.import_browser_download(j,t,info);self.assertTrue((s.job_dir(j)/result).exists());self.assertTrue(source.exists())
        self.assertEqual(s.import_browser_download(j,t,info),result)
        with self.assertRaises(ValueError):s.import_browser_download(j,t,{**info,'download_id':8})
    def test_download_import_cannot_read_outside_downloads(self):
        j=job();source=pathlib.Path(TEMP.name)/'private.mp4';source.write_bytes(b'private')
        with self.assertRaisesRegex(ValueError,'Téléchargements'):s.import_browser_download(j,{'slot':'clip:0','claimed':s.now()},{'download_id':1,'filename':str(source),'size':7})
    def test_download_import_rejects_old_files_and_invalid_video(self):
        j=job();source=s.DOWNLOADS_ROOT/(s.uid()+'.mp4');source.write_bytes(b'not a video')
        info={'download_id':7,'filename':str(source),'size':source.stat().st_size};t={'slot':'clip:1','claimed':s.now()}
        os.utime(source,(1,1))
        with self.assertRaisesRegex(ValueError,'antérieur'):s.import_browser_download(j,t,info)
        os.utime(source,None)
        with self.assertRaisesRegex(ValueError,'vidéo lisible'):s.import_browser_download(j,t,info)
    def test_flow_reference_is_small_jpeg_and_keeps_original(self):
        from PIL import Image
        j=job();d=s.job_dir(j);source=d/'source.png'
        Image.new('RGBA',(941,1672),(255,0,0,128)).save(source);original=source.read_bytes()
        name=s.flow_reference(j,'source.png');self.assertEqual(s.flow_reference(j,'source.png'),name)
        with Image.open(d/name) as image:
            self.assertEqual(image.format,'JPEG');self.assertEqual(image.mode,'RGB');self.assertLessEqual(max(image.size),1280)
        self.assertEqual(source.read_bytes(),original)
    def test_scene_reference_rejected_even_with_different_encoding(self):
        from PIL import Image
        j=job();s.store_script(j,script());j['status']='paused'
        d=s.job_dir(j);Image.new('RGB',(32,64),'red').save(d/'ref.png')
        Image.new('RGBA',(32,64),'red').save(d/'copy.png');j['characters'][0]['file']='ref.png'
        t={'job':j['id'],'slot':'image:0','status':'claimed'}
        with self.assertRaisesRegex(ValueError,'copie exacte'):s.accept_task_result(t,{'ok':True,'file':'copy.png'})
        self.assertNotIn('image',j['scenes'][0])
    def test_repair_keeps_files_and_script_and_marks_images_missing(self):
        from PIL import Image
        j=job();s.store_script(j,script());j['stage']='clips';d=s.job_dir(j)
        Image.new('RGB',(32,64),'red').save(d/'ref.png');j['characters'][0]['file']='ref.png'
        for scene in j['scenes']:scene['image']='ref.png'
        original=copy.deepcopy(j['script']);self.assertEqual(s.repair_duplicate_scenes(j),4)
        self.assertEqual(j['script'],original);self.assertTrue((d/'ref.png').exists())
        self.assertEqual(j['stage'],'images');self.assertEqual(j['status'],'attention')
        self.assertTrue(list(d.glob('repair_backup_*.json')))
        self.assertEqual(s.repair_duplicate_scenes(j),0)
    def test_original_scene_accepted(self):
        from PIL import Image
        j=job();s.store_script(j,script());j['status']='paused';d=s.job_dir(j)
        Image.new('RGB',(32,64),'red').save(d/'ref.png');j['characters'][0]['file']='ref.png'
        Image.new('RGB',(32,64),'blue').save(d/'scene.png')
        s.accept_task_result({'job':j['id'],'slot':'image:0','status':'claimed'},{'ok':True,'file':'scene.png'})
        self.assertEqual(j['scenes'][0]['image'],'scene.png');self.assertEqual(j['status'],'paused')
    def test_path_traversal_blocked(self):
        with self.assertRaises(ValueError): s.safe_child(pathlib.Path(TEMP.name),'../secret')
    def test_counter_is_not_relabelled_as_views(self):
        r=s.rank_candidates([{'url':'https://www.tiktok.com/@a/video/123','signal':3000}])[0]
        self.assertIsNone(r['views']);self.assertEqual(r['basis'],'compteur affiché non identifié')
    def test_rejects_foreign_reference_and_deduplicates(self):
        r=s.rank_candidates([{'url':'https://evil.example/@a/video/123','views':9e9},{'url':'https://www.tiktok.com/@a/video/123','views':10},{'url':'https://www.tiktok.com/@a/video/123?tracking=1','views':20}])
        self.assertEqual(len(r),1);self.assertEqual(r[0]['views'],20)
    def test_no_viral_selection_without_enough_measurements(self):
        j=job();s.apply_research(j,[{'url':'https://www.tiktok.com/@a/video/123'}]);self.assertEqual(j['status'],'waiting_research');self.assertNotIn('selected',j)
    def test_auto_select_uses_actual_metric(self):
        j=job();s.apply_research(j,[{'url':f'https://www.tiktok.com/@a/video/{i}','views':i*100} for i in [1,2,3]])
        self.assertTrue(j['selected']['url'].endswith('/3'));self.assertEqual(j['stage'],'script')
    def test_speaker_must_be_visible_cast(self):
        data=script();data['scenes'][0]['dialogue'][0]['speaker']='intruder'
        with self.assertRaises(ValueError):s.validate_script(data,4)
    def test_rejects_overlong_dialogue(self):
        data=script();data['scenes'][0]['dialogue'][0]['text']=' '.join(['Wort']*26)
        with self.assertRaises(ValueError):s.validate_script(data,4)
    def test_manual_flow_change_preserves_media(self):
        j=job();s.store_script(j,script());j['stage']='clips'
        for i,c in enumerate(j['characters']):c['file']='ref.png'
        scene_images(j)
        j['scenes'][0]['clip']='completed.mp4'
        p={'id':'profile1','label':'Premier','balance':0};s.STATE['profiles'].append(p);j['flow_profile']=p['id'];s.schedule(j)
        self.assertEqual(j['status'],'waiting_credit')
        p2={'id':'profile2','label':'Autre profil choisi','balance':50};s.STATE['profiles'].append(p2);j['flow_profile']=p2['id'];j['status']='running';s.schedule(j)
        t=s.STATE['tasks'][-1];self.assertEqual(t['profile'],'profile2');self.assertEqual(t['slot'],'clip:1');self.assertEqual(j['scenes'][0]['clip'],'completed.mp4')
    def test_pause_survives_inflight_script_completion(self):
        j=job();j['status']='paused';t={'job':j['id'],'slot':'script','status':'claimed'}
        s.accept_task_result(t,{'ok':True,'text':__import__('json').dumps(script())});self.assertEqual(j['status'],'paused');self.assertEqual(len(s.STATE['tasks']),0)
    def test_queue_is_idempotent(self):
        j=job();s.schedule(j);s.schedule(j);self.assertEqual(len(s.STATE['tasks']),1)
    def test_selected_language_reaches_script_and_video_tasks(self):
        for language in ('Deutsch (de-DE)','Français (fr-FR)','English (en-US)'):
            with self.subTest(language=language):
                s.STATE=s.fresh()
                j=job();j['config']['language']=s.creation_language(language);j['selected']={'title':'Une idée','url':'https://www.tiktok.com/@a/video/123'}
                prompt=s.script_prompt(j)
                self.assertIn(language,prompt);self.assertIn('couverture',prompt);self.assertIn('description',prompt)
                self.assertNotIn('Deutsche gesprochene Zeile',prompt)
                s.store_script(j,script());j['stage']='clips';scene_images(j)
                p={'id':'flow','label':'Flow','balance':50};s.STATE['profiles'].append(p);j['flow_profile']='flow';s.schedule(j)
                self.assertIn('Spoken language ONLY: '+language,s.STATE['tasks'][-1]['payload']['prompt'])

    def test_creation_language_accepts_the_five_atelier_languages_only(self):
        for language in ('Français (fr-FR)','English (en-US)','Español (es-ES)','Português (pt-BR)','Deutsch (de-DE)'):self.assertEqual(s.creation_language(language),language)
        for language in ('','Italiano (it-IT)','arbitrary input'):
            with self.assertRaisesRegex(ValueError,'Français, English, Español, Português ou Deutsch'):s.creation_language(language)

    def test_cover_is_checked_once_then_redrawn_once_like_the_atelier(self):
        from PIL import Image
        j=job();j['config']['cover_controls']='fix';s.store_script(j,script());s.STATE['tasks']=[];j['cover_style']='dramatic_v2';j['stage']='cover';scene_images(j)
        for i,scene in enumerate(j['scenes']):scene['clip']=f'clip{i}.mp4'
        Image.new('RGB',(64,128),'yellow').save(s.job_dir(j)/'c1.png');j['cover_file']='c1.png';j['cover']='x'
        previous=s.start_render;s.start_render=lambda id:None
        try:
            s.schedule(j);t=s.STATE['tasks'][-1];self.assertEqual((t['slot'],t['payload']['response_kind']),('cover_review','cover_review'))
            self.assertEqual(j['stage'],'cover','montage waits for the cover check')
            t['status']='claimed';s.accept_task_result(t,{'ok':True,'text':json.dumps({'production_id':j['id'],'generation_task_id':t['id'],'ok':False,'problem':'Titre coupé à droite.'})})
            self.assertNotIn('cover_file',j);self.assertIn('Titre coupé',j['corrections']['cover']);self.assertTrue(j['cover_fixed'])
            redraw=s.STATE['tasks'][-1];self.assertEqual(redraw['slot'],'cover');self.assertIn('Titre coupé',redraw['payload']['prompt'])
            Image.new('RGB',(64,128),'red').save(s.job_dir(j)/'c2.png');redraw['status']='claimed';s.accept_task_result(redraw,{'ok':True,'file':'c2.png'})
            t2=s.STATE['tasks'][-1];self.assertEqual(t2['slot'],'cover_review')
            t2['status']='claimed';s.accept_task_result(t2,{'ok':True,'text':json.dumps({'production_id':j['id'],'generation_task_id':t2['id'],'ok':False,'problem':'Encore coupé.'})})
            self.assertEqual(j['cover_file'],'c2.png','redrawn once only, then reported');self.assertEqual(j['stage'],'edit')
            self.assertEqual(j['alerts'][-1]['level'],'auto')
        finally:s.start_render=previous
    def test_state_roundtrip(self):
        j=job();s.save();r=s.read_state();self.assertEqual(r['jobs'][0]['id'],j['id'])
    def test_flow_browser_never_receives_ai_tasks(self):
        c={'role':'flow','flow_profile':'flow1','ai_provider':'none'}
        for kind in ['chat_text','chat_image','chat_collect','tiktok_search']:
            self.assertFalse(s.client_accepts(c,{'kind':kind,'payload':{'provider':'chatgpt'}}))
        self.assertTrue(s.client_accepts(c,{'kind':'flow_video','profile':'flow1'}))
    def test_ai_browser_never_receives_flow_tasks(self):
        c={'role':'creation','flow_profile':'flow1','ai_provider':'chatgpt'}
        self.assertFalse(s.client_accepts(c,{'kind':'flow_video','profile':'flow1'}))
        self.assertTrue(s.client_accepts(c,{'kind':'chat_image','payload':{'provider':'chatgpt'}}))
        self.assertFalse(s.client_accepts(c,{'kind':'chat_text','payload':{'provider':'claude'}}))
    def test_claude_only_cannot_receive_chatgpt_images(self):
        c={'role':'creation','ai_provider':'claude'}
        self.assertFalse(s.client_accepts(c,{'kind':'chat_image','payload':{'provider':'chatgpt'}}))
        self.assertTrue(s.client_accepts(c,{'kind':'chat_text','payload':{'provider':'claude'}}))
    def test_pre_submission_failure_releases_only_local_reservation(self):
        j=job();p={'id':'flow','label':'Flow','balance':40};s.STATE['profiles'].append(p)
        t={'job':j['id'],'kind':'flow_video','status':'claimed','reservation':{'profile':'flow','amount':10,'refunded':False}}
        s.accept_task_result(t,{'ok':False,'error':'Import absent','generation_submitted':False});self.assertEqual(p['balance'],50)
        s.accept_task_result(t,{'ok':False,'error':'Same','generation_submitted':False});self.assertEqual(p['balance'],50)
        t['reservation']['refunded']=False;p['balance']=40
        s.accept_task_result(t,{'ok':False,'error':'Unknown after submission'});self.assertEqual(p['balance'],40)

class HTTPTests(unittest.TestCase):
    def test_old_open_form_cannot_create_unsupported_native_1080p(self):
        for model,cost in [('gemini_omni_flash',12),('veo_3_1_lite',10)]:
            self.req('/api/job',{'brief':'A family secret','config':{'flow_model':model,'flow_cost':cost,'flow_resolution':'1080p'}})
            cfg=s.STATE['jobs'][0]['config']
            self.assertEqual(cfg['flow_resolution'],'720p')
            self.assertEqual(cfg['flow_resolution_requested'],'1080p')
            self.assertEqual(s.frame_size(s.STATE['jobs'][0]),(1080,1920))

    def test_legacy_queued_flow_task_is_normalized_before_credit_reservation(self):
        j=job();j['stage']='script';j['config'].update(flow_model='gemini_omni_flash',flow_resolution='1080p',flow_cost=12)
        s.STATE['profiles'].append({'id':'flow','label':'Flow','balance':50})
        pair=self.req('/api/bridge/pair',{'code':s.STATE['pair_code'],'role':'flow','flow_profile':'flow'})
        s.STATE['tasks'].append({'id':s.uid(),'job':j['id'],'kind':'flow_video','slot':'clip:0','status':'queued','profile':'flow','payload':{'model':'gemini_omni_flash','resolution':'1080p','cost':12}})
        result=self.req('/api/bridge/task?client='+pair['client']+'&lane=video',headers={'Authorization':'Bearer '+pair['token']})
        self.assertEqual(result['payload']['resolution'],'720p')
        self.assertEqual(j['config']['flow_resolution'],'720p')
        self.assertEqual(s.STATE['profiles'][0]['balance'],38)
    @classmethod
    def setUpClass(cls):
        cls.http=s.http.server.ThreadingHTTPServer(('127.0.0.1',0),s.Handler);s.PORT=cls.http.server_port
        cls.base=f'http://127.0.0.1:{s.PORT}'
        threading.Thread(target=cls.http.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close()
    def setUp(self):s.STATE=s.fresh()
    def test_research_reader_retry_is_owned_and_idempotent(self):
        j=job();j['status']='attention';s.event(j,'Suivi interrompu : lecteur absent')
        pair=self.req('/api/bridge/pair',{'code':s.STATE['pair_code'],'role':'creation'});auth={'Authorization':'Bearer '+pair['token']}
        old={'id':s.uid(),'job':j['id'],'kind':'tiktok_search','client':pair['client'],'slot':'research','status':'failed','payload':{'query':'früchte deutsch'}};s.STATE['tasks'].append(old)
        result=self.req('/api/bridge/retry-research',{'client':pair['client']},auth)
        self.assertEqual(result['resumed'],[j['id']]);self.assertEqual(j['status'],'running')
        self.assertEqual(self.req('/api/bridge/retry-research',{'client':pair['client']},auth)['resumed'],[])
        self.assertEqual(len([t for t in s.STATE['tasks'] if t['status']=='queued']),1)

    def test_existing_flow_clip_recovery_does_not_reserve_credits(self):
        j=job();s.store_script(j,script());j['stage']='clips';j['status']='attention'
        s.STATE['profiles'].append({'id':'flow','label':'Flow','balance':30});j['flow_profile']='flow'
        pair=self.req('/api/bridge/pair',{'code':s.STATE['pair_code'],'role':'flow','flow_profile':'flow'});auth={'Authorization':'Bearer '+pair['token']}
        old={'id':s.uid(),'job':j['id'],'kind':'flow_video','profile':'flow','client':pair['client'],'slot':'clip:1','status':'failed','payload':{'prompt':'exact prompt'}};s.STATE['tasks'].append(old)
        rows=self.req('/api/bridge/recoverable-videos?client='+pair['client'],headers=auth);self.assertEqual(len(rows),1)
        task=self.req('/api/bridge/recover-video',{'client':pair['client'],'previous_task':old['id']},auth)
        self.assertEqual(task['kind'],'flow_collect');self.assertEqual(task['slot'],'clip:1');self.assertEqual(task['status'],'claimed')
        self.assertNotIn('reservation',task);self.assertEqual(s.STATE['profiles'][0]['balance'],30)
        with self.assertRaises(urllib.error.HTTPError):self.req('/api/bridge/recover-video',{'client':pair['client'],'previous_task':old['id']},auth)
    def test_paused_flow_clip_is_not_automatically_recovered(self):
        j=job();s.store_script(j,script());j['stage']='clips';j['status']='paused'
        pair=self.req('/api/bridge/pair',{'code':s.STATE['pair_code'],'role':'flow','flow_profile':'flow'});auth={'Authorization':'Bearer '+pair['token']}
        old={'id':s.uid(),'job':j['id'],'kind':'flow_video','profile':'flow','client':pair['client'],'slot':'clip:0','status':'failed','payload':{}};s.STATE['tasks'].append(old)
        self.assertEqual(self.req('/api/bridge/recoverable-videos?client='+pair['client'],headers=auth),[])
        with self.assertRaises(urllib.error.HTTPError):self.req('/api/bridge/recover-video',{'client':pair['client'],'previous_task':old['id']},auth)
    def test_progress_requires_task_owner_and_does_not_repeat(self):
        j=job();pair=self.req('/api/bridge/pair',{'code':s.STATE['pair_code'],'label':'QA'});auth={'Authorization':'Bearer '+pair['token']}
        t={'id':s.uid(),'job':j['id'],'slot':'clip:0','kind':'flow_video','status':'claimed','client':pair['client']};s.STATE['tasks'].append(t)
        body={'client':pair['client'],'task':t['id'],'message':'Import Flow : traitement en cours'}
        self.req('/api/bridge/progress',body,auth);self.assertEqual(j['events'][-1]['text'],body['message']);count=len(j['events'])
        self.req('/api/bridge/progress',body,auth);self.assertEqual(len(j['events']),count)
        with self.assertRaises(urllib.error.HTTPError):self.req('/api/bridge/progress',{**body,'client':'other'},auth)
    def req(self,path,body=None,headers=None):
        h={'Origin':self.base,'Content-Type':'application/json',**(headers or {})}
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=h)
        with urllib.request.urlopen(req) as r:return json.load(r)
    def test_new_production_defaults_to_omni_without_modifying_existing_job(self):
        old=job();before=copy.deepcopy(old)
        self.req('/api/job',{'brief':'A family secret','config':{'scene_count':4,'provider':'chatgpt','language':'Deutsch (de-DE)'}})
        new=s.STATE['jobs'][0]
        self.assertEqual(new['config']['flow_model'],'gemini_omni_flash_1_2')
        self.assertEqual(new['config']['flow_cost'],30);self.assertEqual(new['config']['flow_resolution'],'720p')
        self.assertEqual(new['config']['clip_seconds'],10);self.assertEqual(new['config']['clip_routing'],'v09_grok_first');self.assertEqual(old,before)
        count=len(s.STATE['jobs'])
        with self.assertRaises(urllib.error.HTTPError):
            self.req('/api/job',{'brief':'test','config':{'flow_model':'gemini_omni_flash','flow_cost':10}})
        self.assertEqual(len(s.STATE['jobs']),count)

    def test_flow_model_costs_and_no_silent_fallback(self):
        for model,cost in [('veo_3_1_fast',20),('veo_3_1_fast',10),('veo_3_1_quality',100),('veo_3_1_lite',5)]:
            self.req('/api/job',{'brief':'test','config':{'flow_model':model,'flow_cost':cost}})
            self.assertEqual(s.STATE['jobs'][0]['config']['flow_model'],model)
            self.assertEqual(s.STATE['jobs'][0]['config']['flow_cost'],cost)
        for model,cost in [('veo_3_1_quality',10),('veo_3_1_fast',12),('unknown',10)]:
            count=len(s.STATE['jobs'])
            with self.assertRaises(urllib.error.HTTPError):
                self.req('/api/job',{'brief':'test','config':{'flow_model':model,'flow_cost':cost}})
            self.assertEqual(len(s.STATE['jobs']),count)

    def test_cross_origin_cannot_change_profiles(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.req('/api/profile',{'label':'bad','balance':50},{'Origin':'https://untrusted.example'})
        self.assertEqual(e.exception.code,403);self.assertEqual(s.STATE['profiles'],[])
    def test_bridge_requires_pairing(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.req('/api/bridge/task?client=unknown')
        self.assertEqual(e.exception.code,401)
    def test_flow_reservation_happens_once_and_waits_when_exhausted(self):
        self.req('/api/profile',{'label':'Flow A','balance':10});p=s.STATE['profiles'][0]
        pair=self.req('/api/bridge/pair',{'code':s.STATE['pair_code'],'label':'QA','role':'flow','flow_profile':p['id']})
        j=job();s.store_script(j,script());j['stage']='clips';j['flow_profile']=p['id']
        scene_images(j)
        auth={'Authorization':'Bearer '+pair['token']}
        t=self.req('/api/bridge/task?client='+pair['client'],headers=auth)
        self.assertEqual(t['slot'],'clip:0');self.assertEqual(p['balance'],0)
        self.assertIsNone(self.req('/api/bridge/task?client='+pair['client'],headers=auth));self.assertEqual(p['balance'],0)
        self.req('/api/bridge/result',{'client':pair['client'],'task':t['id'],'result':{'ok':False,'error':'Coût non lisible'}},auth)
        # 0.1.93: clip 1 (uncertain) waits for the owner; the next clips wait for credits.
        self.assertEqual(s.held_clips(j),{0});self.assertEqual(j['status'],'waiting_credit');self.assertEqual(p['balance'],0)
        self.assertEqual(j['alerts'][-1]['level'],'action')
    def test_declared_balance_cannot_be_negative(self):
        with self.assertRaises(urllib.error.HTTPError):self.req('/api/profile',{'label':'Bad','balance':-1})
        self.assertFalse(s.STATE['profiles'])
    def test_recover_existing_response_never_creates_new_prompt(self):
        j=job();j['stage']='script';j['status']='attention'
        pair=self.req('/api/bridge/pair',{'code':s.STATE['pair_code'],'label':'QA','role':'all'})
        auth={'Authorization':'Bearer '+pair['token']}
        task=self.req('/api/bridge/recover',{'client':pair['client'],'job':j['id']},auth)
        self.assertEqual(task['kind'],'chat_collect');self.assertEqual(task['status'],'claimed');self.assertNotIn('prompt',task['payload'])
        self.assertEqual(task['payload']['expected_job'],j['id'])
        self.assertEqual(j['status'],'running')
        self.req('/api/bridge/result',{'client':pair['client'],'task':task['id'],'result':{'ok':True,'text':json.dumps(script())}},auth)
        self.assertEqual(j['stage'],'characters')

    def test_flow_generation_resolution_preserves_output_and_invalidates_old_dry_run(self):
        j=job();j['status']='paused';j['config']['flow_resolution']='1080p';j['dry_run_passed']='old-engine-test'
        before=s.frame_size(j)
        self.req('/api/job/'+j['id'],{'action':'flow_resolution','resolution':'720p'})
        self.assertEqual(j['config']['flow_resolution'],'720p');self.assertEqual(s.frame_size(j),before)
        self.assertNotIn('dry_run_passed',j);self.assertEqual(j['status'],'paused')
        with self.assertRaises(urllib.error.HTTPError):self.req('/api/job/'+j['id'],{'action':'flow_resolution','resolution':'4k'})
        s.STATE['tasks'].append({'id':'active','job':j['id'],'slot':'clip:0','kind':'flow_video','status':'claimed'})
        with self.assertRaises(urllib.error.HTTPError):self.req('/api/job/'+j['id'],{'action':'flow_resolution','resolution':'1080p'})
        self.assertEqual(j['config']['flow_resolution'],'720p')
    def test_duplicate_result_is_acknowledged_without_duplicate_tasks(self):
        j=job();j['stage']='script';j['status']='attention'
        pair=self.req('/api/bridge/pair',{'code':s.STATE['pair_code'],'label':'QA','role':'all'});auth={'Authorization':'Bearer '+pair['token']}
        task=self.req('/api/bridge/recover',{'client':pair['client'],'job':j['id']},auth)
        payload={'client':pair['client'],'task':task['id'],'result':{'ok':True,'text':json.dumps(script())}}
        self.req('/api/bridge/result',payload,auth);before=len(s.STATE['tasks'])
        again=self.req('/api/bridge/result',payload,auth)
        self.assertTrue(again['already_received']);self.assertEqual(len(s.STATE['tasks']),before)
    def test_automatic_recovery_respects_pause_and_task_owner(self):
        j=job();j['stage']='script';j['status']='attention'
        pair=self.req('/api/bridge/pair',{'code':s.STATE['pair_code'],'label':'QA','role':'all'});auth={'Authorization':'Bearer '+pair['token']}
        task=self.req('/api/bridge/recover',{'client':pair['client'],'job':j['id']},auth)
        j['status']='paused'
        with self.assertRaises(urllib.error.HTTPError):self.req('/api/bridge/recover',{'client':pair['client'],'job':j['id'],'automatic':True,'previous_task':task['id']},auth)
        self.assertEqual(j['status'],'paused')
        with self.assertRaises(urllib.error.HTTPError):self.req('/api/bridge/status?client=other&task='+task['id'],headers=auth)
    def test_failed_image_can_be_recovered_without_new_generation(self):
        j=job();s.store_script(j,script());j['status']='attention'
        pair=self.req('/api/bridge/pair',{'code':s.STATE['pair_code'],'label':'ChatGPT','role':'creation','ai_provider':'chatgpt'});auth={'Authorization':'Bearer '+pair['token']}
        old={'id':s.uid(),'job':j['id'],'kind':'chat_image','slot':'character:orange','status':'failed','client':pair['client'],'payload':{'provider':'chatgpt','prompt':'Unique original orange character image prompt for this production.'}}
        s.STATE['tasks'].append(old)
        rows=self.req('/api/bridge/recoverable-media?client='+pair['client'],headers=auth);self.assertEqual(len(rows),1)
        task=self.req('/api/bridge/recover-media',{'client':pair['client'],'previous_task':old['id']},auth)
        self.assertEqual(task['kind'],'chat_image_collect');self.assertEqual(task['slot'],'character:orange')
        (s.job_dir(j)/'recovered.png').write_bytes(b'test-image')
        self.req('/api/bridge/result',{'client':pair['client'],'task':task['id'],'result':{'ok':True,'file':'recovered.png'}},auth)
        self.assertEqual(j['characters'][0]['file'],'recovered.png');self.assertEqual(j['stage'],'images')

if __name__=='__main__':unittest.main()
