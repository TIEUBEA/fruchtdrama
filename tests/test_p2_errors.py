"""P2-01/P2-02: typed task failures. Unit tests of errors.py and HTTP integration through the bridge."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, unittest, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p2_errors', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import errors


class ClassifyTests(unittest.TestCase):
    def test_explicit_kind_wins_and_unknown_kind_is_ignored(self):
        self.assertEqual(errors.classify({'error_kind': 'refusal', 'error': 'Interface non reconnue'}), 'refusal')
        self.assertEqual(errors.classify({'error_kind': 'hack', 'error': 'Interface non reconnue'}), 'interface')

    def test_messages_from_older_extensions(self):
        cases = {
            'Contrôle du fournisseur : intervention manuelle nécessaire.': 'challenge',
            'Connexion requise. Connectez-vous vous-même.': 'login',
            'Compte Flow différent ou session expirée ; aucun envoi effectué.': 'login',
            'Quota du fournisseur atteint. Reprenez après renouvellement.': 'quota',
            'Crédits Flow insuffisants signalés par le fournisseur ; aucun envoi effectué.': 'credits',
            'Génération trop longue ou média non détecté.': 'timeout',
            'Envoi bloqué : texte présent, commande inactive.': 'interface',
            'Redémarrage : génération précédente à vérifier': 'restart',
            'Quelque chose de nouveau': 'other',
        }
        for message, kind in cases.items():
            with self.subTest(message=message):
                self.assertEqual(errors.classify({'error': message}), kind)
        self.assertEqual(errors.classify({'error': 'x', 'flow_blocked': 'credits'}), 'credits')

    def test_retry_after_is_bounded(self):
        self.assertEqual(errors.retry_after({'retry_after': 7500}), 7500)
        self.assertEqual(errors.retry_after({'retry_after': 5}), 60)
        self.assertEqual(errors.retry_after({'retry_after': 10 ** 9}), 48 * 3600)
        for bad in ({}, {'retry_after': 'abc'}, {'retry_after': -3}, {'retry_after': None}):
            self.assertIsNone(errors.retry_after(bad))

    def test_human_kinds_get_an_action_message_never_a_bypass(self):
        text = errors.message('challenge', 'Contrôle du fournisseur')
        self.assertIn('résolvez-la vous-même', text); self.assertIn('ne contourne jamais', text)
        self.assertEqual(errors.message('timeout', 'x' * 2000), 'x' * 1200)
        self.assertEqual(set(errors.RETRYABLE) & set(errors.HUMAN), set())


def job():
    j = {'id': s.uid(), 'stage': 'images', 'status': 'running', 'events': [], 'brief': 'b', 'candidates': [], 'flow_profile': None,
         'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p', 'file': 'ref.png'}],
         'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'scene', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}]}],
         'config': {'scene_count': 1, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)'}}
    s.STATE['jobs'].append(j); return j


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh()
        pair = self.req('/api/bridge/pair', {'code': s.STATE['pair_code'], 'label': 'QA', 'role': 'creation', 'ai_provider': 'chatgpt'})
        self.client = pair['client']; self.auth = {'Authorization': 'Bearer ' + pair['token']}

    def req(self, path, body=None, headers=None):
        h = {'Origin': self.base, 'Content-Type': 'application/json', **(headers or {})}
        with urllib.request.urlopen(urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=h)) as r:
            return json.load(r)

    def claim(self):
        return self.req('/api/bridge/task?client=' + self.client, headers=self.auth)

    def report(self, t, result):
        return self.req('/api/bridge/result', {'client': self.client, 'task': t['id'], 'result': result}, self.auth)

    def test_challenge_is_typed_and_explained(self):
        j = job(); s.schedule(j); t = self.claim()
        ack = self.report(t, {'ok': False, 'error': 'Contrôle du fournisseur : intervention manuelle nécessaire.', 'error_kind': 'challenge'})
        self.assertEqual(ack['job_status'], 'attention')
        self.assertEqual(j['last_error']['kind'], 'challenge'); self.assertEqual(j['last_error']['slot'], 'image:0')
        self.assertEqual(s.STATE['tasks'][-1]['error_kind'], 'challenge')
        self.assertIn('résolvez-la vous-même', j['events'][-1]['text'])
        public = next(x for x in self.req('/api/state')['jobs'] if x['id'] == j['id'])
        self.assertEqual(public['last_error']['kind'], 'challenge', 'the interface can show the action banner')

    def test_resume_and_success_clear_the_error(self):
        j = job(); s.schedule(j); t = self.claim()
        self.report(t, {'ok': False, 'error': 'Envoi bloqué : commande inactive.'}); self.assertEqual(j['last_error']['kind'], 'interface')
        self.req('/api/job/' + j['id'], {'action': 'resume'}); self.assertNotIn('last_error', j)
        t = self.claim(); self.report(t, {'ok': False, 'error': 'Envoi bloqué'}); j['status'] = 'running'
        s.STATE['tasks'][-1]['status'] = 'claimed'
        from PIL import Image; Image.new('RGB', (32, 64), (10, 200, 30)).save(s.job_dir(j) / 'img.png'); Image.new('RGB', (32, 64), 'orange').save(s.job_dir(j) / 'ref.png')
        s.accept_task_result(s.STATE['tasks'][-1], {'ok': True, 'file': 'img.png'})
        self.assertNotIn('last_error', j)

    def test_invalid_answer_and_restart_are_typed(self):
        j = job(); s.schedule(j); t = self.claim()
        self.report(t, {'ok': True, 'file': '../evil.png'})
        self.assertEqual(j['last_error']['kind'], 'other')
        j2 = job(); j2['status'] = 'running'; s.schedule(j2); self.claim()
        s.recover_after_restart(); self.assertEqual(j2['last_error']['kind'], 'restart')


if __name__ == '__main__':
    unittest.main()
