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

    def test_account_gone_gives_up_its_number(self):
        # Real case 04/11/2026: fruit123abc left Chrome, arnaudchewa65 became /u/0; fruit123abc kept slot 0.
        s.STATE = s.fresh(); c = {'id': 'win', 'role': 'all'}; s.STATE['clients']['win'] = c
        s.STATE['profiles'] = [{'id': 'gone', 'label': 'fruit@x.com', 'flow_email': 'fruit@x.com', 'flow_client': 'win', 'slot': 0, 'auto_enabled': True, 'balance': 5,
                                'credit_probe': {'status': 'failed'}, 'refill_at': 1},
                               {'id': 'other', 'label': 'z@x.com', 'flow_email': 'z@x.com', 'flow_client': 'elsewhere', 'slot': 0, 'auto_enabled': True, 'balance': 9}]
        s.flow_scan(s.STATE, c, [{'slot': 0, 'email': 'new@x.com', 'balance': 50, 'project': None}])
        gone = next(p for p in s.STATE['profiles'] if p['id'] == 'gone')
        self.assertIsNone(gone['slot']); self.assertFalse(gone['auto_enabled'])
        self.assertNotIn('credit_probe', gone); self.assertNotIn('refill_at', gone)
        self.assertEqual(gone['balance'], 5, 'kept, nothing deleted')
        self.assertEqual(next(p for p in s.STATE['profiles'] if p['id'] == 'other')['slot'], 0, 'another browser’s accounts untouched')
        self.assertEqual(flow_accounts.choose(s.STATE, None, 12)['label'], 'new@x.com')
        s.flow_scan(s.STATE, c, [])
        self.assertEqual(next(p for p in s.STATE['profiles'] if p['label'] == 'new@x.com')['slot'], 0, 'an empty scan (window closed) changes nothing')

    def test_nothing_found(self):
        s.STATE = s.fresh(); c = {'id': 'win', 'role': 'all'}
        self.assertIn('Ajouter un compte', s.flow_scan(s.STATE, c, []))

    def test_detected_account_uses_its_slot_and_clears_obsolete_mismatch(self):
        s.STATE=s.fresh();c={'id':'online','role':'all'}
        s.STATE['profiles']=[{'id':'p','label':'owner@x.com','balance':50,'flow_url':'https://flow.google.com/project/old',
            'readiness':{'state':'fix','reason':'Autre compte Google ouvert à cette place : clique « Détecter mes comptes »'}}]
        s.flow_scan(s.STATE,c,[{'slot':1,'email':'owner@x.com','balance':50}])
        p=s.STATE['profiles'][0]
        self.assertEqual(p['flow_url'],'https://flow.google.com/u/1/project/old')
        self.assertNotIn('readiness',p)
        self.assertEqual(flow_accounts.at_slot('https://flow.google.com/u/3/project/old',1),p['flow_url'])


if __name__ == '__main__':
    unittest.main()
