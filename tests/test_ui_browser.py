"""End-to-end interface test: real server process, real Chrome (headless), rendered DOM checked. Skipped without Chrome."""
import datetime, json, os, pathlib, shutil, socket, subprocess, sys, tempfile, time, unittest, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
CHROME = next((shutil.which(x) for x in ('google-chrome', 'chromium', 'chromium-browser', 'chrome') if shutil.which(x)), None)


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0)); return probe.getsockname()[1]


@unittest.skipUnless(CHROME, 'Chrome required for the interface test')
class BrowserInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); data = pathlib.Path(cls.temp.name) / 'data'; data.mkdir()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cls.job = 'a1b2c3d4e5f60718'
        scenes = [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}]} for _ in range(2)]
        state = {'version': 1, 'token': 'test-token', 'pair_code': 'abcd1234', 'profiles': [{'id': 'flow', 'label': 'flow@example.com', 'balance': 40}],
                 'clients': {'c1': {'id': 'c1', 'label': 'Navigateur QA', 'role': 'all', 'ai_provider': 'both', 'seen': now}},
                 'settings': {'provider': 'chatgpt', 'language': 'Deutsch (de-DE)', 'scene_count': 4, 'clip_seconds': 8, 'flow_model': 'gemini_omni_flash', 'flow_resolution': '720p', 'flow_cost': 12, 'query': 'q', 'daily_budget': 50},
                 'jobs': [{'id': cls.job, 'title': 'Épisode QA', 'brief': 'b', 'stage': 'clips', 'status': 'attention', 'created': now, 'updated': now,
                           'config': {'provider': 'chatgpt', 'scene_count': 2, 'language': 'Deutsch (de-DE)', 'flow_model': 'gemini_omni_flash', 'flow_cost': 12},
                           'events': [{'at': now, 'text': 'Redémarrage : génération précédente à vérifier avant de réessayer.'}],
                           'candidates': [], 'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p'}], 'scenes': scenes, 'flow_profile': 'flow'}],
                 'tasks': [{'id': 't1', 'job': cls.job, 'kind': 'flow_video', 'slot': 'clip:1', 'status': 'failed', 'profile': 'flow', 'payload': {'prompt': 'x'},
                            'reservation': {'profile': 'flow', 'amount': 12, 'refunded': False}}]}
        (data / 'state.json').write_text(json.dumps(state), 'utf-8')
        cls.port = free_port(); env = {**os.environ, 'FRUCHT_DATA': str(data), 'FRUCHT_PORT': str(cls.port)}
        cls.server = subprocess.Popen([sys.executable, str(ROOT / 'server.py')], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(100):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{cls.port}/api/state', timeout=1).close(); break
            except OSError:
                time.sleep(.1)
        else:
            cls.server.kill(); raise RuntimeError('server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate(); cls.server.wait(10); cls.server.stderr.close(); cls.temp.cleanup()

    def dom(self, fragment=''):
        profile = pathlib.Path(self.temp.name) / 'chrome'
        result = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-sandbox', '--no-first-run', f'--user-data-dir={profile}',
                                 '--virtual-time-budget=6000', '--dump-dom', f'http://127.0.0.1:{self.port}/{fragment}'],
                                capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr[-500:]); return result.stdout

    def test_studio_renders_productions_and_online_connector(self):
        html = self.dom()
        self.assertIn('Le studio de vos histoires.', html); self.assertIn('Épisode QA', html)
        self.assertIn('1 connecteur(s) en ligne', html); self.assertIn('À vérifier', html)
        self.assertNotIn('Studio inaccessible', html)

    def test_uncertain_clip_notice_and_confirmation_button(self):
        html = self.dom('#job=' + self.job)
        self.assertIn('Envoi Flow incertain', html)
        self.assertIn('data-confirm-no-clip="clip:1"', html); self.assertIn('Scène 2 : aucun clip dans Flow', html)
        self.assertIn('Redémarrage : génération précédente à vérifier', html)

    def test_public_state_hides_token_and_lists_uncertain_scenes(self):
        state = json.load(urllib.request.urlopen(f'http://127.0.0.1:{self.port}/api/state', timeout=5))
        self.assertNotIn('token', state); self.assertEqual(state['jobs'][0]['uncertain_clips'], [1])


if __name__ == '__main__':
    unittest.main()
