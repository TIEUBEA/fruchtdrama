"""Claude model and effort (« Écrite par » = Claude): validation, defaults, settings and task payload."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
os.environ.pop('FRUCHT_BACKUPS', None)
SPEC = importlib.util.spec_from_file_location('studio_claude_model', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


class ClaudeModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port; cls.base = f'http://127.0.0.1:{s.PORT}'
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh()

    def post(self, path, body):
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={'Origin': self.base, 'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(r).read())

    def refused(self, path, body):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post(path, body)
        return e.exception.code, json.loads(e.exception.read())['error']

    def job(self, **config):
        self.post('/api/job', {'brief': 'Une orange cache un secret à sa famille.', 'mode': 'idea', 'config': config})
        return s.STATE['jobs'][0]

    def tasks(self, j, kind='chat_text'):
        return [t for t in s.STATE['tasks'] if t['job'] == j['id'] and t['kind'] == kind]

    def test_default_is_opus_high(self):
        j = self.job(provider='claude')
        self.assertEqual((j['config']['claude_model'], j['config']['claude_effort']), ('opus-5.5', 'high'))
        t = self.tasks(j)[0]
        self.assertEqual(t['payload']['provider'], 'claude')
        self.assertEqual((t['payload']['claude_model'], t['payload']['claude_effort']), ('opus-5.5', 'high'))

    def test_choice_stored_sent_and_remembered(self):
        j = self.job(provider='claude', claude_model='fable-5.1', claude_effort='extra')
        self.assertEqual((j['config']['claude_model'], j['config']['claude_effort']), ('fable-5.1', 'extra'))
        payload = self.tasks(j)[0]['payload']
        self.assertEqual((payload['claude_model'], payload['claude_effort']), ('fable-5.1', 'extra'))
        self.assertEqual((s.STATE['settings']['claude_model'], s.STATE['settings']['claude_effort']), ('fable-5.1', 'extra'), 'last choice kept')
        j2 = self.job(provider='claude')
        self.assertEqual(j2['config']['claude_model'], 'fable-5.1', 'next episode starts from the last choice')
        state = self.post('/api/settings', {'claude_model': 'sonnet-5.5', 'claude_effort': 'medium'})
        self.assertEqual((state['settings']['claude_model'], state['settings']['claude_effort']), ('sonnet-5.5', 'medium'))

    def test_invalid_values_refused_clearly(self):
        for bad, word in (({'claude_model': 'gpt-5'}, 'Modèle Claude inconnu'), ({'claude_effort': 'max'}, 'Effort Claude inconnu'), ({'claude_model': 'opus'}, 'Opus 5.5')):
            code, error = self.refused('/api/job', {'brief': 'Une orange cache un secret.', 'mode': 'idea', 'config': {'provider': 'claude', **bad}})
            self.assertEqual(code, 400); self.assertIn(word, error)
        self.assertEqual(s.STATE['jobs'], [], 'nothing created on a refusal')
        self.assertEqual(self.refused('/api/settings', {'claude_effort': 'turbo'})[0], 400)
        self.assertNotIn('claude_effort', s.STATE['settings'])

    def test_chatgpt_tasks_untouched(self):
        j = self.job(provider='chatgpt')
        payload = self.tasks(j)[0]['payload']
        self.assertEqual(payload['provider'], 'chatgpt')
        self.assertNotIn('claude_model', payload); self.assertNotIn('claude_effort', payload)
        self.assertNotIn('claude_model', s.STATE['settings'], 'a ChatGPT episode does not change the Claude choice')

    def test_older_episode_switched_to_claude_gets_defaults(self):
        j = self.job(provider='chatgpt')
        j['config'].pop('claude_model'); j['config'].pop('claude_effort'); j['config']['provider'] = 'claude'
        s.STATE['tasks'].clear()
        s.add_task(j, 'chat_text', {'provider': 'claude', 'prompt': 'x'}, 'rewrite_meta')
        payload = self.tasks(j)[0]['payload']
        self.assertEqual((payload['claude_model'], payload['claude_effort']), ('opus-5.5', 'high'))
        # Images stay with ChatGPT: no Claude fields on them.
        s.add_task(j, 'chat_image', {'provider': 'chatgpt', 'prompt': 'y'}, 'cover')
        self.assertNotIn('claude_model', self.tasks(j, 'chat_image')[0]['payload'])


if __name__ == '__main__':
    unittest.main()
