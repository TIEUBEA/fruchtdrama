"""Atelier-like accounts: one address opens several services; hidden studio key paired automatically."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, time, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_unified', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import identities, engine_accounts as ea

EXT = 'chrome-extension://abcdefghijklmnopabcdefghijklmnop'


class UnitTests(unittest.TestCase):
    def test_one_address_many_services(self):
        st = {'profiles': [], 'engine_accounts': []}
        identities.add(st, ' Moi@Gmail.com ', ['chatgpt', 'flow', 'grok', 'arena'], 'Principal', 50)
        self.assertEqual(len(st['profiles']), 1); self.assertEqual(st['profiles'][0]['balance'], 50)
        self.assertEqual({a['engine'] for a in st['engine_accounts']}, {'grok'}, 'Arena removed (0.1.97): ignored')
        identities.add(st, 'moi@gmail.com', ['flow', 'claude'])
        self.assertEqual(len(st['profiles']), 1, 'no duplicate Flow profile'); self.assertEqual(len(st['identities']), 1)
        rows = identities.view(st, time.time())
        self.assertEqual(len(rows), 1); self.assertEqual(rows[0]['order'], ['chatgpt', 'claude', 'flow', 'grok'])
        # Rows left by an older version (Arena, Vidogrid) are ignored without error.
        st['engine_accounts'].append({'id': 'old', 'engine': 'arena', 'label': 'x', 'email': 'moi@gmail.com'})
        self.assertNotIn('arena', identities.view(st, time.time())[0]['services'])
        self.assertEqual(rows[0]['label'], 'Principal'); self.assertNotIn('password', json.dumps(st))

    def test_old_records_grouped_by_address(self):
        st = {'profiles': [{'id': 'p1', 'label': 'a@x.com', 'balance': 2}, {'id': 'p2', 'label': 'a@x.com', 'balance': 38}, {'id': 'p3', 'label': 'Flow', 'balance': 9}], 'engine_accounts': []}
        ea.add(st, 'grok', 'a@x.com', 'a@x.com')
        rows = identities.view(st, time.time())
        self.assertEqual([r['email'] for r in rows], ['a@x.com'])
        self.assertEqual(rows[0]['services']['flow']['balance'], 40); self.assertIn('grok', rows[0]['services'])

    def test_truthful_statuses(self):
        st = {'profiles': [], 'engine_accounts': [], 'sites': {'chatgpt': {'connected': True, 'email': 'a@x.com'}, 'flow': {'connected': True, 'email': 'b@x.com'}}}
        identities.add(st, 'a@x.com', ['chatgpt', 'flow'], balance=2); identities.add(st, 'b@x.com', ['chatgpt', 'flow', 'claude'], balance=50)
        rows = {r['email']: r['services'] for r in identities.view(st, time.time())}
        self.assertEqual(rows['a@x.com']['chatgpt']['state'], 'live'); self.assertEqual(rows['b@x.com']['chatgpt']['text'], 'Enregistré · autre compte ouvert')
        self.assertEqual(rows['a@x.com']['flow']['state'], 'low', '2 credits cannot pay a 12-credit clip'); self.assertIn('solde bas', rows['a@x.com']['flow']['text'])
        self.assertEqual(rows['b@x.com']['flow']['state'], 'live'); self.assertEqual(rows['b@x.com']['claude']['state'], 'off')

    def test_walls_and_errors(self):
        st = {'profiles': [], 'engine_accounts': []}
        identities.add(st, 'b@x.com', ['grok'])
        ea.wall(st['engine_accounts'][0], time.time(), 600)
        self.assertEqual(identities.view(st, time.time())[0]['services']['grok']['state'], 'wall')
        for bad in (('nope', ['grok']), ('c@x.com', []), ('c@x.com', ['sora'])):
            with self.assertRaises(ValueError):
                identities.add(st, *bad)

    def test_delete_refuses_busy_then_removes_everything(self):
        st = {'profiles': [], 'engine_accounts': [], 'tasks': []}
        identities.add(st, 'd@x.com', ['flow', 'grok'])
        st['tasks'].append({'status': 'claimed', 'kind': 'engine_video', 'payload': {'engine': 'grok', 'account': {'email': 'd@x.com'}}})
        gone = []
        with self.assertRaises(ValueError):
            identities.delete(st, 'd@x.com', gone.append)
        self.assertEqual(gone, [], 'nothing removed when refused')
        st['tasks'].clear()
        identities.delete(st, 'd@x.com', lambda pid: (gone.append(pid), st['profiles'].clear()))
        self.assertEqual(len(gone), 1); self.assertEqual(st['engine_accounts'], []); self.assertEqual(identities.view(st, 0), [])


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

    def req(self, path, body, origin=None, headers=None):
        h = {'Origin': origin or self.base, 'Content-Type': 'application/json', **(headers or {})}
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers=h)
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def error(self, path, body, origin=None):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req(path, body, origin)
        return e.exception.code, json.load(e.exception).get('error')

    def test_account_api(self):
        st = self.req('/api/account', {'email': 'Moi@x.com', 'services': ['chatgpt', 'flow', 'grok', 'arena'], 'balance': 50})
        self.assertEqual(len(st['accounts']), 1); self.assertEqual(st['accounts'][0]['services']['flow']['balance'], 50)
        self.assertNotIn('arena', st['accounts'][0]['services'])
        self.assertEqual(self.error('/api/account', {'email': 'moi@x.com', 'remove_service': 'arena'})[0], 400)
        st = self.req('/api/account', {'email': 'moi@x.com', 'remove_service': 'grok'})
        self.assertNotIn('grok', st['accounts'][0]['services'])
        st = self.req('/api/account', {'email': 'moi@x.com', 'delete': True})
        self.assertEqual(st['accounts'], []); self.assertEqual(st['profiles'], [])
        self.assertEqual(self.error('/api/account', {'email': 'x', 'services': ['grok']})[0], 400)
        self.assertEqual(self.error('/api/account', {'email': 'e@x.com', 'services': ['grok']}, 'http://evil.test')[0], 403)

    def test_delete_all_backs_up_and_keeps_busy(self):
        for e in ('a@x.com', 'b@x.com', 'c@x.com'):
            self.req('/api/account', {'email': e, 'services': ['flow', 'grok']})
        s.STATE['profiles'].append({'id': 'nomail', 'label': 'Flow', 'balance': 0})
        s.STATE['tasks'].append({'id': 't', 'job': 'j', 'status': 'claimed', 'kind': 'engine_video', 'payload': {'engine': 'grok', 'account': {'email': 'b@x.com'}}})
        st = self.req('/api/account', {'delete_all': True})
        self.assertEqual(st['removed'], 3); self.assertEqual(st['kept'], ['b@x.com'])
        self.assertEqual([a['email'] for a in st['accounts']], ['b@x.com'])
        backup = s.DATA / 'sauvegardes' / st['backup']
        self.assertEqual(len(json.loads(backup.read_text('utf-8'))['identities']), 3, 'state saved before removal')
        self.assertEqual(self.error('/api/account', {'delete_all': True}, 'http://evil.test')[0], 403)

    def test_auto_pair_once_hidden_key(self):
        self.assertEqual(self.error('/api/bridge/auto-pair', {}, 'http://evil.test')[0], 403)
        b = self.req('/api/bridge/auto-pair', {'label': 'Fenêtre'}, EXT)
        self.assertEqual(b['token'], s.STATE['token']); self.assertTrue(b['enabled'])
        self.assertEqual(s.STATE['clients'][b['client']]['role'], 'all')
        st = self.req('/api/state', {}) if False else json.load(urllib.request.urlopen(self.base + '/api/state'))
        self.assertNotIn('token', st); self.assertNotIn('extension_origin', st); self.assertTrue(st['key_saved'])
        self.assertIn('Autorisez', self.error('/api/bridge/auto-pair', {}, 'chrome-extension://other')[1])
        self.req('/api/key/reset', {})
        self.assertTrue(self.req('/api/bridge/auto-pair', {}, 'chrome-extension://other')['token'])
        # 0.1.69: the official extension (fixed key) replaces an older unpacked copy without the owner's approval.
        s.STATE['clients'][next(iter(s.STATE['clients']))]['seen'] = s.now()  # the older copy was polling a moment ago
        b = self.req('/api/bridge/auto-pair', {}, s.OFFICIAL_ORIGIN); self.assertTrue(b['token'])
        self.assertTrue(b['enabled'], 'the official extension is put in charge, not left waiting behind the older copy')
        self.assertEqual([c['id'] for c in s.STATE['clients'].values() if not c.get('disabled')], [b['client']])
        self.assertEqual(s.STATE['extension_origin'], s.OFFICIAL_ORIGIN)
        self.assertIn('Autorisez', self.error('/api/bridge/auto-pair', {}, 'chrome-extension://other')[1])

    def test_gateway_actions_from_studio_page(self):
        b = self.req('/api/bridge/auto-pair', {}, EXT); h = {'Authorization': 'Bearer ' + b['token']}
        self.req('/api/sites', {'action': 'register_flow'}); self.req('/api/sites', {'action': 'tidy'}); self.req('/api/sites', {'action': 'tidy'})
        self.assertEqual(self.error('/api/sites', {'action': 'recover', 'job': 'nope'})[0], 400)
        self.assertEqual(self.error('/api/sites', {'action': 'rm -rf'})[0], 400)
        st = json.load(urllib.request.urlopen(self.base + '/api/state')); self.assertTrue(st['bridge_notice']['pending'])
        r = urllib.request.Request(self.base + '/api/bridge/requests?client=' + b['client'], headers=h)
        self.assertEqual(json.load(urllib.request.urlopen(r)), [{'type': 'register_flow'}, {'type': 'tidy'}], 'queued once each')
        self.req('/api/bridge/notice', {'client': b['client'], 'action': 'tidy', 'ok': True, 'text': '2 onglets rangés'}, headers=h)
        st = json.load(urllib.request.urlopen(self.base + '/api/state'))
        self.assertEqual(st['bridge_notice']['text'], '2 onglets rangés'); self.assertNotIn('pending', st['bridge_notice'])

    def test_forget_offline_browser_only(self):
        b = self.req('/api/bridge/auto-pair', {}, EXT)
        s.STATE['clients'][b['client']]['seen'] = s.now()
        self.assertIn('en ligne', self.error('/api/client', {'id': b['client'], 'forget': True})[1])
        s.STATE['clients'][b['client']]['seen'] = '2026-01-01T00:00:00+00:00'
        self.assertNotIn(b['client'], self.req('/api/client', {'id': b['client'], 'forget': True})['clients'])

    def test_auto_pair_latest_browser_takes_over(self):
        """Real case 03/11: the extension reloaded lost its key, paired again and stayed disabled behind itself."""
        first = self.req('/api/bridge/auto-pair', {}, EXT)
        s.STATE['clients'][first['client']]['seen'] = s.now()
        second = self.req('/api/bridge/auto-pair', {}, EXT)
        self.assertTrue(second['enabled']); self.assertTrue(s.STATE['clients'][first['client']]['disabled'], 'still one working browser')

    def test_auto_pair_waits_while_other_browser_runs_a_task(self):
        first = self.req('/api/bridge/auto-pair', {}, EXT)
        s.STATE['clients'][first['client']]['seen'] = s.now()
        s.STATE['tasks'].append({'id': 'busy', 'job': 'j', 'slot': 'clip:0', 'kind': 'flow_video', 'status': 'claimed', 'client': first['client']})
        try:
            second = self.req('/api/bridge/auto-pair', {}, EXT)
            self.assertFalse(second['enabled']); self.assertFalse(s.STATE['clients'][first['client']].get('disabled'))
        finally:
            s.STATE['tasks'] = [t for t in s.STATE['tasks'] if t['id'] != 'busy']


if __name__ == '__main__':
    unittest.main()
