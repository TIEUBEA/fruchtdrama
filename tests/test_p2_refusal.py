"""P2-05: graduated rewording of refused images. Unit and integration tests."""
import importlib.util, os, pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p2_refusal', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import refusal


class SoftenTests(unittest.TestCase):
    def test_levels(self):
        p = 'Premium 3D animation. A young woman holds a bloody knife next to a corpse.'
        self.assertEqual(refusal.soften(p, 0), p)
        one = refusal.soften(p, 1)
        self.assertIn('red juice', one); self.assertIn('kitchen utensil', one); self.assertIn('motionless figure', one)
        self.assertNotIn('knife', one.lower().replace('kitchen utensil', ''))
        self.assertIn('keep exactly the visual style described below', one); self.assertIn('Premium 3D animation', one, 'style kept, never forced to cartoon')
        self.assertIn('young woman', one, 'ages untouched at level 1')
        two = refusal.soften(p, 2)
        self.assertIn('A woman', two); self.assertTrue(two.endswith('generate the image directly.'))

    def test_german_and_french(self):
        self.assertIn('roter Saft', refusal.soften('Blut auf dem Messer', 1)); self.assertIn('Küchenutensil', refusal.soften('Blut auf dem Messer', 1))
        self.assertIn('jus rouge', refusal.soften('du sang sur le couteau', 1)); self.assertIn('ustensile', refusal.soften('du sang sur le couteau', 1))
        self.assertIn('Spielzeug', refusal.soften('Spielzeug', 1), 'ordinary words untouched')

    def test_applies_only_to_chatgpt_images(self):
        self.assertTrue(refusal.applies({'kind': 'chat_image', 'slot': 'image:3'}))
        self.assertTrue(refusal.applies({'kind': 'chat_image', 'slot': 'characters'}))
        self.assertFalse(refusal.applies({'kind': 'chat_text', 'slot': 'script'}))
        self.assertFalse(refusal.applies({'kind': 'flow_video', 'slot': 'clip:0'}))


def job():
    j = {'id': s.uid(), 'stage': 'images', 'status': 'running', 'events': [], 'brief': 'b', 'candidates': [], 'flow_profile': None,
         'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p', 'file': 'ref.png'}],
         'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'Oma finds a bloody knife', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}]}],
         'config': {'scene_count': 1, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)'}}
    s.STATE['jobs'].append(j); return j


class FlowTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def refuse(self, j):
        t = [x for x in s.STATE['tasks'] if x['status'] == 'queued'][-1]; t['status'] = 'claimed'
        s.accept_task_result(t, {'ok': False, 'error_kind': 'refusal', 'error': 'ChatGPT refuse cette image (refus de contenu)'})
        return t

    def test_two_levels_then_owner(self):
        j = job(); s.schedule(j)
        first = self.refuse(j)
        self.assertNotIn('refusal_level', first['payload'])
        second = [x for x in s.STATE['tasks'] if x['status'] == 'queued'][-1]
        self.assertEqual(second['payload']['refusal_level'], 1); self.assertIn('red juice', second['payload']['prompt'])
        self.assertEqual(j['status'], 'running'); self.assertIn('niveau 1 sur 2', j['events'][-2]['text'])
        self.refuse(j); third = [x for x in s.STATE['tasks'] if x['status'] == 'queued'][-1]
        self.assertEqual(third['payload']['refusal_level'], 2); self.assertIn('Do not ask questions', third['payload']['prompt'])
        self.refuse(j)
        self.assertEqual(j['status'], 'attention'); self.assertIn('même reformulée', j['events'][-1]['text'])
        self.assertEqual([x for x in s.STATE['tasks'] if x['status'] == 'queued'], [], 'no fourth attempt without the owner')

    def test_success_and_redo_reset_the_level(self):
        from PIL import Image
        j = job(); s.schedule(j); self.refuse(j)
        t = [x for x in s.STATE['tasks'] if x['status'] == 'queued'][-1]; t['status'] = 'claimed'
        Image.new('RGB', (32, 64), 'blue').save(s.job_dir(j) / 'ok.png'); Image.new('RGB', (32, 64), 'orange').save(s.job_dir(j) / 'ref.png')
        s.accept_task_result(t, {'ok': True, 'file': 'ok.png'})
        self.assertNotIn('image:0', j['refusal_levels'])
        j['refusal_levels']['cover'] = 2; j.update(stage='done', status='done', cover_file='ok.png', title='T', script={'title': 'T', 'cover_title': 'C', 'description': 'd', 'characters': [], 'scenes': j['scenes']})
        j['scenes'][0]['clip'] = 'c.mp4'
        s.redo(j, 'cover', 'plus doux'); self.assertNotIn('cover', j['refusal_levels'])

    def test_paused_production_is_not_reworded(self):
        j = job(); s.schedule(j); t = [x for x in s.STATE['tasks'] if x['status'] == 'queued'][-1]; t['status'] = 'claimed'; j['status'] = 'paused'
        s.accept_task_result(t, {'ok': False, 'error_kind': 'refusal', 'error': 'refus'})
        self.assertEqual(j['status'], 'paused'); self.assertNotIn('refusal_levels', j)


if __name__ == '__main__':
    unittest.main()
