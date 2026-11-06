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
        cls.job = 'a1b2c3d4e5f60718'; cls.review = 'b1b2c3d4e5f60718'
        scenes = [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}]} for _ in range(2)]
        state = {'version': 1, 'token': 'test-token', 'pair_code': 'abcd1234', 'sites': {'chatgpt': {'connected': True}, 'grok': {'connected': True}}, 'profiles': [{'id': 'flow', 'label': 'flow@example.com', 'balance': 40}],
                 'engine_accounts': [{'id': 'g1', 'engine': 'grok', 'label': 'g@x.com', 'email': 'g@x.com', 'wall': {'at': now, 'until': time.time() + 7200, 'until_text': now, 'message': 'limit'}}],
                 'clients': {'c1': {'id': 'c1', 'label': 'Navigateur QA', 'role': 'all', 'ai_provider': 'both', 'seen': now}},
                 'settings': {'provider': 'chatgpt', 'language': 'Deutsch (de-DE)', 'scene_count': 4, 'clip_seconds': 8, 'flow_model': 'gemini_omni_flash', 'flow_resolution': '720p', 'flow_cost': 12, 'query': 'q', 'daily_budget': 50},
                 'jobs': [{'id': cls.job, 'title': 'Épisode QA', 'brief': 'b', 'stage': 'clips', 'status': 'attention', 'created': now, 'updated': now,
                           'config': {'provider': 'chatgpt', 'scene_count': 2, 'language': 'Deutsch (de-DE)', 'flow_model': 'gemini_omni_flash', 'flow_cost': 12},
                           'events': [{'at': now, 'text': 'Redémarrage : génération précédente à vérifier avant de réessayer.'}],
                           'candidates': [], 'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p', 'file': 'sheet.png'}, {'id': 'kiwi', 'name': 'Kiko', 'appearance': 'k', 'voice': 'v', 'image_prompt': 'p', 'file': 'sheet.png'}], 'character_sheet': 1, 'character_sheet_file': 'sheet.png', 'scenes': scenes, 'flow_profile': 'flow',
                           'script': {'title': 'Épisode QA', 'cover_title': 'WER?', 'description': 'd', 'characters': [], 'scenes': scenes, 'state_changes': [{'from_scene': 2, 'character': 'orange', 'change': 'tablier déchiré'}]},
                           'state_sheets': [{'from_scene': 2, 'character': 'orange', 'change': 'tablier déchiré', 'file': 'state.png'}]},
                          {'id': cls.review, 'title': 'Histoire à relire QA', 'brief': 'b', 'stage': 'characters', 'status': 'waiting_review', 'created': now, 'updated': now,
                           'config': {'provider': 'chatgpt', 'scene_count': 2, 'language': 'Deutsch (de-DE)', 'flow_model': 'gemini_omni_flash', 'flow_cost': 12, 'review_script': True},
                           'events': [], 'candidates': [], 'flow_profile': 'flow', 'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p'}], 'scenes': scenes,
                           'script': {'title': 'Histoire à relire QA', 'cover_title': 'WER FÄHRT?', 'description': 'Beschreibung QA', 'characters': [], 'scenes': scenes}}],
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
        self.assertIn('Le Filon', self.dom(), 'Le Filon opens the application, like the Atelier')
        html = self.dom('#page=studio')
        self.assertIn('Tes histoires et leurs parties.', html); self.assertIn('class="story-card"', html); self.assertIn('ÉPISODE QA', html)
        self.assertIn('1 connecteur(s) en ligne', html); self.assertIn('Tourner', html, 'next action with its direct button')
        self.assertNotIn('Studio inaccessible', html)
        self.assertIn('Grok bloqué par le quota jusqu’à', html, 'wall banner on every page'); self.assertIn('data-wall-wait=', html); self.assertIn('data-forget-wall="g1"', html)

    def test_uncertain_clip_notice_and_confirmation_button(self):
        html = self.dom('#job=' + self.job)
        self.assertIn('Envoi Flow incertain', html)
        self.assertIn('data-confirm-no-clip="clip:1"', html); self.assertIn('Scène 2 : aucun clip dans Flow', html)
        self.assertIn('Redémarrage : génération précédente à vérifier', html)
        self.assertIn('Feuille commune : Oma, Kiko', html); self.assertEqual(html.count('data-upload="characters"'), 1)
        self.assertNotIn('data-upload="character:kiwi"', html)

    def test_story_states_section_like_the_atelier(self):
        html = self.dom('#job=' + self.job)
        self.assertIn('Au fil de l’histoire', html); self.assertIn('Dès la scène 2', html); self.assertIn('OMA : tablier déchiré', html)
        self.assertIn(f'/media/{self.job}/state.png', html); self.assertIn('data-redo="state:0"', html)

    def test_story_review_editor_before_images(self):
        html = self.dom('#job=' + self.review)
        self.assertIn('Relisez l’histoire avant de payer les images', html); self.assertIn('Histoire à relire', html)
        self.assertIn('data-speaker="orange"', html); self.assertIn('value="Hallo"', html)
        self.assertIn('value="WER FÄHRT?"', html); self.assertIn('data-action="approveScript"', html)
        self.assertIn('data-dry-run="1"', html, 'dry run can be enabled before clips')

    def test_create_form_offers_review_option(self):
        html = self.dom('#page=create'); self.assertIn('id="createForm"', html); self.assertIn('name="auto"', html); self.assertIn('name="dry_run"', html)
        for word in ('Pas d’idée', 'J’ai une idée', 'Refaire une virale', '1 min', '2 min', '3 min', 'Propose-moi dix histoires'):
            self.assertIn(word, html)

    def test_public_state_hides_token_and_lists_uncertain_scenes(self):
        state = json.load(urllib.request.urlopen(f'http://127.0.0.1:{self.port}/api/state', timeout=5))
        self.assertNotIn('token', state); self.assertEqual(state['jobs'][0]['uncertain_clips'], [1]); self.assertEqual(state['jobs'][1]['uncertain_clips'], [])


if __name__ == '__main__':
    unittest.main()
