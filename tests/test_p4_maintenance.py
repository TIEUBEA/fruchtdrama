"""P4-1: deletion to a recoverable trash, purge with backup, failure report without secrets."""
import datetime as dt, importlib.util, json, os, pathlib, sys, tempfile, threading, time, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p4_maintenance', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import maintenance


def job(title='A', status='paused'):
    j = {'id': s.uid(), 'title': title, 'stage': 'images', 'status': status, 'events': [{'at': s.now(), 'text': 'contact main@gmail.com token=abcdefgh12345'}],
         'brief': 'b', 'candidates': [], 'flow_profile': None, 'characters': [], 'scenes': [], 'config': {'scene_count': 1, 'language': 'Deutsch (de-DE)'}}
    s.STATE['jobs'].append(j); (s.job_dir(j) / 'scene0.png').write_bytes(b'img'); return j


class UnitTests(unittest.TestCase):
    def test_purge_keeps_recent_and_unresolved(self):
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=40)).isoformat()
        st = {'jobs': [{'id': 'j', 'events': [{'text': str(i)} for i in range(400)]}], 'tasks': [
            {'id': 1, 'job': 'j', 'status': 'done', 'created': old},
            {'id': 2, 'job': 'j', 'status': 'done', 'created': dt.datetime.now(dt.timezone.utc).isoformat()},
            {'id': 3, 'job': 'gone', 'status': 'queued', 'created': old},
            {'id': 4, 'job': 'j', 'status': 'failed', 'created': old, 'kind': 'flow_video', 'reservation': {'refunded': False}},
            {'id': 5, 'job': 'j', 'status': 'queued', 'created': old}]}
        r = maintenance.purge(st, time.time())
        self.assertEqual([t['id'] for t in st['tasks']], [2, 4, 5], 'old finished removed; recent, active and possibly charged Flow kept')
        self.assertEqual(r, {'tasks_removed': 2, 'events_removed': 100}); self.assertEqual(st['jobs'][0]['events'][0]['text'], '100')

    def test_redaction(self):
        text = maintenance.redact('Authorization: Bearer abc.def-123 pair_code=deadbeef token: "ZZZZZZZZZZ" a@b.com x-access-token:ghp_x@github.com')
        for secret in ('abc.def-123', 'deadbeef', 'ZZZZZZZZZZ', 'a@b.com', 'ghp_x'):
            self.assertNotIn(secret, text)

    def test_backup_rotation(self):
        folder = pathlib.Path(tempfile.mkdtemp())
        for i in range(12):
            (folder / 'sauvegardes').mkdir(exist_ok=True); (folder / 'sauvegardes' / f'state-2026010{i:02}.json').write_text('{}')
        maintenance.backup_state(folder, {'x': 1})
        self.assertEqual(len(list((folder / 'sauvegardes').glob('state-*.json'))), 10)


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

    def req(self, path, body=None, origin=None, raw=False, headers=None):
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers={'Origin': origin or self.base, 'Content-Type': 'application/json', **(headers or {})})
        with urllib.request.urlopen(r) as x:
            return x.read().decode() if raw else json.load(x)

    def error(self, path, body, origin=None):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req(path, body, origin)
        return e.exception.code, json.load(e.exception)['error']

    def test_delete_moves_to_trash_and_backs_up(self):
        j = job(); keep = job('B'); s.STATE['tasks'] += [{'id': 't', 'job': j['id'], 'status': 'done'}, {'id': 'u', 'job': keep['id'], 'status': 'done'}]
        s.night_add(keep)
        state = self.req('/api/job/' + j['id'], {'action': 'delete'})
        self.assertNotIn(j['id'], [x['id'] for x in state['jobs']]); self.assertEqual([t['id'] for t in s.STATE['tasks']], ['u'])
        trashed = pathlib.Path(TEMP.name) / 'corbeille' / state['trashed']
        self.assertEqual((trashed / 'scene0.png').read_bytes(), b'img', 'files kept in the trash')
        backups = list((pathlib.Path(TEMP.name) / 'sauvegardes').glob('state-*.json'))
        self.assertTrue(any(j['id'] in b.read_text() for b in backups), 'state copy taken before deletion')
        self.assertEqual(s.night()['ids'], [keep['id']])

    def test_delete_refusals(self):
        busy = job(); s.STATE['tasks'].append({'id': 'c', 'job': busy['id'], 'status': 'claimed', 'kind': 'chat_image', 'slot': 'image:0'})
        self.assertIn('tâche est en cours', self.error('/api/job/' + busy['id'], {'action': 'delete'})[1])
        rendering = job(status='rendering'); self.assertIn('Montage', self.error('/api/job/' + rendering['id'], {'action': 'delete'})[1])
        uncertain = job(); uncertain['scenes'] = [{'image': 'x'}]
        s.STATE['tasks'].append({'id': 'f', 'job': uncertain['id'], 'kind': 'flow_video', 'slot': 'clip:0', 'status': 'failed', 'reservation': {'refunded': False}})
        self.assertIn('Flow', self.error('/api/job/' + uncertain['id'], {'action': 'delete'})[1])
        self.assertEqual(self.error('/api/job/' + busy['id'], {'action': 'delete'}, 'https://evil.example')[0], 403)

    def test_report_has_no_secret(self):
        job(); s.STATE['clients']['c'] = {'label': 'PC', 'role': 'all', 'ai_provider': 'both', 'seen': s.now()}
        (pathlib.Path(TEMP.name) / 'server-errors.log').write_text('Traceback Bearer secret-token-123 for owner@mail.com\n')
        text = self.req('/api/report', raw=True)
        self.assertIn('Rapport de panne FruchtDrama', text); self.assertIn('« A »', text); self.assertIn('Traceback', text)
        for secret in (s.STATE['token'], s.STATE['pair_code'], 'main@gmail.com', 'abcdefgh12345', 'secret-token-123', 'owner@mail.com'):
            self.assertNotIn(secret, text)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/report', raw=True, headers={'Sec-Fetch-Site': 'cross-site'})
        self.assertEqual(e.exception.code, 403)

    def test_purge_route(self):
        job(); r = self.req('/api/maintenance/purge', {})
        self.assertEqual(r['purge']['tasks_removed'], 0)


if __name__ == '__main__':
    unittest.main()
