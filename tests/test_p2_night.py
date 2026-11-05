"""P2-10..P2-12: night queue and Windows keep-awake. Unit and HTTP tests."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, time, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p2_night', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import power


class FakeKernel:
    def __init__(self): self.calls = []
    def SetThreadExecutionState(self, flags): self.calls.append(flags)


class PowerTests(unittest.TestCase):
    def setUp(self):
        power._applied = None

    def test_keep_awake_then_release_once(self):
        k = FakeKernel()
        self.assertTrue(power.sync(True, k)); self.assertFalse(power.sync(True, k), 'applied once, not every 3 s')
        self.assertTrue(power.sync(False, k))
        self.assertEqual(k.calls, [power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED, power.ES_CONTINUOUS])

    def test_no_effect_outside_windows(self):
        if sys.platform != 'win32':
            self.assertIsNone(power.kernel32()); self.assertTrue(power.sync(True))


def job(title, status='paused', stage='images'):
    j = {'id': s.uid(), 'title': title, 'stage': stage, 'status': status, 'events': [], 'brief': 'b', 'candidates': [], 'flow_profile': None,
         'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p', 'file': 'ref.png'}],
         'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'scene', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}]}],
         'config': {'scene_count': 1, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)'}}
    s.STATE['jobs'].append(j); return j


def queued(j):
    return [t for t in s.STATE['tasks'] if t['job'] == j['id'] and t['status'] == 'queued']


class NightTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_one_at_a_time_in_order(self):
        a, b = job('A'), job('B'); s.night_add(a); s.night_add(b)
        self.assertEqual((a['status'], b['status']), ('waiting_night', 'waiting_night'))
        s.night()['active'] = True; s.night_tick()
        self.assertEqual(a['status'], 'running'); self.assertEqual(len(queued(a)), 1); self.assertEqual(b['status'], 'waiting_night')
        s.night_tick(); self.assertEqual(b['status'], 'waiting_night', 'B waits while A works')
        a['status'] = 'done'; s.night_tick()
        self.assertEqual(s.night()['ids'], [b['id']]); self.assertEqual(b['status'], 'running')
        b['status'] = 'done'; s.night_tick(); s.night_tick()
        self.assertFalse(s.night()['active']); self.assertIn('terminée', s.night()['log'][-1]['text'])

    def test_retryable_failure_three_times_with_growing_delay(self):
        a = job('A'); s.night_add(a); s.night()['active'] = True
        moment = time.time()
        for attempt in (1, 2, 3):
            s.night_tick(moment); self.assertEqual(a['status'], 'running')
            a['status'] = 'attention'; a['last_error'] = {'kind': 'interface'}; s.night_tick(moment)
            self.assertEqual(a['status'], 'waiting_night'); self.assertEqual(s.night()['failures'][a['id']], attempt)
            s.night_tick(moment); self.assertEqual(a['status'], 'waiting_night', 'not before its delay')
            moment += 120 * attempt + 1
        s.night_tick(moment); a['status'] = 'attention'; a['last_error'] = {'kind': 'timeout'}; s.night_tick(moment)
        self.assertNotIn(a['id'], s.night()['ids']); self.assertEqual(a['status'], 'attention', 'left for the owner after 3 retries')

    def test_human_cases_are_removed_with_their_reason(self):
        cases = [('attention', {'kind': 'challenge'}, 'images'), ('attention', None, 'script'), ('attention', {'kind': 'interface'}, 'quality'),
                 ('waiting_account', None, 'clips'), ('paused', None, 'images')]
        for status, error, stage in cases:
            with self.subTest(status=status, error=error, stage=stage):
                s.STATE = s.fresh(); a = job('A'); s.night_add(a); s.night()['active'] = True; s.night_tick()
                a['status'] = status; a['stage'] = stage
                if error:
                    a['last_error'] = error
                s.night_tick(); self.assertEqual(s.night()['ids'], []); self.assertEqual(a['status'], status, 'owner state untouched')

    def test_uncertain_flow_clip_is_never_retried(self):
        a = job('A', stage='clips'); s.night_add(a); s.night()['active'] = True; s.night_tick()
        a.update(status='attention', last_error={'kind': 'timeout'})
        a['scenes'][0]['image'] = 'x.png'
        s.STATE['tasks'].append({'id': 't', 'job': a['id'], 'kind': 'flow_video', 'slot': 'clip:0', 'status': 'failed', 'reservation': {'refunded': False}})
        s.night_tick(); self.assertEqual(s.night()['ids'], [])

    def test_waiting_states_hold_the_queue(self):
        a, b = job('A'), job('B'); s.night_add(a); s.night_add(b); s.night()['active'] = True; s.night_tick()
        for status in ('waiting_quota', 'waiting_credit', 'rendering'):
            a['status'] = status; s.night_tick(); self.assertEqual(b['status'], 'waiting_night', status)

    def test_add_rules(self):
        a = job('A'); a['config']['dry_run'] = True
        with self.assertRaisesRegex(ValueError, 'essai à blanc'):
            s.night_add(a)
        b = job('B', status='waiting_review')
        with self.assertRaisesRegex(ValueError, 'histoire à relire'):
            s.night_add(b)
        c = job('C', status='running'); s.STATE['tasks'].append({'id': 'x', 'job': c['id'], 'kind': 'chat_image', 'slot': 'image:0', 'status': 'claimed'})
        with self.assertRaisesRegex(ValueError, 'tâche est en cours'):
            s.night_add(c)
        d = job('D', status='done')
        with self.assertRaises(ValueError):
            s.night_add(d)
        e = job('E'); s.night_add(e)
        with self.assertRaises(ValueError):
            s.night_add(e)
        s.night_remove(e); self.assertEqual(e['status'], 'paused')

    def test_owner_pause_is_respected(self):
        a = job('A'); s.night_add(a); s.night()['active'] = True; s.night_tick(); a['status'] = 'paused'
        s.night_tick(); self.assertEqual(a['status'], 'paused'); self.assertTrue(any('mise en pause par vous' in x['text'] for x in s.night()['log']))

    def test_survives_restart_and_power_follows(self):
        a = job('A'); s.night_add(a); s.night()['active'] = True; s.save()
        s.STATE = s.read_state(); self.assertTrue(s.night()['active']); self.assertEqual(s.night()['ids'], [a['id']])
        power._applied = None; k = FakeKernel(); original = power.kernel32; power.kernel32 = lambda: k
        try:
            s.night_once(); self.assertEqual(k.calls[-1], power.ES_CONTINUOUS | power.ES_SYSTEM_REQUIRED)
            s.night()['active'] = False; s.night_once(); self.assertEqual(k.calls[-1], power.ES_CONTINUOUS)
        finally:
            power.kernel32 = original; power._applied = None


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

    def req(self, body, origin=None):
        r = urllib.request.Request(self.base + '/api/night', data=json.dumps(body).encode(), headers={'Origin': origin or self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def error(self, body, origin=None):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req(body, origin)
        return e.exception.code, json.load(e.exception)['error']

    def test_api(self):
        self.assertIn('Ajoutez', self.error({'action': 'start'})[1])
        a = job('A'); state = self.req({'action': 'add', 'job': a['id']})
        self.assertEqual(state['night']['ids'], [a['id']])
        self.assertTrue(self.req({'action': 'start'})['night']['active'])
        self.assertFalse(self.req({'action': 'stop'})['night']['active'])
        self.req({'action': 'remove', 'job': a['id']}); self.assertEqual(s.night()['ids'], [])
        self.assertEqual(self.error({'action': 'start'}, 'https://evil.example')[0], 403)
        self.assertIn('inconnue', self.error({'action': 'dance'})[1])


if __name__ == '__main__':
    unittest.main()
