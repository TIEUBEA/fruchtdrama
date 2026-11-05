"""P1-1: read and correct the story before any image is paid. Unit and HTTP integration tests."""
import importlib.util, json, os, pathlib, tempfile, threading, unittest, urllib.error, urllib.request

TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p1_review', pathlib.Path(__file__).parents[1] / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


def script(n=4):
    return {'title': 'Omas Reise', 'cover_title': 'MUSS OMA GEHEN?', 'description': 'Eine originelle KI-Geschichte.',
            'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'Orange', 'voice': 'Warm', 'image_prompt': 'Orange'},
                           {'id': 'kiwi', 'name': 'Kiko', 'appearance': 'Kiwi', 'voice': 'Jung', 'image_prompt': 'Kiwi'}],
            'scenes': [{'characters': ['orange', 'kiwi'], 'meaning': f'Moment {i}', 'image_prompt': 'p', 'video_prompt': 'v',
                        'dialogue': [{'speaker': 'orange', 'text': 'Wir fahren heute ans Meer.'}, {'speaker': 'kiwi', 'text': 'Ohne mich?'}]} for i in range(n)]}


def review_job(review=True, **extra):
    j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'brief': 'b', 'characters': [], 'scenes': [], 'candidates': [], 'flow_profile': None,
         'config': {'scene_count': 4, 'provider': 'chatgpt', 'flow_cost': 10, 'language': 'Deutsch (de-DE)', 'review_script': review}, **extra}
    s.STATE['jobs'].append(j); s.store_script(j, script()); s.schedule(j); return j


def queued():
    return [t for t in s.STATE['tasks'] if t['status'] == 'queued']


def lines(*texts):
    return [{'dialogue': [{'speaker': 'orange', 'text': t}, {'speaker': 'kiwi', 'text': 'Ohne mich?'}]} for t in texts]


class ReviewGateTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_story_waits_for_owner_before_any_image(self):
        j = review_job()
        self.assertEqual(j['status'], 'waiting_review'); self.assertEqual(queued(), [])
        self.assertIn('relisez', j['events'][-1]['text'])
        s.schedule(j); self.assertEqual(queued(), [], 'gate holds on every schedule')

    def test_without_option_production_stays_fully_automatic(self):
        j = review_job(review=False)
        self.assertEqual(j['status'], 'running'); self.assertEqual([t['slot'] for t in queued()], ['character:orange'])

    def test_resume_does_not_bypass_review(self):
        j = review_job(); j['status'] = 'running'; s.schedule(j)
        self.assertEqual(j['status'], 'waiting_review'); self.assertEqual(queued(), [])

    def test_edit_updates_script_scenes_and_files(self):
        j = review_job()
        changed = s.edit_script(j, {'title': ' Neuer Titel ', 'description': 'Neue Beschreibung', 'scenes': lines('Halt!', 'Warte  bitte.', 'Komm zurück.', 'Danke dir.')})
        self.assertTrue(changed); self.assertEqual(j['title'], 'Neuer Titel'); self.assertEqual(j['script']['title'], 'Neuer Titel')
        self.assertEqual(j['scenes'][1]['dialogue'][0]['text'], 'Warte bitte.', 'whitespace normalised')
        self.assertEqual(j['script']['scenes'][0]['dialogue'][0]['text'], 'Halt!')
        folder = s.job_dir(j)
        self.assertEqual(json.loads((folder / 'scenario.json').read_text('utf-8'))['title'], 'Neuer Titel')
        self.assertEqual((folder / 'description.txt').read_text('utf-8'), 'Neue Beschreibung')
        self.assertEqual(j['scenes'][0]['image_prompt'], 'p', 'prompts untouched')

    def test_unchanged_edit_is_a_no_op(self):
        j = review_job(); count = len(j['events'])
        self.assertFalse(s.edit_script(j, {'title': 'Omas Reise'})); self.assertEqual(len(j['events']), count)

    def test_invalid_edits_are_rejected_without_change(self):
        j = review_job(); before = json.dumps(j['script'])
        cases = [
            ({'title': '  '}, 'Titre'),
            ({'scenes': lines('a', 'b')}, 'Une correction par scène'),
            ({'scenes': lines('', 'b', 'c', 'd')}, 'Dialogue'),
            ({'scenes': [{'dialogue': [{'speaker': 'ghost', 'text': 'Hallo'}]}] * 4}, 'locuteur'),
            ({'scenes': lines(' '.join(['Wort'] * 26), 'b', 'c', 'd')}, '25 mots'),
            ({'scenes': 'texte'}, 'Une correction par scène'),
        ]
        for change, message in cases:
            with self.subTest(change=str(change)[:40]):
                with self.assertRaisesRegex(ValueError, message):
                    s.edit_script(j, change)
                self.assertEqual(json.dumps(j['script']), before)

    def test_retention_productions_keep_twenty_word_limit(self):
        j = review_job(editorial_version=0, retention_version=1)
        j['editorial_version'] = 2
        with self.assertRaisesRegex(ValueError, '20 mots'):
            s.edit_script(j, {'scenes': lines(' '.join(['Wort'] * 19), 'b', 'c', 'd')})

    def test_story_locked_once_images_started(self):
        j = review_job(); j['script_approved'] = s.now(); j['status'] = 'running'; s.schedule(j)
        with self.assertRaisesRegex(ValueError, 'ne peut plus être modifiée'):
            s.edit_script(j, {'title': 'Neu'})
        self.assertEqual(j['title'], 'Omas Reise')


class ReviewHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh()

    def req(self, path, body=None, origin=None):
        request = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                                         headers={'Origin': origin or self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request) as r:
            return json.load(r)

    def test_option_is_stored_as_boolean(self):
        self.req('/api/job', {'brief': 'x', 'config': {'review_script': 'yes'}}); self.assertIs(s.STATE['jobs'][0]['config']['review_script'], True)
        self.req('/api/job', {'brief': 'x', 'config': {}}); self.assertIs(s.STATE['jobs'][0]['config']['review_script'], False)

    def test_edit_then_approve_starts_images(self):
        j = review_job(); path = '/api/job/' + j['id']
        self.req(path, {'action': 'edit_script', 'script': {'cover_title': 'WER FÄHRT MIT?'}})
        self.assertEqual(j['script']['cover_title'], 'WER FÄHRT MIT?'); self.assertEqual(j['status'], 'waiting_review')
        self.req(path, {'action': 'approve_script'})
        self.assertTrue(j['script_approved']); self.assertEqual(j['status'], 'running')
        self.assertEqual([t['slot'] for t in queued()], ['character:orange'])
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req(path, {'action': 'approve_script'})
        self.assertIn('Aucune histoire', json.load(e.exception)['error'])
        with self.assertRaises(urllib.error.HTTPError):
            self.req(path, {'action': 'edit_script', 'script': {'title': 'Trop tard'}})

    def test_foreign_origin_cannot_edit_or_approve(self):
        j = review_job()
        for body in ({'action': 'edit_script', 'script': {'title': 'pirate'}}, {'action': 'approve_script'}):
            with self.assertRaises(urllib.error.HTTPError) as e:
                self.req('/api/job/' + j['id'], body, origin='https://evil.example')
            self.assertEqual(e.exception.code, 403)
        self.assertEqual(j['title'], 'Omas Reise'); self.assertEqual(j['status'], 'waiting_review')


if __name__ == '__main__':
    unittest.main()
