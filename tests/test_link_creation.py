"""Atelier-like creation from a TikTok link: research skipped, story inspired by the given video."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_link', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


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

    def req(self, body):
        r = urllib.request.Request(self.base + '/api/job', data=json.dumps(body).encode(), headers={'Origin': self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def test_link_skips_research_and_drops_tracking(self):
        self.req({'brief': '', 'source_url': 'https://www.tiktok.com/@oma/video/7312345678901234567?is_from_webapp=1&sender=x', 'config': {}})
        j = s.STATE['jobs'][0]
        self.assertEqual(j['stage'], 'script'); self.assertEqual(j['selected']['url'], 'https://www.tiktok.com/@oma/video/7312345678901234567')
        task = s.STATE['tasks'][-1]; self.assertEqual(task['slot'], 'script')
        self.assertIn('7312345678901234567', task['payload']['prompt'])
        self.assertTrue(any('sans copier' in e['text'] for e in j['events']))

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
