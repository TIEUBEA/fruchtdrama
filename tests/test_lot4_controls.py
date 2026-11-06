"""Atelier lot 4 (03/11/2026): board check before the clips, clips checked by ear only, settings."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_lot4', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
from tests import accounts_ready; accounts_ready.install(s)  # 0.1.91: accounts ready before starting
import board_check, quality

BRIEF = 'Une orange cache la vérité à sa famille depuis dix ans.'


def job(n=6, **config):
    from PIL import Image
    j = {'id': s.uid(), 'stage': 'images', 'status': 'running', 'events': [], 'brief': 'b', 'candidates': [], 'flow_profile': None, 'quality_version': 1,
         'title': 'T', 'script': {'title': 'T', 'cover_title': 'C', 'description': 'd'},
         'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p', 'file': 'ref.png'}],
         'scenes': [{'characters': ['orange'], 'meaning': f'm{i}', 'image_prompt': 'i', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}], 'image': f's{i}.png'} for i in range(n)],
         'config': {'scene_count': n, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)', 'video_engine': 'grok', 'clip_seconds': 6, **config}}
    s.STATE = s.fresh(); s.STATE['jobs'].append(j); folder = s.job_dir(j)
    Image.new('RGB', (64, 112), 'orange').save(folder / 'ref.png')
    for i in range(n):
        Image.new('RGB', (64, 112), (30 * i, 80, 160)).save(folder / f's{i}.png')
    return j


def answer(j, statuses):
    t = next(t for t in s.STATE['tasks'] if t['job'] == j['id'] and t['slot'] == 'board_review')
    t['status'] = 'done'
    text = json.dumps({'production_id': j['id'], 'generation_task_id': t['id'], 'board_review': {'boards': [{'index': i, 'status': st, 'detail': 'personnage en trop' if st == 'issue' else 'ok'} for i, st in enumerate(statuses)]}})
    s.accept_task_result(t, {'ok': True, 'text': text})
    return t


class BoardCheck(unittest.TestCase):
    def test_off_by_default_goes_to_clips(self):
        j = job(); s.schedule(j)
        self.assertEqual(j['stage'], 'clips'); self.assertFalse(any(t['slot'] == 'board_review' for t in s.STATE['tasks']))

    def test_redo_redraws_failing_boards_once(self):
        j = job(board_controls='redo'); s.schedule(j)
        t = next(t for t in s.STATE['tasks'] if t['slot'] == 'board_review')
        self.assertEqual(j['stage'], 'images')
        sheets = [a for a in t['payload']['attachments'] if 'board-check' in a]
        self.assertEqual(len(sheets), 2, 'six boards: one attachment for five boards')
        self.assertIn(j['id'], t['payload']['prompt'])
        answer(j, ['pass', 'issue', 'pass', 'issue', 'pass', 'pass'])
        self.assertEqual([i for i, x in enumerate(j['scenes']) if not x.get('image')], [1, 3])
        self.assertIn('personnage en trop', j['corrections']['image:1'])
        queued = [t for t in s.STATE['tasks'] if t['job'] == j['id'] and t['status'] == 'queued']
        # 0.1.89: boards redrawn one after the other on the chat lane; the validated board 1 is already animated.
        self.assertEqual([t['slot'] for t in queued], ['image:1', 'clip:0'], 'boards redrawn one after the other, validated board animated meanwhile')
        self.assertIn('personnage en trop', queued[0]['payload']['prompt'], 'reason sent with the new attempt')
        self.assertEqual(sum(1 for h in j['redo_history'] if h['note'] == 'contrôle des planches'), 2)
        for i in (1, 3):
            j['scenes'][i]['image'] = f's{i}.png'
        for t in queued:
            t['status'] = 'done'
        s.schedule(j)
        self.assertEqual(j['stage'], 'clips', 'checked once: no second review')
        self.assertEqual(sum(1 for t in s.STATE['tasks'] if t['slot'] == 'board_review'), 1)

    def test_at_most_four_redrawn(self):
        j = job(board_controls='redo'); s.schedule(j); answer(j, ['issue'] * 6)
        self.assertEqual(sum(1 for x in j['scenes'] if not x.get('image')), board_check.MAX_REDRAW)

    def test_report_only_continues(self):
        j = job(board_controls='report'); s.schedule(j); answer(j, ['pass', 'issue', 'pass', 'pass', 'pass', 'pass'])
        self.assertEqual(j['stage'], 'clips'); self.assertTrue(all(x.get('image') for x in j['scenes']))
        self.assertTrue(any('Planches signalées' in e['text'] and 'planche 2' in e['text'] for e in j['events']))

    def test_invalid_answer_is_refused(self):
        j = job(n=2, board_controls='redo'); s.schedule(j)
        t = next(t for t in s.STATE['tasks'] if t['slot'] == 'board_review')
        for bad in ({'production_id': j['id'], 'generation_task_id': 'x', 'board_review': {'boards': []}},
                    {'production_id': j['id'], 'generation_task_id': t['id'], 'board_review': {'boards': [{'index': 0, 'status': 'pass', 'detail': 'ok'}]}},
                    {'production_id': j['id'], 'generation_task_id': t['id'], 'board_review': {'boards': [{'index': 0, 'status': 'maybe', 'detail': 'ok'}, {'index': 1, 'status': 'pass', 'detail': 'ok'}]}}):
            with self.assertRaises(ValueError):
                board_check.validate(bad, j, t['id'])


class ClipLook(unittest.TestCase):
    def test_ear_only_skips_the_visual_review_and_says_so(self):
        j = job(n=1, clip_look='ear'); j['stage'] = 'quality'; folder = s.job_dir(j); (folder / 'c.mp4').write_bytes(b'clip'); j['scenes'][0]['clip'] = 'c.mp4'
        j['quality_report'] = {'fingerprint': quality.fingerprint(j, folder), 'hard_errors': [], 'warnings': [], 'clips': [{}]}
        s.schedule_quality(j)
        self.assertEqual(j['stage'], 'cover')
        self.assertTrue(j['quality_report']['visual']['skipped'])
        self.assertIn('Non regardé', j['quality_report']['visual']['scenes'][0]['detail'])
        self.assertFalse(any(t['slot'] == 'quality_review' for t in s.STATE['tasks']), 'no ChatGPT message')


class Settings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port; cls.base = f'http://127.0.0.1:{s.PORT}'
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def post(self, path, body):
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={'Origin': self.base, 'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(r).read())

    def test_settings_and_economy(self):
        s.STATE = s.fresh()
        self.post('/api/settings', {'board_controls': 'redo', 'clip_look': 'look'})
        self.post('/api/job', {'brief': BRIEF, 'mode': 'idea', 'config': {}})
        c = s.STATE['jobs'][0]['config']; self.assertEqual((c['board_controls'], c['clip_look']), ('redo', 'look'))
        self.post('/api/job', {'brief': BRIEF, 'mode': 'idea', 'config': {'quality': 'economy'}})
        c = s.STATE['jobs'][0]['config']; self.assertEqual((c['board_controls'], c['clip_look'], c['controls']), ('report', 'ear', 'report'))
        for bad in ({'board_controls': 'max'}, {'clip_look': 'eyes'}):
            with self.assertRaises(urllib.error.HTTPError):
                self.post('/api/settings', bad)


if __name__ == '__main__':
    unittest.main()
