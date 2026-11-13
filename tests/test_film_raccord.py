"""Rendu film (11/11/2026): owner script kept word for word, raccord from the last image, no montage zoom."""
import importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_film', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import montage

SCRIPT = json.loads((ROOT / 'scenario-malediction-de-mango-ep1.json').read_text('utf-8'))


def job():
    j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'brief': '', 'characters': [], 'scenes': [], 'candidates': [],
         'selected': {'title': 'Scénario', 'source': 'owner_script'}, 'editorial_version': 2, 'retention_version': 1, 'hook_version': 1,
         'config': {'scene_count': len(SCRIPT['scenes']), 'provider': 'chatgpt', 'flow_cost': 24, 'language': 'Français (fr-FR)',
                    'montage': montage.validate({})}}
    s.STATE['jobs'].append(j)
    return j


class FilmTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_owner_script_kept_word_for_word(self):
        j = job(); s.store_script(j, json.loads(json.dumps(SCRIPT)))
        self.assertEqual(j['stage'], 'characters')
        self.assertEqual([x['dialogue'] for x in j['scenes']], [x['dialogue'] for x in SCRIPT['scenes']])
        self.assertEqual(j['scenes'][13]['dialogue'], [], 'silent dusk shot allowed')

    def test_raccord_same_place_only(self):
        j = job(); s.store_script(j, json.loads(json.dumps(SCRIPT)))
        self.assertIsNone(s.raccord_from(j, 0))
        self.assertEqual(s.raccord_from(j, 1), 0)
        self.assertIsNone(s.raccord_from(j, 5), 'couvent -> marché: new place')
        self.assertIsNone(s.raccord_from(j, 9), 'subject changes: marked raccord false')
        self.assertTrue(s.raccord_waiting(j, 1))
        j['config']['montage']['raccord'] = False
        self.assertIsNone(s.raccord_from(j, 1))

    def test_old_episodes_keep_zoom_and_no_raccord(self):
        self.assertTrue(montage.of({})['zoom']); self.assertFalse(montage.of({})['raccord'])
        film = montage.validate({})
        self.assertFalse(film['zoom']); self.assertFalse(film['fast_cuts']); self.assertTrue(film['raccord'])

    def test_film_direction_in_prompt(self):
        j = job(); s.store_script(j, json.loads(json.dumps(SCRIPT)))
        p = s.clip_prompt(j, 1, 'flow')
        self.assertIn('no extreme close-up', p); self.assertLessEqual(len(p), s.CLIP_PROMPT_MAX)
        self.assertIn('SETTING, identical from the first to the last frame', p)
        self.assertTrue(all(len(s.clip_prompt(j, i, 'grok')) <= s.CLIP_PROMPT_MAX for i in range(len(j['scenes']))))

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg requis')
    def test_start_image_is_last_frame_of_previous_clip(self):
        from PIL import Image
        j = job(); s.store_script(j, json.loads(json.dumps(SCRIPT))); d = s.job_dir(j)
        for i in (0, 1):
            Image.new('RGB', (32, 64), (9, 9, 9)).save(d / f'scene{i}.png'); j['scenes'][i]['image'] = f'scene{i}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=red:s=72x128:r=10', '-t', '2', '-pix_fmt', 'yuv420p', str(d / 'clip0.mp4')], check=True)
        j['scenes'][0]['clip'] = 'clip0.mp4'
        name = s.start_image(j, 1)
        self.assertTrue(name.startswith('raccord1_')); self.assertIn('last frame of the previous shot', s.clip_prompt(j, 1, 'flow'))
        with Image.open(d / name) as im:
            self.assertGreater(im.getpixel((5, 5))[0], 200)
        self.assertEqual(s.start_image(j, 0), 'scene0.png')

    def test_native_720p_without_upscale(self):
        j = job()
        self.assertEqual(s.frame_size(j), (720, 1280))
        self.assertEqual(s.frame_size({'config': {}}), (1080, 1920), 'old episodes keep 1080p')

    def test_voice_accent_in_prompt(self):
        j = job(); s.store_script(j, json.loads(json.dumps(SCRIPT)))
        j['config']['voice_accent'] = 'West African French (Cameroon, Ivory Coast)'
        p = s.clip_prompt(j, 0, 'grok')
        self.assertIn('West African French', p); self.assertIn('Que veux-tu', p)
        j['config']['extras_rule'] = 'Background extras are fruit characters, never humans.'
        self.assertIn('never humans', s.clip_prompt(j, 5, 'grok'))

    def test_grok_when_flow_has_no_credits(self):
        from PIL import Image
        j = job(); s.store_script(j, json.loads(json.dumps(SCRIPT))); d = s.job_dir(j)
        j['config']['grok_when_no_credits'] = True; j['grok_ok'] = True; j['stage'] = 'clips'
        Image.new('RGB', (32, 64), (9, 9, 9)).save(d / 'scene0.png'); j['scenes'][0]['image'] = 'scene0.png'
        from unittest import mock
        with mock.patch.object(s, 'engine_ready', lambda j, e, m=None: e == 'grok'):
            s.schedule_flow_clip(j, 0)
        t = s.STATE['tasks'][-1]
        self.assertEqual((t['kind'], t['payload']['engine']), ('engine_video', 'grok'))


if __name__ == '__main__':
    unittest.main()
