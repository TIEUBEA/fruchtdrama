"""Atelier lot 5 (03/11/2026): Filon niches with their own search, task and montage timestamps for the 6 h counts."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_lot5', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


class Niches(unittest.TestCase):
    def test_queries(self):
        for lang, q in s.RESEARCH_QUERIES.items():
            self.assertEqual(s.niche_query('Fruits', lang), q, 'Fruits keeps the historical search')
        self.assertEqual(s.niche_query('Animaux', 'Français (fr-FR)'), 'histoire animaux IA')
        self.assertEqual(s.niche_query('Animaux', 'Deutsch (de-DE)'), 'Tiere KI Geschichte')
        self.assertEqual(s.niche_query('Dinosaures', 'English (en-US)'), 'AI Dinosaures story', 'own niche used as typed')
        for bad in ('', 'x', 'a' * 31, '<script>', 'a/b'):
            with self.assertRaises(ValueError):
                s.niche_name(bad)
        self.assertEqual(s.niche_name('  Avatar   humain '), 'Avatar humain')

    def test_research_results_are_tagged_with_the_niche(self):
        s.STATE = s.fresh()
        j = s.filon_refresh('Français (fr-FR)', 'Chats')
        self.assertEqual((j['config']['filon_niche'], j['config']['query']), ('Chats', 'histoire chats IA'))
        s.apply_research(j, [{'url': 'https://www.tiktok.com/@a/video/1', 'title': 't', 'views': 10, 'metric_kind': 'views', 'age_days': 1}])
        self.assertTrue(j['candidates']); self.assertEqual({c['niche'] for c in j['candidates']}, {'Chats'})

    def test_done_tasks_are_timestamped(self):
        s.STATE = s.fresh()
        j = s.filon_refresh('Français (fr-FR)', 'Fruits')
        t = next(t for t in s.STATE['tasks'] if t['job'] == j['id']); t['status'] = 'claimed'
        s.accept_task_result(t, {'ok': True, 'candidates': [{'url': 'https://www.tiktok.com/@a/video/2', 'title': 't', 'views': 10, 'metric_kind': 'views', 'age_days': 1}]})
        self.assertEqual(t['status'], 'done')
        self.assertTrue(t['done_at'], 'counted in the Studio "en 6 h"')


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port; cls.base = f'http://127.0.0.1:{s.PORT}'
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def post(self, body):
        r = urllib.request.Request(self.base + '/api/filon', data=json.dumps(body).encode(), headers={'Origin': self.base, 'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(r).read())

    def test_my_niches(self):
        s.STATE = s.fresh()
        st = self.post({'niches': ['Fruits', 'Animaux', 'Fruits']})
        self.assertEqual(st['settings']['filon_niches'], ['Fruits', 'Animaux'], 'no duplicate')
        self.post({'niche': 'Animaux'}); self.assertEqual(s.STATE['settings']['filon_niche'], 'Animaux')
        self.post({'niches': ['Fruits']}); self.assertEqual(s.STATE['settings']['filon_niche'], 'Fruits', 'removed niche no longer current')
        for bad in ({'niches': []}, {'niches': [f'Niche {i}' for i in range(9)]}, {'niches': ['<b>']}, {'niche': '/'}):
            with self.assertRaises(urllib.error.HTTPError):
                self.post(bad)
        self.post({'refresh': True, 'niche': 'Bébés', 'language': 'Français (fr-FR)'})
        j = next(j for j in s.STATE['jobs'] if j.get('filon_only'))
        self.assertEqual((j['config']['filon_niche'], j['config']['query']), ('Bébés', 'histoire bébé IA'))


if __name__ == '__main__':
    unittest.main()
