"""Atelier-like versions of an episode: horizontal 16:9 and other languages."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_variants', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import quality


def episode():
    from PIL import Image
    sc = {'title': 'T', 'cover_title': 'C', 'description': 'd IA', 'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p'}],
          'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'Oma in the kitchen, portrait 9:16', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo Oma'}]} for _ in range(3)]}
    j = {'id': s.uid(), 'title': 'T', 'brief': 'b', 'stage': 'done', 'status': 'done', 'events': [], 'candidates': [], 'flow_profile': None, 'script': sc,
         'config': {'scene_count': 3, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)', 'clip_seconds': 8},
         'characters': [dict(sc['characters'][0], file='ref.png')], 'scenes': [dict(x, image=f's{i}.png', clip=f'c{i}.mp4') for i, x in enumerate(sc['scenes'])]}
    s.STATE['jobs'].append(j); d = s.job_dir(j)
    for f in ('ref.png', 's0.png', 's1.png', 's2.png'):
        Image.new('RGB', (32, 64), 'orange').save(d / f)
    return j


class VariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh()

    def req(self, path, body):
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={'Origin': self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def error(self, path, body):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req(path, body)
        return json.load(e.exception).get('error')

    def test_horizontal_redraws_boards_in_landscape(self):
        j = episode()
        st = self.req('/api/job/' + j['id'], {'action': 'variant', 'kind': 'horizontal'})
        v = s.job_by(st['created'])
        self.assertEqual(v['config']['format'], 'horizontal'); self.assertEqual(v['stage'], 'images'); self.assertEqual(v['variant']['of'], j['id'])
        self.assertTrue((s.job_dir(v) / 'ref.png').is_file()); self.assertFalse(any(x.get('image') for x in v['scenes']))
        t = next(t for t in s.STATE['tasks'] if t['job'] == v['id'] and t['kind'] == 'chat_image')
        self.assertIn('landscape 16:9', t['payload']['prompt']); self.assertNotIn('9:16', t['payload']['prompt']); self.assertEqual(t['payload']['aspect'], '16:9')
        self.assertEqual(s.frame_size(v), (1920, 1080))
        self.assertIn('planches', self.error('/api/job/' + v['id'], {'action': 'variant', 'kind': 'horizontal'}), 'no boards yet')
        v['scenes'][0]['image'] = 's0.png'
        self.assertIn('déjà horizontal', self.error('/api/job/' + v['id'], {'action': 'variant', 'kind': 'horizontal'}))

    def test_language_keeps_boards_and_remakes_clips(self):
        j = episode()
        self.assertIn('autre langue', self.error('/api/job/' + j['id'], {'action': 'variant', 'kind': 'language', 'language': 'Deutsch (de-DE)'}))
        st = self.req('/api/job/' + j['id'], {'action': 'variant', 'kind': 'language', 'language': 'Français (fr-FR)'})
        v = s.job_by(st['created'])
        t = next(t for t in s.STATE['tasks'] if t['job'] == v['id'])
        self.assertEqual(t['slot'], 'script'); self.assertIn('Français (fr-FR)', t['payload']['prompt']); self.assertIn('Hallo Oma', t['payload']['prompt'])
        translated = json.loads(json.dumps(j['script'])); translated['production_id'] = v['id']; translated['title'] = 'La mamie'
        for x in translated['scenes']:
            x['dialogue'][0]['text'] = 'Bonjour mamie'
        t['status'] = 'claimed'; s.accept_task_result(t, {'ok': True, 'text': json.dumps(translated)})
        self.assertEqual([x.get('image') for x in v['scenes']], ['s0.png', 's1.png', 's2.png'], 'same boards')
        self.assertEqual(v['characters'][0]['file'], 'ref.png'); self.assertEqual(v['stage'], 'clips')
        self.assertFalse(any(x.get('clip') for x in v['scenes']), 'clips made again with new voices')

    def test_orientation_checks(self):
        self.assertEqual(s.landscape('A shot, portrait 9:16, vertical framing'), 'A shot, landscape 16:9, horizontal framing')
        self.assertEqual(s.frame_size({'config': {}}), (1080, 1920))


if __name__ == '__main__':
    unittest.main()
