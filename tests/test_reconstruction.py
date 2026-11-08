import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).parents[1]))
import reconstruction


class ReferenceTests(unittest.TestCase):
    def test_description_mode_never_copies_source_images_into_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest,folder=self.fixture(temp)
            manifest['generation_mode']='description_only'
            manifest['script']['characters'][0].update(name='Boy',appearance='Red apple boy',image_prompt='Generate a new boy from text')
            manifest['script']['scenes'][0]['image_prompt']='New street scene from text'
            manifest['script']['scenes'][0]['video_prompt']='Boy offers a cake'
            (folder/'manifest.json').write_text(json.dumps(manifest),'utf-8')
            state={'jobs':[],'profiles':[],'settings':{},'tasks':[]}
            job,_=reconstruction.create(temp,state,'reference-de','c'*16,'now')
            self.assertEqual(job['stage'],'characters')
            self.assertTrue(job['config']['generated_from_description'])
            self.assertNotIn('file',job['characters'][0])
            self.assertNotIn('image',job['scenes'][0])
            self.assertNotIn('reference_image',job['scenes'][0])
            self.assertFalse((pathlib.Path(temp)/'jobs'/job['id']/'frame.jpg').exists())
            self.assertIn('No source screenshot',reconstruction.sheet_prompt(job))
            self.assertIn('No source-video capture',reconstruction.image_prompt(job,0))

    def test_part2_cannot_start_before_part1_is_done(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest,folder=self.fixture(temp)
            manifest['depends_on']='part1'
            (folder/'manifest.json').write_text(json.dumps(manifest),'utf-8')
            state={'jobs':[],'profiles':[],'settings':{},'tasks':[]}
            with self.assertRaisesRegex(ValueError,'partie 1'):
                reconstruction.create(temp,state,'reference-de','d'*16,'now')

    def test_silent_source_shot_is_not_mistaken_for_missing_dialogue(self):
        import quality
        self.assertEqual(quality.compare('', '', 'de', 0), (1.0, []))
        score, issues=quality.compare('', 'Invented dialogue', 'de', 1)
        self.assertEqual(score,0)
        self.assertTrue(issues)

    def fixture(self,root):
        folder=pathlib.Path(root)/'reference-presets'/'reference-de'
        folder.mkdir(parents=True)
        (folder/'frame.jpg').write_bytes(b'provided-frame')
        manifest={'source_kind':'user_supplied_video','source_seconds':6,'language':'Deutsch (de-DE)',
          'source':{'fruit_change_allowed':True,'fruit_change_applied':False},
          'script':{'title':'Original scene','characters':[{'id':'boy'}],
                    'scenes':[{'reference_image':'frame.jpg','source_start':0,'source_end':6,
                               'characters':['boy'],'dialogue':[{'speaker':'boy','text':'Guten Tag!'}]}]}}
        (folder/'manifest.json').write_text(json.dumps(manifest),'utf-8')
        return manifest,folder

    def test_prepare_preserves_accounts_and_never_queues_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            self.fixture(temp)
            state={'jobs':[],'profiles':[{'id':'saved','balance':50}],'engine_accounts':[{'id':'grok'}],
                   'settings':{},'tasks':[],'token':'secret','pair_code':'same'}
            before=json.dumps({k:state[k] for k in ('profiles','engine_accounts','tasks','token','pair_code')})
            job,created=reconstruction.create(temp,state,'reference-de','a'*16,'now','saved')
            self.assertTrue(created)
            self.assertEqual(job['status'],'paused')
            self.assertEqual(job['stage'],'clips')
            self.assertFalse(job['config']['dynamic'])
            self.assertFalse(job['config']['smooth_transitions'])
            self.assertEqual(job['config']['language'],'Deutsch (de-DE)')
            self.assertEqual(before,json.dumps({k:state[k] for k in ('profiles','engine_accounts','tasks','token','pair_code')}))
            again,new=reconstruction.create(temp,state,'reference-de','b'*16,'later')
            self.assertFalse(new);self.assertEqual(again['id'],job['id']);self.assertEqual(len(state['jobs']),1)
            self.assertEqual((pathlib.Path(temp)/'jobs'/job['id']/'frame.jpg').read_bytes(),b'provided-frame')

    def test_rejects_paths_outside_preset_and_unknown_speakers(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest,folder=self.fixture(temp)
            with self.assertRaises(ValueError):reconstruction.load(temp,'../outside')
            manifest['script']['scenes'][0]['reference_image']='../frame.jpg'
            (folder/'manifest.json').write_text(json.dumps(manifest),'utf-8')
            with self.assertRaises(ValueError):reconstruction.load(temp,'reference-de')

    def test_trim_never_removes_detected_german_speech(self):
        scene={'source_start':0,'source_end':4,'dialogue':[{'text':'Hallo'}]}
        self.assertEqual(reconstruction.duration(scene,None,8),8)
        self.assertAlmostEqual(reconstruction.duration(scene,{'words':[{'end':6.7}]},8),6.9)
        self.assertEqual(reconstruction.duration({**scene,'dialogue':[]},None,8),4)


if __name__=='__main__':unittest.main()
