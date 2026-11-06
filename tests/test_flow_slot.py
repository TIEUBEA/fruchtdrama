"""06/11/2026: Google renumbered the signed-in accounts (/u/3 became another one): the account is found again by address."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, unittest, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_slot', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


class FlowSlot(unittest.TestCase):
    def test_new_number_moves_profile_task_and_project(self):
        s.STATE = s.fresh()
        url = 'https://flow.google.com/u/3/project/abc'
        s.STATE['profiles'] = [{'id': 'p', 'label': 'x', 'flow_url': url, 'slot': 3}]
        j = {'id': 'j', 'events': [], 'flow_projects': {'p': url}}; s.STATE['jobs'] = [j]
        t = {'id': 't', 'job': 'j', 'kind': 'flow_video', 'status': 'claimed', 'client': 'c', 'profile': 'p', 'slot': 'clip:0',
             'payload': {'flow_route': {'url': url, 'email': 'x@example.org', 'client': 'c'}}}
        s.STATE['tasks'] = [t]; s.STATE['clients'] = {'c': {'id': 'c', 'role': 'all'}}
        server = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/bridge/flow-slot', data=json.dumps({'task': 't', 'client': 'c', 'slot': 8}).encode(),
                                         headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + s.STATE['token']})
            self.assertTrue(json.loads(urllib.request.urlopen(req).read())['ok'])
        finally:
            server.shutdown()
        new = 'https://flow.google.com/u/8/project/abc'
        self.assertEqual(s.STATE['profiles'][0]['flow_url'], new)
        self.assertEqual(t['payload']['flow_route']['url'], new)
        self.assertEqual(j['flow_projects']['p'], new)
