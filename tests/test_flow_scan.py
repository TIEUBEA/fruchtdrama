"""Détecter mes comptes: every Google account of the window becomes a Flow profile with real credits."""
import importlib.util, json, os, pathlib, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_scan', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import flow_accounts


class ScanTests(unittest.TestCase):
    def test_scan_creates_updates_and_routes(self):
        s.STATE = s.fresh(); c = {'id': 'win', 'role': 'all'}; s.STATE['clients']['win'] = c
        s.STATE['profiles'].append({'id': 'old', 'label': 'b@x.com', 'balance': 50})
        msg = s.flow_scan(s.STATE, c, [{'slot': 0, 'email': 'A@x.com', 'balance': 120, 'project': 'https://flow.google.com/u/0/project/abc'},
                                       {'slot': 1, 'email': 'b@x.com', 'balance': 5, 'project': None},
                                       {'slot': 2, 'email': 'c@x.com', 'balance': 0, 'project': None}, {'slot': 3, 'email': 'pas un email'}])
        self.assertIn('3 compte(s)', msg); self.assertIn('125 crédits', msg)
        a = next(p for p in s.STATE['profiles'] if p['label'] == 'a@x.com'); b = next(p for p in s.STATE['profiles'] if p['id'] == 'old')
        self.assertEqual(b['balance'], 5, 'declared 50 replaced by the real 5'); self.assertEqual(b['credit_source'], 'read')
        self.assertEqual(flow_accounts.route(a)['url'], 'https://flow.google.com/u/0/project/abc')
        self.assertEqual(flow_accounts.account_home(b['flow_url']), 'https://flow.google.com/u/1/', 'no project yet: home of the account')
        self.assertTrue(s.STATE['settings']['flow_auto'])
        self.assertEqual(flow_accounts.choose(s.STATE, None, 12)['label'], 'a@x.com', 'rotation picks an account that can pay')
        self.assertEqual(next(p for p in s.STATE['profiles'] if p['label'] == 'c@x.com')['blocked'], 'credits')

    def test_nothing_found(self):
        s.STATE = s.fresh(); c = {'id': 'win', 'role': 'all'}
        self.assertIn('Ajouter un compte', s.flow_scan(s.STATE, c, []))


if __name__ == '__main__':
    unittest.main()
