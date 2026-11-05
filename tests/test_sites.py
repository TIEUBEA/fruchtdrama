"""Atelier-like accounts: owner requests (open / re-check), detected site status, default language."""
import importlib.util, json, os, pathlib, tempfile, threading, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_sites', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


class SitesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh()
        pair = self.req('/api/bridge/pair', {'code': s.STATE['pair_code'], 'label': 'QA', 'role': 'all', 'ai_provider': 'chatgpt'})
        self.client = pair['client']; self.auth = {'Authorization': 'Bearer ' + pair['token']}

    def req(self, path, body=None, headers=None, origin=None):
        h = {'Origin': origin or self.base, 'Content-Type': 'application/json', **(headers or {})}
        with urllib.request.urlopen(urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=h)) as r:
            return json.load(r)

    def test_requests_are_queued_once_and_delivered_once(self):
        self.req('/api/sites', {'action': 'check'}); self.req('/api/sites', {'action': 'check'})
        self.req('/api/sites', {'action': 'open', 'site': 'flow'})
        got = self.req('/api/bridge/requests?client=' + self.client, headers=self.auth)
        self.assertEqual(got, [{'type': 'check'}, {'type': 'open', 'site': 'flow'}])
        self.assertEqual(self.req('/api/bridge/requests?client=' + self.client, headers=self.auth), [])

    def test_refusals(self):
        for body in ({'action': 'open', 'site': 'evil'}, {'action': 'dance'}):
            with self.assertRaises(urllib.error.HTTPError) as e:
                self.req('/api/sites', body)
            self.assertEqual(e.exception.code, 400)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/sites', {'action': 'check'}, origin='https://evil.example')
        self.assertEqual(e.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/bridge/requests?client=' + self.client)
        self.assertEqual(e.exception.code, 401)
        s.STATE['clients'][self.client]['disabled'] = True; self.req('/api/sites', {'action': 'check'})
        self.assertEqual(self.req('/api/bridge/requests?client=' + self.client, headers=self.auth), [], 'switched-off gateway gets nothing')
        self.assertEqual(s.STATE['bridge_requests'], [{'type': 'check'}], 'kept for an active gateway')

    def test_status_is_stored_and_filtered(self):
        self.req('/api/bridge/sites', {'client': self.client, 'sites': {'chatgpt': {'connected': True}, 'flow': {'connected': True, 'email': 'A@b.com'}, 'evil': {'connected': True}}}, self.auth)
        sites = self.req('/api/state')['sites']
        self.assertTrue(sites['chatgpt']['connected']); self.assertEqual(sites['flow']['email'], 'A@b.com'); self.assertNotIn('evil', sites)

    def test_default_language(self):
        self.req('/api/settings', {'language': 'Français (fr-FR)'}); self.assertEqual(s.STATE['settings']['language'], 'Français (fr-FR)')
        with self.assertRaises(urllib.error.HTTPError):
            self.req('/api/settings', {'language': 'Klingon'})


if __name__ == '__main__':
    unittest.main()
