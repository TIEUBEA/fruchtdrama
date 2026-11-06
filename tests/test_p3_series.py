"""P3: series continuation reusing paid character images, publication kit."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p3', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import series

CAST = [{'id': 'orange', 'name': 'Oma Orange', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p'}, {'id': 'kiwi', 'name': 'Kiko', 'appearance': 'k', 'voice': 'v', 'image_prompt': 'p'}]


def done_job(language='Deutsch (de-DE)'):
    from PIL import Image
    scenes = [{'characters': ['orange'], 'meaning': 'Le gâteau a disparu', 'image_prompt': 'i', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Wo ist mein Kuchen?'}]}]
    j = {'id': s.uid(), 'title': 'Omas Kuchen', 'stage': 'done', 'status': 'done', 'events': [], 'brief': 'b', 'candidates': [], 'flow_profile': None,
         'editorial_version': 2, 'retention_version': 1, 'character_sheet': 1, 'selected': {'title': 'Ref', 'url': 'https://www.tiktok.com/@a/video/1'},
         'characters': [dict(c, file='sheet.png') for c in CAST], 'scenes': scenes,
         'script': {'title': 'Omas Kuchen', 'description': 'Oma sucht ihren Kuchen.', 'cover_title': 'WER?', 'characters': CAST, 'scenes': scenes},
         'config': {'scene_count': 4, 'provider': 'chatgpt', 'flow_cost': 12, 'language': language, 'video_engine': 'flow', 'dry_run': True}}
    s.STATE['jobs'].append(j); Image.new('RGB', (32, 64), 'orange').save(s.job_dir(j) / 'sheet.png'); return j


class KitTests(unittest.TestCase):
    def test_kit_per_language_and_part(self):
        s.STATE = s.fresh(); j = done_job()
        k = series.kit(j)
        self.assertEqual(k['title'], 'Omas Kuchen'); self.assertIn('#fürdich', k['hashtags']); self.assertIn('#OmaOrange', k['hashtags'])
        self.assertEqual(k['slots']['zone'], 'Europe/Berlin'); self.assertIn('aucune garantie', k['note'])
        j['series'] = {'part': 2}; j['config']['language'] = 'Français (fr-FR)'
        k = series.kit(j); self.assertEqual(k['title'], 'Omas Kuchen (Partie 2)'); self.assertIn('#Partie2', k['hashtags']); self.assertLessEqual(len(k['hashtags']), 10)
        self.assertIn('#Partie2', series.kit_text(k))

    def test_brief(self):
        s.STATE = s.fresh(); text = series.brief(done_job(), 'Kiko avoue')
        for part in ('partie 2', 'Omas Kuchen', '"orange"', 'Wo ist mein Kuchen?', 'Kiko avoue'):
            self.assertIn(part, text)


class SeriesFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def req(self, path, body):
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={'Origin': self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def test_next_part_reuses_cast_images(self):
        s.STATE = s.fresh(); prev = done_job()
        state = self.req('/api/job/' + prev['id'], {'action': 'continue_series', 'note': 'Kiko avoue'})
        nxt = s.job_by(state['created'])
        self.assertEqual(nxt['stage'], 'script'); self.assertEqual(nxt['series'], {'id': prev['id'], 'part': 2, 'previous': prev['id']})
        self.assertFalse(nxt['config']['dry_run']); self.assertIn('Kiko avoue', nxt['brief'])
        task = [t for t in s.STATE['tasks'] if t['job'] == nxt['id']][-1]; self.assertEqual(task['slot'], 'script'); task['status'] = 'done'
        script = {'title': 'Omas Kuchen 2', 'cover_title': 'WER?', 'description': 'd', 'characters': CAST + [{'id': 'plum', 'name': 'Pia', 'appearance': 'p', 'voice': 'v', 'image_prompt': 'p'}],
                  'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': f'Neue Spur {i}'}]} for i in range(4)]}
        nxt['editorial_version'] = 1; s.store_script(nxt, script)
        files = {c['id']: c.get('file') for c in nxt['characters']}
        self.assertTrue(files['orange'].startswith('ref_orange_p1')); self.assertIsNone(files['plum'])
        self.assertTrue((s.job_dir(nxt) / files['orange']).is_file()); self.assertIn('aucune image repayée', ' '.join(e['text'] for e in nxt['events']))
        nxt['status'] = 'running'; s.schedule(nxt)
        slots = [t['slot'] for t in s.STATE['tasks'] if t['job'] == nxt['id'] and t['status'] == 'queued']
        self.assertEqual(slots, ['character:plum'], 'only the new character is paid; no new sheet')

    def test_only_finished_episode(self):
        s.STATE = s.fresh(); j = done_job(); j['status'] = 'running'
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/job/' + j['id'], {'action': 'continue_series'})
        self.assertIn('Terminez', json.load(e.exception)['error'])


if __name__ == '__main__':
    unittest.main()
