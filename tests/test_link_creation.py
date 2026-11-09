"""Atelier-like creation from a TikTok link: research skipped, story inspired by the given video."""
import base64, importlib.util, json, os, pathlib, sys, tempfile, threading, time, unittest, urllib.error, urllib.request
from unittest import mock

ROOT = pathlib.Path(__file__).parents[1]
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_link', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
from tests import accounts_ready; accounts_ready.install(s)  # 0.1.91: accounts ready before starting


class LinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh()
        # Never reach TikTok from the tests: the video fetch is replaced by a local fake.
        def fake_download(url, dest, opener=None):
            if 'broken' in url:
                raise ValueError('Vidéo TikTok illisible (privée, supprimée ou page changée).')
            dest.write_bytes(b'\x00\x00\x00\x18ftypmp42'); return {'desc': 'La pomme cache une lettre', 'duration': 24, 'account': 'oma'}
        for target, value in (('download', fake_download), ('board', lambda video, out, duration: out.write_bytes(b'jpg') or True),
                              ('transcribe', lambda video, root: '[00:01] Où est la lettre ?')):
            patcher = mock.patch.object(s.source_video, target, value); patcher.start(); self.addCleanup(patcher.stop)

    def script_task(self):
        for _ in range(100):
            with s.LOCK:
                task = next((t for t in s.STATE['tasks'] if t['slot'] == 'script'), None)
            if task:
                return task
            time.sleep(.05)
        self.fail('no script task after the source analysis')

    def req(self, body):
        r = urllib.request.Request(self.base + '/api/job', data=json.dumps(body).encode(), headers={'Origin': self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def test_link_skips_research_and_drops_tracking(self):
        self.req({'brief': '', 'source_url': 'https://www.tiktok.com/@oma/video/7312345678901234567?is_from_webapp=1&sender=x', 'config': {'recreate': 'inspired'}})
        j = s.STATE['jobs'][0]
        self.assertEqual(j['stage'], 'script'); self.assertEqual(j['selected']['url'], 'https://www.tiktok.com/@oma/video/7312345678901234567')
        task = self.script_task()
        # The AI now sees the video: key-frame board attached, description and transcription in the prompt.
        self.assertEqual(task['payload']['attachments'], [f"/media/{j['id']}/source_board.jpg"])
        self.assertIn('La pomme cache une lettre', task['payload']['prompt']); self.assertIn('Où est la lettre ?', task['payload']['prompt'])
        self.assertIn('INSPIRÉE de cette vidéo', task['payload']['prompt']); self.assertIn('entièrement ORIGINALE', task['payload']['prompt'])
        self.assertTrue(any('sans copier' in e['text'] for e in j['events']))
        self.assertTrue(any('Vidéo d’origine analysée' in e['text'] for e in j['events']))

    def test_identical_with_captures_and_instructions(self):
        png = 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'0' * 20).decode()
        self.req({'brief': 'Mets ma tête à la place du père.', 'source_url': 'https://www.tiktok.com/@oma/video/7312345678901234567',
                  'config': {'recreate': 'identical'}, 'captures': [{'name': 'moi.png', 'data': png}]})
        j = s.STATE['jobs'][0]
        self.assertEqual(j['config']['recreate'], 'identical'); self.assertEqual(j['source_captures'], ['source_capture_1.png'])
        task = self.script_task()
        self.assertEqual(task['payload']['attachments'], [f"/media/{j['id']}/source_board.jpg", f"/media/{j['id']}/source_capture_1.png"])
        prompt = task['payload']['prompt']
        self.assertIn('MOTEUR V09 — COPIE FIDÈLE', prompt); self.assertIn('traduites fidèlement', prompt); self.assertNotIn('entièrement ORIGINALE', prompt)
        self.assertIn('Mets ma tête à la place du père.', prompt)
        self.assertIn('owner instructions: Mets ma tête', s.capture_note(j))
        self.assertEqual(s.captures_of(j), [f"/media/{j['id']}/source_capture_1.png"])

    def test_video_not_fetched_still_writes(self):
        self.req({'brief': '', 'source_url': 'https://www.tiktok.com/@broken/video/7312345678901234567', 'config': {}})  # FRUIT-Z by default
        task = self.script_task(); j = s.STATE['jobs'][0]
        self.assertNotIn('attachments', task['payload']); self.assertIn('seul son lien est connu', task['payload']['prompt'])
        self.assertTrue(any('Vidéo d’origine non récupérée' in e['text'] for e in j['events']))

    def test_link_defaults_to_fruit_z_mechanics(self):
        self.req({'brief': 'Plutôt à Lyon.', 'source_url': 'https://www.tiktok.com/@oma/video/7312345678901234567', 'config': {}})
        j = s.STATE['jobs'][0]
        self.assertEqual(j['config']['recreate'], 'mecanique'); self.assertEqual(j['config']['moteur'], 'fruit_z')
        self.assertEqual(j['config']['scene_count'], 8); self.assertEqual(j['config']['flow_cost'], 30)
        prompt = self.script_task()['payload']['prompt']
        self.assertIn('MOTEUR FRUIT-Z', prompt); self.assertIn('La pomme cache une lettre', prompt); self.assertIn('Plutôt à Lyon.', prompt)
        self.assertNotIn('INSPIRÉE de cette vidéo', prompt)

    def test_bad_capture_refused(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req({'brief': '', 'source_url': 'https://www.tiktok.com/@oma/video/1', 'config': {}, 'captures': [{'data': 'data:text/plain;base64,aGk='}]})
        self.assertIn('Capture illisible', json.load(e.exception)['error'])
        self.assertEqual(s.STATE['jobs'], [], 'nothing half-created')

    def test_without_link_research_runs(self):
        self.req({'brief': 'x', 'config': {}}); self.assertEqual(s.STATE['tasks'][-1]['kind'], 'tiktok_search')

    def test_refuses_other_sites(self):
        for bad in ('http://www.tiktok.com/@a/video/1', 'https://evil.example/@a/video/1', 'https://user:pw@www.tiktok.com/@a/video/1', 'javascript:alert(1)'):
            with self.subTest(bad=bad), self.assertRaises(urllib.error.HTTPError) as e:
                self.req({'brief': '', 'source_url': bad, 'config': {}})
            self.assertIn('Lien TikTok attendu', json.load(e.exception)['error'])
        self.assertEqual(s.STATE['jobs'], [])


if __name__ == '__main__':
    unittest.main()
