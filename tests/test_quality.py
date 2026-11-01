import copy,json,pathlib,shutil,subprocess,tempfile,unittest
from unittest.mock import patch
import quality
import server as s

class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=pathlib.Path(self.temp.name)
        self.previous=s.STATE,s.DATA;s.DATA=self.folder;s.STATE=s.fresh()
        self.job={'id':'qualitytest','title':'Original','status':'running','stage':'quality','events':[],
                  'config':{'language':'Deutsch (de-DE)'},'characters':[{'id':'pear','name':'Lou','appearance':'Pear','file':'ref.png'}],
                  'scenes':[{'clip':'clip.mp4','image':'scene.png','meaning':'An accusation','dialogue':[{'speaker':'pear','text':'Gib mir meinen Schlüssel!'}]}]}
        s.STATE['jobs']=[self.job];d=s.job_dir(self.job)
        for name in ('clip.mp4','scene.png','ref.png'):(d/name).write_bytes(name.encode())
        self.key=quality.fingerprint(self.job,d)
        self.job['quality_report']={'fingerprint':self.key,'hard_errors':[],'warnings':[],'clips':[{'sheet':'sheet.jpg'}]}
    def tearDown(self):s.STATE,s.DATA=self.previous;self.temp.cleanup()
    def test_transcript_comparison_keeps_accents_and_flags_missing_or_changed_dialogue(self):
        self.assertEqual(quality.compare('Gib mir meinen Schlüssel!','Gib mir meinen Schlüssel.', 'de',.95),(1.0,[]))
        self.assertTrue(quality.compare('Gib mir meinen Schlüssel!','Goodbye, see you tomorrow.', 'en',.95)[1])
        self.assertTrue(quality.compare('Bonjour','', 'fr',.2)[1])
    def test_matching_subtitles_follow_actual_speech_times(self):
        scene=self.job['scenes'][0];speech={'match':1,'words':[{'word':w,'start':a,'end':b} for w,a,b in [('Gib',1,1.2),('mir',1.3,1.5),('meinen',1.6,1.9),('Schlüssel',2,2.5)]]}
        self.assertEqual(quality.caption_events(scene,speech,8),[(9,10.5,'Gib mir meinen Schlüssel!')])
        self.assertIsNone(quality.caption_events(scene,{**speech,'match':.3},8))
        speech['words'][-1]['end']=9
        self.assertIsNone(quality.caption_events(scene,speech,8))
    def test_pause_on_audio_issue_does_not_queue_any_flow_generation(self):
        self.job['quality_report']['warnings']=['Dialogue incomplet']
        s.schedule_quality(self.job)
        self.assertEqual(self.job['status'],'attention');self.assertEqual(s.STATE['tasks'],[])
    def test_success_queues_bound_visual_review_once_using_actual_sheets(self):
        self.job['quality_version']=1
        s.schedule(self.job);s.schedule(self.job)
        self.assertEqual(len(s.STATE['tasks']),1);t=s.STATE['tasks'][0]
        self.assertEqual((t['kind'],t['slot']),('chat_text','quality_review'))
        self.assertEqual(t['payload']['response_kind'],'quality_review')
        self.assertEqual(t['payload']['fingerprint'],self.key)
        self.assertTrue(t['payload']['attachments'][-1].endswith('/sheet.jpg'))
    def test_visual_mismatch_holds_export_and_never_regenerates_clips(self):
        report=self.job['quality_report'];report['visual']={'scenes':[{'index':0,'status':'issue','detail':'Fruit identity changed'}],'continuity':{'status':'pass','detail':'Same room'}}
        original=copy.deepcopy(self.job['scenes']);s.schedule_quality(self.job)
        self.assertEqual(self.job['status'],'attention');self.assertEqual(self.job['scenes'],original)
        self.assertEqual(s.STATE['tasks'],[])
    def test_report_rejects_wrong_binding_and_partial_review(self):
        value={'production_id':self.job['id'],'generation_task_id':'task','quality_review':{'scenes':[{'index':0,'status':'pass','detail':'Same pear'}],'continuity':{'status':'pass','detail':'Same room'}}}
        self.assertEqual(quality.validate_visual(value,self.job,'task'),value['quality_review'])
        with self.assertRaises(ValueError):quality.validate_visual(value,self.job,'other')
        value['quality_review']['scenes']=[]
        with self.assertRaises(ValueError):quality.validate_visual(value,self.job,'task')
    def test_received_review_is_saved_and_preserves_pause(self):
        s.schedule_quality(self.job);t=s.STATE['tasks'][0];t['status']='claimed';self.job['status']='paused'
        value={'production_id':self.job['id'],'generation_task_id':t['id'],'quality_review':{'scenes':[{'index':0,'status':'pass','detail':'Same pear'}],'continuity':{'status':'pass','detail':'Same room'}}}
        s.accept_task_result(t,{'ok':True,'text':json.dumps(value)})
        self.assertEqual(t['status'],'done');self.assertEqual(self.job['status'],'paused')
        self.assertEqual(self.job['stage'],'quality');self.assertTrue((s.job_dir(self.job)/'quality-report.json').exists())

    def test_stale_visual_result_cannot_be_accepted_after_replacement(self):
        s.schedule_quality(self.job);t=s.STATE['tasks'][0]
        (s.job_dir(self.job)/'clip.mp4').write_bytes(b'replaced')
        with self.assertRaisesRegex(ValueError,'Médias changés'):
            s.accept_task_result(t,{'ok':True,'text':'{}'})
        self.assertNotIn('visual',self.job['quality_report'])

    def test_media_replacement_invalidates_report(self):
        (s.job_dir(self.job)/'clip.mp4').write_bytes(b'new clip')
        self.assertNotEqual(quality.fingerprint(self.job,s.job_dir(self.job)),self.key)
    def test_silent_video_is_not_presented_as_passed_audio(self):
        if not shutil.which('ffmpeg'):self.skipTest('ffmpeg required')
        file=self.folder/'silent.mp4'
        subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=red:s=72x128:r=1','-f','lavfi','-i','anullsrc=r=16000:cl=mono','-t','8','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(file)],check=True,capture_output=True)
        self.assertTrue(any('silencieux' in x for x in quality.technical(file)['hard_errors']))
