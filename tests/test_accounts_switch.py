"""0.1.90: accounts and automatic switching without waiting (owner 06/11/2026).

Real cases: an episode resumed while the FruchtDrama window was online went to « Action requise » after
« Ouverture Flow impossible (Chrome introuvable…) »; a ChatGPT image limit was announced in UTC."""
import datetime as dt, importlib.util, json, os, pathlib, sys, tempfile, threading, time, unittest, urllib.request
from unittest.mock import patch

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_accounts_switch', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import flow_accounts, quotas, identities, engine_accounts


def iso(ago):
    return dt.datetime.fromtimestamp(time.time() - ago, dt.timezone.utc).isoformat()


def profile(name, balance, client):
    return {'id': name, 'label': name + '@example.com', 'balance': balance, 'flow_email': name + '@example.com', 'flow_client': client,
            'flow_url': 'https://flow.google.com/u/' + ('0' if name == 'a' else '1') + '/project/' + name, 'auto_enabled': True, 'slot': 0 if name == 'a' else 1}


def clip_job(profile_id='a'):
    j = {'id': s.uid(), 'stage': 'clips', 'status': 'running', 'events': [], 'config': {'flow_cost': 12}, 'flow_profile': profile_id,
         'characters': [], 'scenes': [{'image': 'image.png', 'dialogue': [], 'video_prompt': 'a scene'}]}
    s.STATE['jobs'].append(j); return j


class ReinstalledExtension(unittest.TestCase):
    """Old pairing never switched off (it held a task when the new one paired), silent since; the new one online."""
    def setUp(self):
        s.STATE = s.fresh(); s.STATE['settings']['flow_auto'] = True
        s.STATE['clients'] = {'old': {'id': 'old', 'auto': True, 'role': 'all', 'seen': iso(3600)},
                              'new': {'id': 'new', 'auto': True, 'role': 'all', 'seen': iso(5)}}
        s.STATE['profiles'] = [profile('a', 50, 'old'), profile('b', 50, 'old')]
        self.job = clip_job()

    def queue_clip(self):
        # The clip was prepared while the old pairing still held the accounts.
        with patch.object(flow_accounts, 'follow_active_browser', return_value=0), patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.schedule(self.job)
        t = s.STATE['tasks'][-1]; self.assertEqual(t['payload']['flow_route']['client'], 'old'); return t

    def test_accounts_follow_the_window_heard_from(self):
        self.assertEqual(flow_accounts.follow_active_browser(s.STATE), 2)
        self.assertEqual({p['flow_client'] for p in s.STATE['profiles']}, {'new'})

    def test_online_window_takes_the_queued_clip_and_nothing_is_launched(self):
        t = self.queue_clip()
        self.assertFalse(s.client_accepts(s.STATE['clients']['new'], t), 'before: the new window never took it')
        with patch.object(flow_accounts, 'launch') as launch, patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.flow_dispatch_tick(); s.flow_dispatch_tick()
        launch.assert_not_called()
        self.assertEqual(t['payload']['flow_route']['client'], 'new')
        self.assertTrue(s.client_accepts(s.STATE['clients']['new'], t))
        self.assertEqual(self.job['status'], 'running', 'never « Action requise »')
        self.assertFalse(any('Ouverture' in e['text'] or 'Chrome' in e['text'] for e in self.job['events']))

    def test_a_claimed_clip_keeps_its_browser(self):
        t = self.queue_clip(); t.update(status='claimed', client='old')
        s.rebind_flow_routes()
        self.assertEqual(t['payload']['flow_route']['client'], 'old', 'may already be in Flow: never moved')

    def test_queued_balance_check_follows_too(self):
        p = s.STATE['profiles'][0]
        p['credit_probe'] = {'id': 'x', 'status': 'queued', 'client': 'old', 'target': {**flow_accounts.route(p)}, 'created': iso(0), 'expires': iso(-180)}
        s.rebind_flow_routes()
        self.assertEqual((p['credit_probe']['client'], p['credit_probe']['target']['client']), ('new', 'new'))
        self.assertEqual(p['credit_probe']['target'], flow_accounts.route(p), 'the report check still matches')

    def test_two_windows_online_are_never_rewired_by_guess(self):
        s.STATE['clients']['old']['seen'] = iso(5)
        self.assertEqual(flow_accounts.follow_active_browser(s.STATE), 0)


class NoWindow(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh(); s.STATE['settings']['flow_auto'] = True
        s.STATE['clients'] = {'w': {'id': 'w', 'auto': True, 'role': 'all', 'seen': iso(3600)}}
        s.STATE['profiles'] = [profile('a', 50, 'w')]
        self.job = clip_job()
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.schedule(self.job)

    def test_chrome_started_once_in_background_and_episode_keeps_waiting(self):
        with patch.object(flow_accounts, 'launch') as launch:
            s.flow_dispatch_tick(); s.flow_dispatch_tick()
        launch.assert_called_once()
        self.assertEqual(self.job['status'], 'running')

    def test_launch_failure_never_asks_for_action(self):
        with patch.object(flow_accounts, 'launch', side_effect=ValueError('Chrome introuvable sur cet ordinateur.')):
            s.flow_dispatch_tick()
        self.assertEqual(self.job['status'], 'running', 'the clip leaves as soon as the window opens')
        self.assertIn('dès que la fenêtre FruchtDrama est ouverte', self.job['events'][-1]['text'])

    def test_another_window_online_opens_nothing(self):
        s.STATE['clients']['other'] = {'id': 'other', 'role': 'flow', 'seen': iso(5)}  # manual pairing: not rewired
        with patch.object(flow_accounts, 'launch') as launch:
            s.flow_dispatch_tick(); s.flow_dispatch_tick()
        launch.assert_not_called()
        self.assertEqual(sum('mémorisé par une autre fenêtre' in e['text'] for e in self.job['events']), 1, 'said once')

    def test_background_balance_reading_never_starts_chrome(self):
        s.STATE['tasks'] = []; s.STATE['jobs'] = []; s.STATE['profiles'][0]['balance'] = 0
        with patch.object(flow_accounts, 'launch') as launch:
            s.flow_dispatch_tick()
        launch.assert_not_called()


class ChromeLocation(unittest.TestCase):
    def test_linux_macos_windows(self):
        with tempfile.TemporaryDirectory() as d:
            exe = pathlib.Path(d) / 'Google/Chrome/Application/chrome.exe'; exe.parent.mkdir(parents=True); exe.write_text('')
            self.assertEqual(flow_accounts.chrome_executable('win32', {'LOCALAPPDATA': d}, lambda n: None), exe)
        self.assertIsNone(flow_accounts.chrome_executable('win32', {}, lambda n: '/usr/bin/' + n))
        which = lambda n: '/usr/bin/chromium' if n == 'chromium' else None
        with patch.object(pathlib.Path, 'is_file', return_value=False):
            self.assertEqual(flow_accounts.chrome_executable('linux', {}, which), pathlib.Path('/usr/bin/chromium'))
            self.assertEqual(flow_accounts.chrome_executable('darwin', {}, which), pathlib.Path('/usr/bin/chromium'))
            self.assertIsNone(flow_accounts.chrome_executable('linux', {}, lambda n: None))

    def test_launch_opens_no_window_and_no_url(self):
        p = profile('a', 50, 'w'); p['chrome_profile'] = 'Profile 2'
        with patch.object(flow_accounts, 'chrome_executable', return_value=pathlib.Path('/opt/google/chrome/chrome')), patch.object(flow_accounts.subprocess, 'Popen') as popen:
            flow_accounts.launch(p)
        args = popen.call_args[0][0]
        self.assertEqual(args, ['/opt/google/chrome/chrome', '--no-startup-window', '--profile-directory=Profile 2'])
        with patch.object(flow_accounts, 'chrome_executable', return_value=None), self.assertRaisesRegex(ValueError, 'Chrome introuvable'):
            flow_accounts.launch(p)


class LocalTime(unittest.TestCase):
    def test_clock_is_local_with_remaining_wait(self):
        moment = time.time(); at = moment + 28 * 60
        self.assertEqual(s.clock(at, moment), dt.datetime.fromtimestamp(at).strftime('%H:%M') if dt.datetime.fromtimestamp(at).date() == dt.datetime.fromtimestamp(moment).date() else s.clock(at, moment))
        self.assertTrue(s.clock_in(at, moment).endswith('(dans 28 min)'))
        self.assertTrue(s.clock_in(moment + 90 * 60, moment).endswith('(dans 1 h 30)'))
        self.assertTrue(s.clock(moment + 86400, moment).startswith('demain '))

    def test_image_limit_said_in_local_time_and_clips_go_on(self):
        s.STATE = s.fresh(); j = clip_job(); j['stage'] = 'images'
        quotas.note_wall(s.STATE, 'chatgpt_image', time.time(), 25 * 60)
        s.add_task(j, 'chat_image', {'provider': 'chatgpt', 'prompt': 'p'}, 'image:0')
        text = j['events'][-1]['text']
        self.assertEqual(j['status'], 'waiting_quota'); self.assertNotIn('UTC', text)
        self.assertIn(dt.datetime.fromtimestamp(j['wait_until']).strftime('%H:%M'), text)
        self.assertIn('délai annoncé', text); self.assertIn('clips des planches déjà dessinées continuent', text)

    def test_grok_limit_in_accounts_page_is_local(self):
        st = {'engine_accounts': [], 'profiles': [], 'identities': []}
        a = engine_accounts.add(st, 'grok', '', 'g@example.com'); engine_accounts.wall(a, time.time(), 3600)
        text = identities.view(st, time.time())[0]['services']['grok']['text']
        self.assertNotIn('UTC', text); self.assertIn(dt.datetime.fromtimestamp(a['wall']['until']).strftime('%H:%M'), text)


class SwitchHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh()
        pair = self.req('/api/bridge/pair', {'code': s.STATE['pair_code'], 'label': 'QA', 'role': 'all'})
        self.client = pair['client']; self.auth = {'Authorization': 'Bearer ' + pair['token']}
        s.STATE['settings']['flow_auto'] = True

    def req(self, path, body=None):
        h = {'Origin': self.base, 'Content-Type': 'application/json', **getattr(self, 'auth', {})}
        request = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=h)
        with urllib.request.urlopen(request) as r:
            return json.load(r)

    def test_empty_account_switches_at_claim_without_waiting(self):
        s.STATE['profiles'] = [profile('a', 50, self.client), profile('b', 50, self.client)]
        j = clip_job()
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.schedule(j); s.STATE['profiles'][0]['balance'] = 0  # read again in Flow meanwhile: empty
            t = self.req('/api/bridge/task?client=' + self.client + '&lane=video')
        self.assertEqual(t['profile'], 'b', 'same request, next account, no waiting_credit')
        self.assertEqual(j['flow_profile'], 'b'); self.assertEqual(s.STATE['profiles'][0]['balance'], 0, 'nothing reserved on the empty one')
        self.assertIn('Passage automatique au compte Flow b@example.com (50 crédits)', ' '.join(e['text'] for e in j['events']))

    def test_board_held_by_a_gone_window_is_asked_again(self):
        s.STATE['clients'][self.client]['auto'] = True
        s.STATE['clients']['gone'] = {'id': 'gone', 'auto': True, 'role': 'all', 'seen': iso(3600), 'disabled': True}
        j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'config': {}}
        s.STATE['jobs'].append(j)
        old = {'id': 'old', 'job': j['id'], 'kind': 'chat_text', 'slot': 'script', 'status': 'claimed', 'client': 'gone', 'payload': {'provider': 'chatgpt'}, 'created': iso(600)}
        clip = {'id': 'clip', 'job': j['id'], 'kind': 'flow_video', 'slot': 'clip:0', 'status': 'claimed', 'client': 'gone', 'payload': {}, 'created': iso(600)}
        s.STATE['tasks'] = [old, clip]
        with patch.object(s, 'schedule'):
            self.req('/api/bridge/task?client=' + self.client + '&lane=chat')
        self.assertEqual(old['status'], 'failed'); self.assertEqual(clip['status'], 'claimed', 'a clip is never sent again without the owner')
        self.assertIn('la reprend', j['events'][-1]['text'])

    def test_live_window_task_is_kept(self):
        s.STATE['clients'][self.client]['auto'] = True
        s.STATE['clients']['other'] = {'id': 'other', 'auto': True, 'role': 'all', 'seen': iso(5)}
        j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'config': {}}
        s.STATE['jobs'].append(j)
        t = {'id': 't', 'job': j['id'], 'kind': 'chat_text', 'slot': 'script', 'status': 'claimed', 'client': 'other', 'payload': {}, 'created': iso(10)}
        s.STATE['tasks'] = [t]
        with patch.object(s, 'schedule'):
            self.req('/api/bridge/task?client=' + self.client + '&lane=chat')
        self.assertEqual(t['status'], 'claimed')


if __name__ == '__main__':
    unittest.main()
