"""P1-4: Flow dry run. Full bridge flow over HTTP: dry run, no reservation, pause, then real production."""
import importlib.util, json, os, pathlib, tempfile, threading, unittest, urllib.error, urllib.request

TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p1_dry', pathlib.Path(__file__).parents[1] / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
from tests import accounts_ready; accounts_ready.install(s)  # 0.1.91: accounts ready before starting


def script():
    return {'title': 'Omas Reise', 'cover_title': 'WER?', 'description': 'd',
            'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'Orange', 'voice': 'v', 'image_prompt': 'p'}],
            'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}]} for _ in range(4)]}


def clip_job(dry=True):
    from PIL import Image
    j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'brief': 'b', 'characters': [], 'scenes': [], 'candidates': [], 'flow_profile': 'flow',
         'config': {'scene_count': 4, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)', 'flow_model': 'gemini_omni_flash', 'dry_run': dry}}
    s.STATE['jobs'].append(j); s.store_script(j, script()); j['stage'] = 'clips'
    for i, scene in enumerate(j['scenes']):
        Image.new('RGB', (32, 64), (i * 50, 9, 9)).save(s.job_dir(j) / f'scene{i}.png'); scene['image'] = f'scene{i}.png'
    return j


class DryRunHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh(); s.STATE['profiles'].append({'id': 'flow', 'label': 'Flow', 'balance': 40})
        pair = self.req('/api/bridge/pair', {'code': s.STATE['pair_code'], 'label': 'QA', 'role': 'flow', 'flow_profile': 'flow'})
        self.client = pair['client']; self.auth = {'Authorization': 'Bearer ' + pair['token']}

    def req(self, path, body=None, headers=None, origin=None):
        h = {'Origin': origin or self.base, 'Content-Type': 'application/json', **(headers or {})}
        request = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=h)
        with urllib.request.urlopen(request) as r:
            return json.load(r)

    def claim(self):
        return self.req('/api/bridge/task?client=' + self.client, headers=self.auth)

    def report(self, task, result):
        return self.req('/api/bridge/result', {'client': self.client, 'task': task['id'], 'result': result}, self.auth)

    def test_dry_run_then_real_production(self):
        j = clip_job()
        t = self.claim()
        self.assertEqual(t['slot'], 'clip:0'); self.assertTrue(t['payload']['dry_run'])
        self.assertEqual(s.STATE['profiles'][0]['balance'], 40, 'no reservation for a dry run'); self.assertNotIn('reservation', t)
        ack = self.report(t, {'ok': False, 'dry_run': True, 'generation_submitted': False, 'error': 'Essai à blanc réussi : Flow prêt.'})
        self.assertEqual(ack['job_status'], 'paused'); self.assertTrue(j['dry_run_passed'])
        self.assertIn('Désactivez l’essai à blanc', j['events'][-1]['text'])
        self.assertIsNone(self.claim(), 'a paused production never sends')
        self.assertEqual(s.uncertain_clip_tasks(j), [])
        self.req('/api/job/' + j['id'], {'action': 'set_dry_run', 'enabled': False})
        self.req('/api/job/' + j['id'], {'action': 'resume'})
        real = self.claim()
        self.assertEqual(real['slot'], 'clip:0'); self.assertNotIn('dry_run', real['payload'])
        self.assertEqual(s.STATE['profiles'][0]['balance'], 28, 'real generation reserves credits')

    def test_failed_dry_run_reports_the_problem(self):
        j = clip_job(); t = self.claim()
        self.report(t, {'ok': False, 'generation_submitted': False, 'error': 'Flow : coût affiché différent du budget prévu. Aucun envoi effectué.'})
        self.assertEqual(j['status'], 'attention'); self.assertIn('coût affiché différent', j['events'][-1]['text'])
        self.assertNotIn('dry_run_passed', j)

    def test_dry_run_flag_cannot_be_forged_by_a_real_task(self):
        j = clip_job(dry=False); t = self.claim(); self.assertEqual(s.STATE['profiles'][0]['balance'], 28)
        self.report(t, {'ok': False, 'dry_run': True, 'generation_submitted': False, 'error': 'x'})
        self.assertNotIn('dry_run_passed', j); self.assertEqual(j['status'], 'attention')
        self.assertEqual(s.STATE['profiles'][0]['balance'], 40, 'real task not submitted: normal refund')

    def test_switching_mode_rebuilds_queued_tasks_and_waits_for_running_ones(self):
        j = clip_job(dry=False); s.schedule(j)
        queued = [t for t in s.STATE['tasks'] if t['status'] == 'queued']; self.assertNotIn('dry_run', queued[0]['payload'])
        self.req('/api/job/' + j['id'], {'action': 'set_dry_run', 'enabled': True})
        self.assertEqual(queued[0]['status'], 'cancelled'); self.assertIn('Essai à blanc activé', j['events'][-1]['text'])
        t = self.claim(); self.assertTrue(t['payload']['dry_run'])
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/job/' + j['id'], {'action': 'set_dry_run', 'enabled': False})
        self.assertIn('tâche est en cours', json.load(e.exception)['error'])
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/job/' + j['id'], {'action': 'set_dry_run', 'enabled': False}, origin='https://evil.example')
        self.assertEqual(e.exception.code, 403)

    def test_creation_option_and_restart_safety(self):
        self.req('/api/job', {'brief': 'x', 'config': {'dry_run': True}}); self.assertIs(s.STATE['jobs'][0]['config']['dry_run'], True)
        j = clip_job(); self.claim(); s.recover_after_restart()
        self.assertEqual(s.uncertain_clip_tasks(j), [], 'an interrupted dry run is never an uncertain paid submission')


if __name__ == '__main__':
    unittest.main()
