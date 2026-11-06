"""P2-06/P2-07/P2-08: learned quotas, waiting instead of failing, automatic wake, manual reset."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, time, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p2_quotas', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import quotas


class JournalTests(unittest.TestCase):
    def test_capacity_remaining_and_renewal(self):
        st = {}
        for t in (1000, 2000, 3000):
            quotas.note_pass(st, 'chatgpt_image', t)
        self.assertIsNone(quotas.status(st, 'chatgpt_image', 3100)['capacity'], 'not measured before a wall')
        quotas.note_wall(st, 'chatgpt_image', 3500)
        q = quotas.status(st, 'chatgpt_image', 3600)
        self.assertEqual((q['capacity'], q['used'], q['remaining']), (3, 3, 0))
        self.assertTrue(q['blocked']); self.assertEqual(q['retry_at'], 3500 + quotas.PROBE, 'unannounced: tried again after 30 min, not oldest pass + 6 h')
        self.assertFalse(q['announced'])
        self.assertFalse(quotas.status(st, 'chatgpt_image', 3500 + quotas.PROBE)['blocked'])
        st['quotas']['walls'][-1][0] = 1000 + quotas.WINDOW - 60
        self.assertEqual(quotas.status(st, 'chatgpt_image', 1000 + quotas.WINDOW - 30)['retry_at'], 1000 + quotas.WINDOW, 'oldest pass + 6 h when it comes sooner')
        self.assertFalse(quotas.status(st, 'chatgpt_text', 3600)['blocked'], 'services are independent')

    def test_announced_delay_wins_default_and_dedup(self):
        st = {}
        quotas.note_wall(st, 'chatgpt_image', 100, retry_after=7200); quotas.note_wall(st, 'chatgpt_image', 130, retry_after=5)
        self.assertEqual(len(st['quotas']['walls']), 1, 'same wall within a minute')
        self.assertEqual(quotas.status(st, 'chatgpt_image', 200)['retry_at'], 7300)
        self.assertTrue(quotas.status(st, 'chatgpt_image', 200)['announced'], 'announced delay kept, never shortened')
        st2 = {}; quotas.note_wall(st2, 'claude_text', 100)
        self.assertEqual(quotas.status(st2, 'claude_text', 200)['retry_at'], 100 + quotas.DEFAULT_WAIT)

    def test_a_pass_after_the_wall_unblocks(self):
        st = {}; quotas.note_wall(st, 'chatgpt_image', 100); quotas.note_pass(st, 'chatgpt_image', 400)
        self.assertFalse(quotas.status(st, 'chatgpt_image', 500)['blocked'])

    def test_bounded_and_forget(self):
        st = {}
        for t in range(3100):
            quotas.note_pass(st, 'chatgpt_text', t)
        self.assertEqual(len(st['quotas']['passes']), 3000)
        quotas.note_wall(st, 'chatgpt_text', 5000); quotas.forget(st, 'chatgpt_text')
        self.assertFalse(quotas.status(st, 'chatgpt_text', 5001)['blocked'])

    def test_service_mapping(self):
        self.assertEqual(quotas.service({'kind': 'chat_image', 'payload': {}}), 'chatgpt_image')
        self.assertEqual(quotas.service({'kind': 'chat_text', 'payload': {'provider': 'claude'}}), 'claude_text')
        self.assertIsNone(quotas.service({'kind': 'chat_collect', 'payload': {}}), 'collecting is not a generation')


def job():
    j = {'id': s.uid(), 'stage': 'images', 'status': 'running', 'events': [], 'brief': 'b', 'candidates': [], 'flow_profile': None,
         'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p', 'file': 'ref.png'}],
         'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'scene', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}]}],
         'config': {'scene_count': 1, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)'}}
    s.STATE['jobs'].append(j); return j


def queued():
    return [t for t in s.STATE['tasks'] if t['status'] == 'queued']


class ServerTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_quota_waits_then_wakes_without_owner(self):
        j = job(); s.schedule(j); t = queued()[-1]; t['status'] = 'claimed'
        s.accept_task_result(t, {'ok': False, 'error_kind': 'quota', 'error': 'limit', 'retry_after': 3600})
        self.assertEqual(j['status'], 'waiting_quota'); self.assertEqual(queued(), [], 'nothing sent while at the limit')
        self.assertAlmostEqual(j['wait_until'], time.time() + 3600, delta=5)
        other = job(); s.schedule(other)
        self.assertEqual(other['status'], 'waiting_quota', 'another production also waits instead of hitting the wall')
        s.STATE['quotas']['walls'][-1][3] = time.time() - 1; j['wait_until'] = other['wait_until'] = time.time() - 1
        self.assertEqual(sorted(s.wake_waiting()), sorted([j['id'], other['id']]))
        self.assertEqual(len(queued()), 2)

    def test_passes_are_counted_on_success(self):
        from PIL import Image
        j = job(); s.schedule(j); t = queued()[-1]; t['status'] = 'claimed'
        Image.new('RGB', (32, 64), 'blue').save(s.job_dir(j) / 'a.png'); Image.new('RGB', (32, 64), 'orange').save(s.job_dir(j) / 'ref.png')
        s.accept_task_result(t, {'ok': True, 'file': 'a.png'})
        self.assertEqual(quotas.status(s.STATE, 'chatgpt_image', time.time())['used'], 1)


class HttpTests(unittest.TestCase):
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
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers={'Origin': origin or self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def test_status_and_forget(self):
        quotas.note_wall(s.STATE, 'chatgpt_image', time.time(), 3600)
        j = job(); j.update(status='waiting_quota', wait_until=time.time() + 3600)
        state = self.req('/api/state')
        self.assertTrue(next(q for q in state['quota_status'] if q['service'] == 'chatgpt_image')['blocked'])
        self.req('/api/quota/forget', {'service': 'chatgpt_image'})
        self.assertEqual(j['wait_until'], 0); self.assertEqual(s.wake_waiting(), [j['id']]); self.assertEqual(len(queued()), 1)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/quota/forget', {'service': 'x'})
        self.assertEqual(e.exception.code, 400)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/quota/forget', {'service': 'chatgpt_image'}, 'https://evil.example')
        self.assertEqual(e.exception.code, 403)


if __name__ == '__main__':
    unittest.main()
