"""Several Chrome profiles at once: Google allows about 10 accounts per profile, the others add theirs."""
import datetime as dt, importlib.util, os, pathlib, sys, tempfile, time, unittest, unittest.mock
ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_sessions', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import flow_accounts


def iso(ago):
    return dt.datetime.fromtimestamp(time.time() - ago, dt.timezone.utc).isoformat()


def window(key, ago=0, **extra):
    return {'id': key, 'role': 'all', 'auto': True, 'ai_provider': 'both', 'flow_profile': None, 'seen': iso(ago), **extra}


def scan(n, first=0, domain='x.com'):
    return [{'slot': i, 'email': f'u{first + i}@{domain}', 'balance': 50, 'project': None} for i in range(n)]


class SessionTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def light(self, client):
        import json, threading, urllib.request
        http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = http.server_port
        threading.Thread(target=http.serve_forever, daemon=True).start()
        try:
            with unittest.mock.patch.object(s.Handler, 'auth_bridge', lambda self: True):
                url = f'http://127.0.0.1:{s.PORT}/api/bridge/requests?client={client}&light=1'
                return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'Origin': url[:22 + len(str(s.PORT))]})))
        finally:
            http.shutdown(); http.server_close()

    def test_busy_window_still_reads_balances(self):
        self.add(window('w1'))
        s.STATE['bridge_requests'] = [{'type': 'scan_flow', 'background': True}, {'type': 'check'}]
        self.assertEqual([r['type'] for r in self.light('w1')], ['scan_flow'], 'scan given to the busy main window')
        self.assertEqual([r['type'] for r in s.STATE['bridge_requests']], ['check'], 'other checks wait for idle')
        s.STATE['bridge_requests'] = [{'type': 'scan_flow', 'background': True}]
        s.STATE['tasks'].append({'id': 't', 'job': 'j', 'kind': 'flow_video', 'status': 'claimed', 'client': 'w1', 'slot': 'clip:0'})
        self.assertEqual(self.light('w1'), [], 'never while this window has a Flow clip in hand')

    def test_no_access_follows_the_flow_page(self):
        c = window('w1'); self.add(c)
        s.flow_scan(s.STATE, c, [{'slot': 0, 'email': 'u0@x.com', 'balance': None, 'project': None, 'unavailable': True, 'why': 'Flow ist in Ihrem Land nicht verfügbar'}])
        p = s.STATE['profiles'][0]
        self.assertIn('Flow ist in Ihrem Land', p['readiness']['reason'])
        self.assertFalse(flow_accounts.usable(p), 'Google page « /unavailable »: no access')
        s.flow_scan(s.STATE, c, scan(1))
        self.assertFalse(flow_accounts.usable(p), 'an older extension cannot tell: the verdict stays')
        s.flow_scan(s.STATE, c, [{**scan(1)[0], 'unavailable': False}])
        self.assertTrue(flow_accounts.usable(p), 'the real Flow page was seen: access back')

    def add(self, *clients):
        for c in clients:
            s.STATE['clients'][c['id']] = c
        return clients

    def test_other_profile_open_at_the_same_time_adds_its_accounts(self):
        main, other = self.add(window('main', 5), window('other', 60, disabled=True))
        self.assertEqual(s.session_rejoined(other, time.time() - 60), 'session')
        self.assertFalse(other['disabled']); self.assertEqual(other['role'], 'flow'); self.assertTrue(other['pool'])
        self.assertFalse(main.get('disabled'), 'the main window keeps working'); self.assertEqual(main['role'], 'all')
        self.assertIn({'type': 'scan_flow', 'client': 'other'}, s.STATE['bridge_requests'])
        s.flow_scan(s.STATE, main, scan(10))
        s.flow_scan(s.STATE, other, scan(10, first=10))
        self.assertEqual(len(s.STATE['profiles']), 20, 'beyond the 10 of one Chrome profile')
        self.assertEqual(sum(p['flow_client'] == 'other' for p in s.STATE['profiles']), 10)
        first_other = next(p for p in s.STATE['profiles'] if p['label'] == 'u10@x.com')
        self.assertEqual(first_other['slot'], 0, 'its number in its own Chrome profile')
        self.assertTrue(flow_accounts.eligible(s.STATE, first_other))

    def test_chat_stays_in_the_main_window(self):
        main, other = self.add(window('main', 5), window('other', 5, pool=True, role='flow', ai_provider='none'))
        other['role'] = 'flow'
        chat = {'kind': 'chat_text', 'payload': {'provider': 'chatgpt'}}
        self.assertFalse(s.client_accepts(other, chat))
        video = {'kind': 'flow_video', 'profile': 'p', 'payload': {'flow_route': {'client': 'other'}}}
        s.STATE['profiles'] = [{'id': 'p', 'label': 'a@x.com'}]
        self.assertTrue(s.client_accepts(other, video))
        self.assertFalse(s.client_accepts(main, video))

    def test_reinstalled_extension_still_takes_over(self):
        # The old pairing is silent since before the new one was first heard: not a second profile.
        old, new = self.add(window('old', 500), window('new', 400, disabled=True))
        self.assertEqual(s.session_rejoined(new, time.time() - 400), 'takeover')
        self.assertEqual(new['role'], 'all'); self.assertFalse(new.get('pool')); self.assertTrue(old['disabled'])

    def test_reinstall_while_old_pairing_still_counts_as_online(self):
        # Old pairing heard 100 s ago (under the 180 s limit), before the new one's last contact: wait, do not demote.
        self.add(window('old', 100), window('new', 50, disabled=True))
        self.assertIsNone(s.session_rejoined(s.STATE['clients']['new'], time.time() - 50))
        self.assertFalse(s.STATE['clients']['new'].get('pool'))

    def test_new_profile_pairing_gives_the_main_place_back(self):
        main, new = self.add(window('main', 5, disabled=True), window('new', 3, replaced=['main'], taken={'p': 'main'}))
        s.STATE['profiles'] = [{'id': 'p', 'label': 'a@x.com', 'flow_client': 'new'}]
        self.assertEqual(s.session_rejoined(main, time.time() - 5), 'main')
        self.assertFalse(main['disabled']); self.assertEqual(main['role'], 'all')
        self.assertTrue(new['pool']); self.assertFalse(new['disabled'])
        self.assertEqual(s.STATE['profiles'][0]['flow_client'], 'main', 'its accounts come back')

    def test_owner_switched_off_stays_off(self):
        self.add(window('main', 5)); off = self.add(window('off', 60, disabled=True, owner_off=True))[0]
        self.assertIsNone(s.session_rejoined(off, time.time() - 60)); self.assertTrue(off['disabled'])

    def test_closed_session_keeps_its_accounts(self):
        main, other = self.add(window('main', 5), window('other', 900, pool=True, role='flow'))
        s.STATE['profiles'] = [{'id': 'p', 'label': 'a@x.com', 'flow_email': 'a@x.com', 'flow_client': 'other', 'auto_enabled': True, 'balance': 50, 'flow_url': 'https://flow.google.com/u/0/project/abc'}]
        self.assertEqual(flow_accounts.follow_active_browser(s.STATE), 0)
        self.assertEqual(s.STATE['profiles'][0]['flow_client'], 'other', 'never rewired to a browser that does not hold it')
        self.assertFalse(flow_accounts.eligible(s.STATE, s.STATE['profiles'][0]), 'skipped while its Chrome is closed')

    def test_same_account_in_two_profiles_stays_with_its_session(self):
        main, other = self.add(window('main', 5), window('other', 5, pool=True, role='flow'))
        s.flow_scan(s.STATE, main, [{'slot': 3, 'email': 'both@x.com', 'balance': 50, 'project': None}])
        message = s.flow_scan(s.STATE, other, [{'slot': 0, 'email': 'both@x.com', 'balance': 50, 'project': None}])
        p = s.STATE['profiles'][0]
        self.assertEqual((p['flow_client'], p['slot'], len(s.STATE['profiles'])), ('main', 3, 1))
        self.assertIn('déjà suivi', message); self.assertFalse(message.startswith('Aucun'))

    def test_account_lost_by_the_main_window_goes_to_the_profile_that_has_it(self):
        # borismoussa53, 10/11/2026: no longer in the main profile (slot None, out of rotation), signed in to Boris53.
        main, other = self.add(window('main', 5), window('other', 5, pool=True, role='flow'))
        s.STATE['profiles'] = [{'id': 'p', 'label': 'b53@x.com', 'flow_email': 'b53@x.com', 'flow_client': 'main', 'slot': None, 'auto_enabled': False, 'balance': 2}]
        s.flow_scan(s.STATE, other, [{'slot': 0, 'email': 'b53@x.com', 'balance': 2, 'project': None}])
        p = s.STATE['profiles'][0]
        self.assertEqual((p['flow_client'], p['slot'], p['auto_enabled']), ('other', 0, True))

    def test_session_does_not_take_over_main_pairing(self):
        main, other = self.add(window('main', 5), window('other', 5, pool=True, role='flow'))
        self.assertEqual(s.switch_off_main_windows(), ['main'])
        self.assertFalse(other.get('disabled'), 'a new pairing leaves the extra sessions on')


class ClosedProfileTests(unittest.TestCase):
    """A closed Chrome profile is opened again when only its accounts can pay (owner 10/11/2026)."""
    FOLDERS = {'main@x.com': 'Profile 1', 'other@x.com': 'Profile 5', 'third@x.com': 'Profile 7'}

    def setUp(self):
        s.STATE = s.fresh(); s.STATE['settings']['flow_auto'] = True
        self.main = window('main', 5); self.other = window('other', 5, pool=True, role='flow')
        s.STATE['clients'] = {'main': self.main, 'other': self.other}
        s.flow_scan(s.STATE, self.main, [{'slot': 0, 'email': 'main@x.com', 'balance': 2, 'project': None}])
        s.flow_scan(s.STATE, self.other, [{'slot': 0, 'email': 'main@x.com', 'balance': 2}, {'slot': 1, 'email': 'other@x.com', 'balance': 40, 'project': None}])
        self.assertEqual(s.remember_chrome_folder(self.main, [{'slot': 0, 'email': 'main@x.com'}], self.FOLDERS), 'Profile 1')
        self.assertEqual(s.remember_chrome_folder(self.other, [{'slot': 0, 'email': 'main@x.com'}, {'slot': 1, 'email': 'other@x.com'}], self.FOLDERS), 'Profile 5',
                         'a shared account never gives this window the main profile')
        s.STATE['jobs'] = [{'id': 'j', 'stage': 'clips', 'status': 'waiting_credit', 'config': {'flow_cost': 15}, 'events': []}]

    def test_profile_known_by_its_first_account(self):
        # Default: its own account at /u/0, plus an account that is Profile 3's own Chrome account.
        folders = {**self.FOLDERS, 'own@x.com': 'Default', 'p3@x.com': 'Profile 3'}
        default = window('default', 5, pool=True, role='flow'); s.STATE['clients']['default'] = default
        s.flow_scan(s.STATE, default, [{'slot': 0, 'email': 'main@x.com'}, {'slot': 1, 'email': 'p3@x.com', 'balance': 30}])
        self.assertEqual(s.remember_chrome_folder(default, [{'slot': 0, 'email': 'own@x.com'}, {'slot': 1, 'email': 'p3@x.com'}], folders), 'Default')

    def test_folder_reaches_the_accounts(self):
        other = next(p for p in s.STATE['profiles'] if p['flow_email'] == 'other@x.com')
        self.assertEqual(other['chrome_profile'], 'Profile 5')
        self.assertEqual(flow_accounts.folder_of([{'slot': 0, 'email': 'third@x.com'}], self.FOLDERS, {'Profile 7'}), None)

    def test_closed_profile_opened_once_when_it_can_pay(self):
        self.assertIsNone(s.closed_session_account(15), 'open profile: nothing to open')
        self.other['seen'] = iso(900)
        with unittest.mock.patch.object(flow_accounts, 'launch') as launch:
            self.assertTrue(s.wake_closed_session())
            self.assertFalse(s.wake_closed_session(), 'not twice in 15 min')
        self.assertEqual(launch.call_args[0][0]['chrome_profile'], 'Profile 5')
        self.assertIn('autre profil Chrome', s.STATE['jobs'][0]['events'][-1]['text'] if isinstance(s.STATE['jobs'][0]['events'][-1], dict) else str(s.STATE['jobs'][0]['events'][-1]))

    def test_nothing_opened_without_need(self):
        self.other['seen'] = iso(900)
        with unittest.mock.patch.object(flow_accounts, 'launch') as launch:
            s.STATE['jobs'][0]['status'] = 'running'
            self.assertFalse(s.wake_closed_session())
            s.STATE['jobs'][0]['status'] = 'waiting_credit'; s.STATE['jobs'][0]['config']['flow_cost'] = 60
            self.assertFalse(s.wake_closed_session(), 'its 40 credits cannot pay')
            self.other['owner_off'] = True; s.STATE['jobs'][0]['config']['flow_cost'] = 15
            self.assertFalse(s.wake_closed_session(), 'switched off by the owner')
        launch.assert_not_called()

    def test_reads_only_profile_names(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / 'Local State'
            path.write_text('{"os_crypt":{"encrypted_key":"secret"},"profile":{"info_cache":{"Default":{"user_name":"A@x.com"},"Profile 3":{"user_name":"b@x.com"},"../evil":{"user_name":"c@x.com"}}}}', 'utf-8')
            self.assertEqual(flow_accounts.chrome_folders(path), {'a@x.com': 'Default', 'b@x.com': 'Profile 3'})
            self.assertEqual(flow_accounts.chrome_folders(pathlib.Path(d) / 'missing'), {})


class SingleStudioTests(unittest.TestCase):
    def test_second_studio_cannot_take_the_same_port(self):
        first = s.StudioServer(('127.0.0.1', 0), s.Handler)
        try:
            with self.assertRaises(OSError):
                s.StudioServer(('127.0.0.1', first.server_address[1]), s.Handler).server_close()
        finally:
            first.server_close()


class WatchdogTests(unittest.TestCase):
    """10/11/2026: out of memory, the studio kept its port but answered nothing, and nobody could start it again."""
    def run_watch(self, answers):
        class Done(BaseException): pass  # ends the test run; never counted as a silent check
        stopped = []; it = iter(answers)
        def ping():
            answer = next(it, None)
            if answer is None: raise Done()
            if not answer: raise OSError('timed out')
        try:
            s.watchdog_loop(ping=ping, stop=lambda: stopped.append(True), interval=0, limit=3, sleep=lambda x: None)
        except Done:
            pass
        return stopped

    def test_frozen_studio_stops_itself_after_three_silent_checks(self):
        self.assertEqual(self.run_watch([True, False, False, False]), [True])

    def test_one_slow_answer_is_not_a_freeze(self):
        self.assertEqual(self.run_watch([False, False, True, False, False, True]), [], 'two misses then an answer: keeps running')

    def test_a_montage_in_progress_is_never_taken_for_a_freeze(self):
        class Done(BaseException): pass
        stopped = []; rounds = iter([True, True, True, True, False])
        def busy():
            value = next(rounds, None)
            if value is None: raise Done()
            return value
        def ping(): raise OSError('timed out')  # slow answers during the montage
        try:
            s.watchdog_loop(ping=ping, stop=lambda: stopped.append(True), interval=0, limit=3, sleep=lambda x: None, busy=busy)
        except Done:
            pass
        self.assertEqual(stopped, [], 'four silent checks during a montage, one after: not stopped')

    def test_one_montage_at_a_time(self):
        self.assertTrue(s.RENDER_SLOT.acquire(blocking=False))
        try:self.assertFalse(s.RENDER_SLOT.acquire(blocking=False), 'a second montage waits its turn')
        finally:s.RENDER_SLOT.release()

    def test_a_port_that_never_answers_is_seen_as_frozen(self):
        import socket
        frozen = socket.socket(); frozen.bind(('127.0.0.1', 0)); frozen.listen(1)  # listening, never answering
        port = s.PORT; s.PORT = frozen.getsockname()[1]
        try:
            with self.assertRaises(OSError): s.self_ping(timeout=1)
        finally:
            s.PORT = port; frozen.close()


if __name__ == '__main__':
    unittest.main()
