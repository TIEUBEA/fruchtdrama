"""P5-06: video engine per production. Unit, HTTP and real ffmpeg montage tests."""
import importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile, threading, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p5_engines', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
from tests import accounts_ready; accounts_ready.install(s)  # 0.1.91: accounts ready before starting
import engines, quality, editorial


def script(words=5):
    line = ' '.join(['Hallo'] * words)
    return {'title': 'Omas Reise', 'cover_title': 'WER?', 'description': 'd',
            'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'Orange', 'voice': 'v', 'image_prompt': 'p'}],
            'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'motion', 'dialogue': [{'speaker': 'orange', 'text': line}]} for _ in range(4)]}


def clip_job(engine='grok', dry=False):
    from PIL import Image
    j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'brief': 'b', 'characters': [], 'scenes': [], 'candidates': [], 'flow_profile': None, 'selected': {'title': 'Référence', 'url': 'https://www.tiktok.com/@a/video/1'},
         'config': {'scene_count': 4, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)', 'video_engine': engine, 'dry_run': dry}}
    s.STATE['jobs'].append(j); s.store_script(j, script()); j['stage'] = 'clips'
    for i, scene in enumerate(j['scenes']):
        Image.new('RGB', (32, 64), (i * 50, 9, 9)).save(s.job_dir(j) / f'scene{i}.png'); scene['image'] = f'scene{i}.png'
    return j


class EngineUnitTests(unittest.TestCase):
    def test_catalogue_and_validation(self):
        self.assertEqual(set(engines.ENGINES), {'flow', 'grok', 'vidogrid'})
        self.assertEqual(engines.validate(None), 'flow')
        with self.assertRaises(ValueError):
            engines.validate('sora')
        self.assertEqual(engines.of({'config': {}}), 'flow', 'older productions stay on Flow')

    def test_word_limit_follows_duration(self):
        self.assertEqual(engines.word_limit({'config': {}}), 24)
        self.assertEqual(engines.word_limit({'config': {'video_engine': 'grok'}}), 30)
        self.assertEqual(engines.word_limit({'config': {'video_engine': 'grok'}}, 25), 31)

    def test_montage_length(self):
        self.assertEqual(engines.clip_length({'config': {}}, 7.7), 8.0, 'Flow stays exactly 8 s')
        grok = {'config': {'video_engine': 'grok'}}
        self.assertEqual(engines.clip_length(grok, 6.04), 6.04)
        self.assertEqual(engines.clip_length(grok, 30), 10.5)
        self.assertEqual(engines.clip_length(grok, None), 5.5)

    def test_editorial_limit_scales(self):
        j = {'config': {'video_engine': 'grok'}, 'retention_version': 1}
        self.assertIn('30 mots parlés par scène de 10 secondes', editorial.retention_instructions(j))


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_grok_clip_task_without_credit_reservation(self):
        j = clip_job('grok'); s.schedule(j)
        t = s.STATE['tasks'][-1]
        self.assertEqual((t['kind'], t['slot']), ('engine_video', 'clip:0'))
        self.assertEqual(t['payload']['engine'], 'grok'); self.assertEqual(t['payload']['seconds'], 10)
        self.assertIn('10 seconds', t['payload']['prompt']); self.assertNotIn('cost', t['payload'])
        self.assertEqual(j['status'], 'running', 'no Flow profile or credit needed')

    def test_script_prompt_and_edit_follow_the_engine(self):
        j = clip_job('grok')
        self.assertIn('scènes de 10 secondes', s.script_prompt(j))
        j.update(stage='characters', editorial_version=2, retention_version=1); j['config']['review_script'] = True
        for c in j['characters']:
            c.pop('file', None)
        with self.assertRaisesRegex(ValueError, '30 mots'):
            s.edit_script(j, {'scenes': [{'dialogue': [{'speaker': 'orange', 'text': t}]} for t in (' '.join(['Wort'] * 31), 'b', 'c', 'd')]})

    def test_dry_run_for_grok(self):
        j = clip_job('vidogrid', dry=True); s.schedule(j)
        t = s.STATE['tasks'][-1]; self.assertTrue(t['payload']['dry_run']); t['status'] = 'claimed'
        s.accept_task_result(t, {'ok': False, 'dry_run': True, 'generation_submitted': False, 'error': 'Essai à blanc réussi'})
        self.assertEqual(j['status'], 'paused'); self.assertTrue(j['dry_run_passed'])

    def test_failed_engine_clip_is_never_uncertain(self):
        j = clip_job('grok'); s.schedule(j); t = s.STATE['tasks'][-1]; t['status'] = 'claimed'
        s.accept_task_result(t, {'ok': False, 'error': 'Génération trop longue', 'generation_submitted': True})
        self.assertEqual(s.uncertain_clip_tasks(j), [], 'no money at stake: no uncertain-submission lock')
        self.assertEqual(j['last_error']['kind'], 'timeout')

    def test_routing(self):
        task = {'kind': 'engine_video', 'payload': {'engine': 'grok'}}
        self.assertTrue(s.client_accepts({'role': 'all'}, task)); self.assertFalse(s.client_accepts({'role': 'flow'}, task))
        self.assertFalse(s.client_accepts({'role': 'creation'}, task))


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh(); self.available = engines.AVAILABLE

    def tearDown(self):
        engines.AVAILABLE = self.available

    def req(self, body):
        r = urllib.request.Request(self.base + '/api/job', data=json.dumps(body).encode(), headers={'Origin': self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def test_engine_is_validated_and_gated_until_its_connector_ships(self):
        self.req({'brief': 'x', 'config': {}})
        self.assertEqual(s.STATE['jobs'][0]['config']['video_engine'], 'flow'); self.assertEqual(s.STATE['jobs'][0]['config']['clip_seconds'], 10, 'Omni 1.2 Flash, moteur V09')
        engines.AVAILABLE = ('flow',)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req({'brief': 'x', 'config': {'video_engine': 'grok'}})
        self.assertIn('pas encore livré', json.load(e.exception)['error'])
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req({'brief': 'x', 'config': {'video_engine': 'sora'}})
        self.assertIn('inconnu', json.load(e.exception)['error'])
        engines.AVAILABLE = ('flow', 'grok')
        self.req({'brief': 'x', 'config': {'video_engine': 'grok'}})
        self.assertEqual(s.STATE['jobs'][0]['config']['clip_seconds'], 10)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg requis')
class RealMediaTests(unittest.TestCase):
    def clip(self, folder, name, seconds):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=red:s=72x128:r=10', '-f', 'lavfi', '-i', 'sine=f=440:r=16000',
                        '-t', str(seconds), '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', str(folder / name)], check=True)

    def test_qc_duration_range_per_engine(self):
        folder = pathlib.Path(tempfile.mkdtemp()); self.clip(folder, 'six.mp4', 6)
        self.assertEqual([e for e in quality.technical(folder / 'six.mp4', engines.ENGINES['grok']['range'])['hard_errors'] if 'Durée' in e], [])
        # 0.1.99: a length outside the engine's range is noted, never blocking (the clip is kept as it is at the montage).
        flow = quality.technical(folder / 'six.mp4', engines.ENGINES['flow']['range'])
        self.assertEqual([e for e in flow['hard_errors'] if 'Durée' in e], [])
        self.assertTrue(any('Durée' in n for n in flow['notes']), 'a 6 s clip is noted for Flow')

    def test_montage_keeps_real_grok_durations(self):
        s.STATE = s.fresh(); j = clip_job('grok'); folder = s.job_dir(j)
        for i, scene in enumerate(j['scenes']):
            self.clip(folder, f'clip{i}.mp4', 6); scene['clip'] = f'clip{i}.mp4'
        j.update(stage='edit', status='rendering')
        s.render_job(j['id'])
        self.assertEqual(j['status'], 'done', j['events'][-1]['text'])
        duration = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(folder / 'final.mp4')], capture_output=True, text=True).stdout)
        self.assertAlmostEqual(duration, 24, delta=0.6, msg='4 x 6 s, no frozen padding to 8 s')
        ass = (folder / 'subtitles.ass').read_text('utf-8-sig')
        self.assertIn('Dialogue: 0,0:00:18.', ass, 'last scene captions start at 18 s, not 24 s')


if __name__ == '__main__':
    unittest.main()
