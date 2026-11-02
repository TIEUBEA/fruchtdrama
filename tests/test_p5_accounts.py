"""P5-07/P5-08: Grok / Arena accounts, limit per account, guided account change, automatic wake."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, time, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p5_accounts', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import engine_accounts as ea


def clip_job(engine='grok'):
    from PIL import Image
    j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'brief': 'b', 'characters': [], 'scenes': [], 'candidates': [], 'flow_profile': None,
         'config': {'scene_count': 4, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)', 'video_engine': engine}}
    sc = {'title': 'T', 'cover_title': 'C', 'description': 'd', 'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p'}],
          'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}]} for _ in range(4)]}
    s.STATE['jobs'].append(j); s.store_script(j, sc); j['stage'] = 'clips'
    for i, scene in enumerate(j['scenes']):
        Image.new('RGB', (32, 64), (i * 50, 9, 9)).save(s.job_dir(j) / f'scene{i}.png'); scene['image'] = f'scene{i}.png'
    return j


def active():
    return [t for t in s.STATE['tasks'] if t['status'] in ('queued', 'claimed')]


class UnitTests(unittest.TestCase):
    def test_choose_rotates_and_waits(self):
        st = {}
        a = ea.add(st, 'grok', 'A', 'A@x.com'); b = ea.add(st, 'grok', 'B', 'b@x.com'); ea.add(st, 'arena', 'C', 'c@x.com')
        self.assertEqual(a['email'], 'a@x.com')
        self.assertEqual(ea.choose(st, 'grok', None, 100)['id'], a['id'])
        ea.wall(a, 100, 60); self.assertEqual(ea.choose(st, 'grok', a['id'], 120)['id'], b['id'])
        ea.wall(b, 100); self.assertIsNone(ea.choose(st, 'grok', b['id'], 120))
        self.assertEqual(ea.next_free(st, 'grok', 120), 160)
        self.assertEqual(ea.choose(st, 'grok', b['id'], 161)['id'], a['id'], 'first renewed account comes back')
        ea.forget(b); self.assertFalse(ea.walled(b, 120))
        with self.assertRaises(ValueError):
            ea.add(st, 'grok', 'dup', 'b@x.com')
        with self.assertRaises(ValueError):
            ea.add(st, 'grok', 'pw', 'not-an-email')
        self.assertNotIn('password', json.dumps(st))


class FlowTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def claim(self, j):
        s.schedule(j); t = active()[-1]; t['status'] = 'claimed'; return t

    def test_account_attached_then_guided_switch_then_resume(self):
        a = ea.add(s.STATE, 'grok', 'Main', 'main@x.com'); b = ea.add(s.STATE, 'grok', 'Second', 'second@x.com')
        j = clip_job(); t = self.claim(j)
        self.assertEqual(t['payload']['account']['email'], 'main@x.com'); self.assertEqual(j['engine_account'], a['id'])
        s.accept_task_result(t, {'ok': False, 'error_kind': 'quota', 'error': 'Rate limit', 'retry_after': 7200, 'generation_submitted': True})
        self.assertTrue(ea.walled(a, time.time())); self.assertGreater(a['wall']['until'], time.time() + 7000)
        self.assertEqual(j['status'], 'waiting_account'); self.assertEqual(j['account_switch']['to'], 'second@x.com')
        self.assertEqual(active(), [], 'nothing sent before the owner changes account')
        self.assertIn('connectez-vous vous-même à second@x.com', j['events'][-1]['text'])
        j['status'] = 'running'; j.pop('account_switch'); s.schedule(j)
        self.assertEqual(active()[-1]['payload']['account']['email'], 'second@x.com')

    def test_all_accounts_walled_waits_then_wakes(self):
        a = ea.add(s.STATE, 'arena', 'Only', 'only@x.com')
        j = clip_job('arena'); t = self.claim(j)
        s.accept_task_result(t, {'ok': False, 'error_kind': 'quota', 'error': 'limit', 'retry_after': 120})
        self.assertEqual(j['status'], 'waiting_quota'); self.assertEqual(active(), [])
        self.assertEqual(s.wake_waiting(time.time() + 10), [], 'not before the renewal')
        # Simulate the passage of time: the renewal moment is reached.
        a['wall']['until'] = time.time() - 1; j['wait_until'] = time.time() - 1
        self.assertEqual(s.wake_waiting(), [j['id']])
        self.assertEqual(j['status'], 'running'); self.assertEqual(active()[-1]['payload']['account']['email'], 'only@x.com')

    def test_without_registered_accounts_waits_on_the_announced_delay(self):
        j = clip_job(); t = self.claim(j); self.assertNotIn('account', t['payload'])
        s.accept_task_result(t, {'ok': False, 'error_kind': 'quota', 'error': 'limit', 'retry_after': 600})
        self.assertEqual(j['status'], 'waiting_quota'); self.assertAlmostEqual(j['wait_until'], time.time() + 600, delta=5)

    def test_paused_production_is_never_moved(self):
        ea.add(s.STATE, 'grok', 'Main', 'main@x.com'); j = clip_job(); t = self.claim(j); j['status'] = 'paused'
        s.accept_task_result(t, {'ok': False, 'error_kind': 'quota', 'error': 'limit'})
        self.assertEqual(j['status'], 'paused')

    def test_other_failures_stay_for_the_owner(self):
        ea.add(s.STATE, 'grok', 'Main', 'main@x.com'); j = clip_job(); t = self.claim(j)
        s.accept_task_result(t, {'ok': False, 'error_kind': 'login', 'error': 'Grok Imagine : le compte connecté (x@y.z) n’est pas le compte attendu'})
        self.assertEqual(j['status'], 'attention'); self.assertIn('Connexion requise', j['events'][-1]['text'])

    def test_dry_run_needs_no_account(self):
        ea.add(s.STATE, 'grok', 'Main', 'main@x.com'); a = s.STATE['engine_accounts'][0]; ea.wall(a, time.time())
        j = clip_job(); j['config']['dry_run'] = True; s.schedule(j)
        self.assertTrue(active()[-1]['payload']['dry_run'], 'a dry run is possible even when the account is at its limit')


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

    def req(self, path, body, origin=None):
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={'Origin': origin or self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def error(self, path, body, origin=None):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req(path, body, origin)
        return e.exception.code, json.load(e.exception).get('error')

    def test_accounts_api(self):
        state = self.req('/api/engine-account', {'engine': 'grok', 'email': 'Main@x.com', 'label': 'Main'})
        a = state['engine_accounts'][0]; self.assertEqual(a['email'], 'main@x.com'); self.assertNotIn('token', state)
        self.assertIn('Flow', self.error('/api/engine-account', {'engine': 'flow', 'email': 'f@x.com'})[1])
        self.assertIn('inconnu', self.error('/api/engine-account', {'engine': 'sora', 'email': 'f@x.com'})[1])
        self.assertEqual(self.error('/api/engine-account', {'engine': 'grok', 'email': 'z@x.com'}, 'https://evil.example')[0], 403)
        ea.wall(s.STATE['engine_accounts'][0], time.time())
        j = clip_job(); j.update(status='waiting_quota', wait_until=time.time() + 9999)
        self.req('/api/engine-account', {'id': a['id'], 'forget_wall': True})
        self.assertNotIn('wall', s.STATE['engine_accounts'][0]); self.assertEqual(j['wait_until'], 0)
        self.assertEqual(s.wake_waiting(), [j['id']])
        self.req('/api/engine-account', {'id': a['id'], 'delete': True}); self.assertEqual(s.STATE['engine_accounts'], [])

    def test_account_switched_action(self):
        j = clip_job(); j.update(status='waiting_account', account_switch={'to': 'b@x.com'})
        self.req('/api/job/' + j['id'], {'action': 'account_switched'})
        self.assertEqual(j['status'], 'running'); self.assertNotIn('account_switch', j)
        self.assertIn('Aucun changement', self.error('/api/job/' + j['id'], {'action': 'account_switched'})[1])

    def test_new_grok_production(self):
        self.req('/api/job', {'brief': 'x', 'config': {'video_engine': 'grok'}})
        self.assertEqual(s.STATE['jobs'][0]['config']['video_engine'], 'grok')


if __name__ == '__main__':
    unittest.main()
