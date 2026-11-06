"""Daily Flow credit refill: clock starts at first spend, rescan when due, soonest-refill accounts used first."""
import importlib.util, os, pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_refill', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import flow_refill as r


class Refill(unittest.TestCase):
    def test_clock(self):
        p = {}
        r.spent(p, 1000); r.spent(p, 5000)
        self.assertEqual(p['refill_at'], 1000 + r.PERIOD, 'later spends keep the first clock')
        r.read(p, 20, 2000); self.assertEqual(p['refill_at'], 1000 + r.PERIOD)
        r.read(p, 20, 1000 + r.PERIOD + 1); self.assertEqual(p['refill_at'], 1000 + r.PERIOD + 1 + r.RETRY, 'not back yet: retry in 1 h')
        r.read(p, 50, 99999); self.assertNotIn('refill_at', p)
        q = {}; r.read(q, 5, 100); self.assertEqual(q['refill_at'], 100 + r.PERIOD, 'spent outside: worst case')

    def test_order_and_due(self):
        a, b, c = {'id': 'a'}, {'id': 'b', 'refill_at': 900, 'slot': 1}, {'id': 'c', 'refill_at': 500, 'slot': 2}
        self.assertEqual([x['id'] for x in r.order([a, b, c])], ['c', 'b', 'a'])
        self.assertEqual(r.due([a, b, c], 600), [c])

    def test_server_requests_scan_once(self):
        s.STATE = s.fresh()
        s.STATE['profiles'] = [{'id': 'x', 'label': 'x@gmail.com', 'balance': 2, 'slot': 0, 'refill_at': 10}]
        self.assertTrue(s.refill_check(100)); self.assertIn({'type': 'scan_flow', 'background': True}, s.STATE['bridge_requests'])
        self.assertFalse(s.refill_check(200), 'at most every 10 minutes')
        self.assertEqual(s.STATE['profiles'][0]['refill_at'], 100 + r.RETRY, 'unread balance (window closed): asked again in an hour')
        self.assertFalse(s.refill_check(800), 'not every 10 minutes while the window stays closed')
        c = {'id': 'cl'}
        s.flow_scan(s.STATE, c, [{'email': 'x@gmail.com', 'slot': 0, 'balance': 50}])
        self.assertNotIn('refill_at', s.STATE['profiles'][0]); self.assertNotIn('blocked', s.STATE['profiles'][0])


if __name__ == '__main__':
    unittest.main()
