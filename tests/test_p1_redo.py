"""P1-3: targeted redo of one media with an owner correction. Unit and HTTP integration tests."""
import importlib.util, json, os, pathlib, tempfile, threading, unittest, urllib.error, urllib.request

TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p1_redo', pathlib.Path(__file__).parents[1] / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


def script():
    return {'title': 'Omas Reise', 'cover_title': 'WER FÄHRT?', 'description': 'Beschreibung',
            'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'Orange', 'voice': 'v', 'image_prompt': 'Orange ref'}],
            'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': f'scene {i}', 'video_prompt': f'motion {i}', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}]} for i in range(4)]}


def finished_job(**extra):
    """A finished episode: every media exists, final rendered."""
    from PIL import Image
    j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'brief': 'b', 'characters': [], 'scenes': [], 'candidates': [], 'flow_profile': 'flow',
         'config': {'scene_count': 4, 'provider': 'chatgpt', 'flow_cost': 10, 'language': 'Deutsch (de-DE)', 'flow_model': 'gemini_omni_flash'}, **extra}
    s.STATE['jobs'].append(j); s.store_script(j, script())
    folder = s.job_dir(j); j['characters'][0]['file'] = 'ref.png'; Image.new('RGB', (32, 64), 'orange').save(folder / 'ref.png')
    for i, scene in enumerate(j['scenes']):
        Image.new('RGB', (32, 64), (i * 40, 90, 160)).save(folder / f'scene{i}.png'); scene.update(image=f'scene{i}.png', clip=f'clip{i}.mp4')
    j.update(stage='done', status='done', cover_file='cover.png', cover=s.asset_url(j, 'cover.png'), final=s.asset_url(j, 'final.mp4'), qc={'export': 'ok'})
    s.STATE['profiles'].append({'id': 'flow', 'label': 'Flow', 'balance': 100})
    return j


def active():
    return [t for t in s.STATE['tasks'] if t['status'] in ('queued', 'claimed')]


class RedoTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh(); self._render = s.start_render; self.renders = []; s.start_render = self.renders.append

    def tearDown(self):
        s.start_render = self._render

    def test_redo_cover_with_correction_keeps_everything_else(self):
        j = finished_job(); scenes = json.dumps(j['scenes'])
        s.redo(j, 'cover', '  plus   de lumière ')
        self.assertEqual(j['stage'], 'cover'); self.assertNotIn('final', j); self.assertNotIn('cover_file', j); self.assertNotIn('qc', j)
        task = active()[0]; self.assertEqual(task['slot'], 'cover')
        self.assertIn('Owner correction for this new attempt (apply it, keep everything else unchanged): plus de lumière', task['payload']['prompt'])
        self.assertEqual(json.dumps(j['scenes']), scenes); self.assertEqual(j['redo_history'][-1]['file'], 'cover.png')
        self.assertEqual(self.renders, [])

    def test_redo_clip_regenerates_only_that_scene_with_correction(self):
        j = finished_job(); s.redo(j, 'clip:2', 'sans musique')
        self.assertEqual(j['stage'], 'clips'); task = active()[0]
        self.assertEqual((task['kind'], task['slot']), ('flow_video', 'clip:2'))
        self.assertIn('sans musique', task['payload']['prompt'])
        self.assertEqual([sc.get('clip') for sc in j['scenes']], ['clip0.mp4', 'clip1.mp4', None, 'clip3.mp4'])

    def test_redo_image_requires_clip_together(self):
        j = finished_job()
        with self.assertRaisesRegex(ValueError, 'refaites l’image et le clip ensemble'):
            s.redo(j, 'image:1', 'autre angle')
        self.assertEqual(j['scenes'][1]['image'], 'scene1.png'); self.assertEqual(j['status'], 'done')
        s.redo(j, 'image:1', 'autre angle', include_clip=True)
        self.assertEqual(j['stage'], 'images'); task = active()[0]
        self.assertEqual(task['slot'], 'image:1'); self.assertIn('autre angle', task['payload']['prompt'])
        self.assertNotIn('clip', j['scenes'][1]); self.assertEqual(j['corrections']['clip:1'], 'autre angle')
        self.assertEqual({h['slot'] for h in j['redo_history']}, {'image:1', 'clip:1'})

    def test_previous_failed_submissions_do_not_become_uncertain(self):
        j = finished_job()
        old = {'id': 'old', 'job': j['id'], 'kind': 'flow_video', 'slot': 'clip:0', 'status': 'failed', 'reservation': {'profile': 'flow', 'amount': 10, 'refunded': False}}
        s.STATE['tasks'].append(old); s.redo(j, 'clip:0')
        self.assertTrue(old['acknowledged']); self.assertEqual(s.uncertain_clip_tasks(j), [])
        self.assertEqual(active()[0]['slot'], 'clip:0')

    def test_correction_removed_when_redone_without_note(self):
        j = finished_job(); s.redo(j, 'cover', 'rouge'); active()[0]['status'] = 'done'
        j['cover_file'] = 'cover2.png'; s.redo(j, 'cover')
        self.assertNotIn('cover', j.get('corrections', {})); self.assertNotIn('Owner correction', active()[-1]['payload']['prompt'])

    def test_characters_locked_once_scenes_exist(self):
        j = finished_job()
        with self.assertRaisesRegex(ValueError, 'refaites plutôt les images'):
            s.redo(j, 'character:orange')
        for scene in j['scenes']:
            scene.pop('image'); scene.pop('clip')
        j['stage'] = 'images'; s.redo(j, 'character:orange', 'plus jeune')
        self.assertEqual(j['stage'], 'characters'); self.assertEqual(active()[0]['slot'], 'character:orange')
        self.assertIn('plus jeune', active()[0]['payload']['prompt'])

    def test_refused_while_busy_or_invalid(self):
        j = finished_job()
        for slot, message in (('image:9', 'Scène inconnue'), ('video:1', 'inconnu'), ('character:ghost', 'Personnage inconnu')):
            with self.subTest(slot=slot), self.assertRaisesRegex(ValueError, message):
                s.redo(j, slot)
        s.STATE['tasks'].append({'id': 'x', 'job': j['id'], 'kind': 'chat_image', 'slot': 'cover', 'status': 'claimed'})
        with self.assertRaisesRegex(ValueError, 'tâche est en cours'):
            s.redo(j, 'cover')
        s.STATE['tasks'] = []; j['status'] = 'rendering'
        with self.assertRaisesRegex(ValueError, 'Montage en cours'):
            s.redo(j, 'cover')
        self.assertEqual(j['cover_file'], 'cover.png')

    def test_note_is_bounded(self):
        j = finished_job(); s.redo(j, 'cover', 'x' * 900); self.assertEqual(len(j['corrections']['cover']), 500)

    def test_redo_before_final_does_not_move_stage_forward(self):
        j = finished_job(); j['stage'] = 'images'; j['status'] = 'attention'; j['scenes'][3].pop('clip'); j['scenes'][3].pop('image')
        s.redo(j, 'cover'); self.assertEqual(j['stage'], 'images', 'earlier stage kept'); self.assertEqual(active()[0]['slot'], 'image:3')


class RedoHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh()

    def req(self, path, body, origin=None):
        request = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={'Origin': origin or self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(request) as r:
            return json.load(r)

    def test_redo_action_and_errors(self):
        j = finished_job(); path = '/api/job/' + j['id']
        state = self.req(path, {'action': 'redo', 'slot': 'clip:1', 'note': 'plus lent'})
        self.assertEqual(next(x for x in state['jobs'] if x['id'] == j['id'])['stage'], 'clips')
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req(path, {'action': 'redo', 'slot': 'cover'})
        self.assertIn('tâche est en cours', json.load(e.exception)['error'])
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req(path, {'action': 'redo', 'slot': 'cover'}, origin='https://evil.example')
        self.assertEqual(e.exception.code, 403)


if __name__ == '__main__':
    unittest.main()
