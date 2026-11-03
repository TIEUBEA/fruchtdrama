"""Atelier-like start: ten stories, decision sheet, validation before anything is paid."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_ideas', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import ideas

IDEAS = {'ideas': [{'title': f'Idée {i}', 'pitch': f'À dix ans, une petite pêche découvre le secret {i}.', 'why': 'Danger visible'} for i in range(10)]}
SHEET = {'logline': 'Une pêche sauve sa sœur.', 'engine': 'Sauver sa sœur', 'obstacle': 'Le père', 'twist': 'La mère revient',
         'image': 'Deux pêches derrière une porte', 'question': 'Va-t-elle réussir ?', 'titles': ['LA PORTE', 'LE SECRET', 'LA NUIT'],
         'hooks': ['Papa, pourquoi elle est enfermée ?', 'Ouvre cette porte !', 'Il reste une heure.'], 'end_call': 'Écris 1 ou 2 !',
         'cast': [{'name': 'Pêchette', 'role': 'protagoniste', 'appearance': 'pêche, 10 ans'}, {'name': 'Papa', 'role': 'antagoniste', 'appearance': 'pêche adulte'}]}


class UnitTests(unittest.TestCase):
    def test_validate_ideas(self):
        self.assertEqual(len(ideas.validate_ideas(IDEAS)), 10)
        with self.assertRaises(ValueError):
            ideas.validate_ideas({'ideas': IDEAS['ideas'][:3]})
        with self.assertRaises(ValueError):
            ideas.validate_ideas({'nope': 1})

    def test_validate_sheet_and_brief(self):
        sh = ideas.validate_sheet(SHEET)
        bad = dict(SHEET); bad['twist'] = ''
        with self.assertRaisesRegex(ValueError, 'Twist'):
            ideas.validate_sheet(bad)
        b = ideas.brief(sh, 1, 2)
        self.assertIn('LE SECRET', b); self.assertIn('« Il reste une heure. »', b); self.assertIn('Écris 1 ou 2', b)
        edited = ideas.apply_edits(sh, {'twist': 'Nouveau twist', 'cast': [{'name': 'Pêcha'}], 'evil': 'x'})
        self.assertEqual(edited['twist'], 'Nouveau twist'); self.assertEqual(edited['cast'][0]['name'], 'Pêcha'); self.assertNotIn('evil', edited)

    def test_trends_from_filon(self):
        jobs = [{'filon_only': True, 'candidates': [{'title': 'B', 'views': 5}, {'title': 'A', 'views': 9}, {'title': 'B', 'views': 1}]}, {'candidates': [{'title': 'X', 'views': 99}]}]
        self.assertEqual(ideas.trends(jobs), ['A', 'B'])


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

    def req(self, path, body):
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={'Origin': self.base, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def error(self, path, body):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req(path, body)
        return json.load(e.exception).get('error')

    def answer(self, slot, payload):
        t = next(t for t in s.STATE['tasks'] if t['slot'] == slot and t['status'] == 'queued')
        self.assertEqual(t['kind'], 'chat_text'); self.assertEqual(t['payload']['response_kind'], slot)
        t['status'] = 'claimed'; s.accept_task_result(t, {'ok': True, 'text': json.dumps(payload, ensure_ascii=False)})
        return t

    def create(self, **extra):
        st = self.req('/api/job', {'brief': extra.pop('brief', ''), 'mode': extra.pop('mode'), 'config': {'provider': 'chatgpt', 'scene_count': 4, 'language': 'Français (fr-FR)', **extra}})
        return s.job_by(st['jobs'][0]['id'])

    def test_ten_stories_then_sheet_then_script(self):
        j = self.create(mode='ideas')
        self.assertEqual(j['stage'], 'ideas')
        t = self.answer('ideas', IDEAS)
        self.assertIn('Français', t['payload']['prompt'])
        self.assertEqual(j['status'], 'waiting_review'); self.assertEqual(len(j['ideas']), 10)
        self.assertFalse([t for t in s.STATE['tasks'] if t['status'] == 'queued'], 'nothing else asked before choosing')
        self.assertIn('inconnue', self.error('/api/job/' + j['id'], {'action': 'pick_idea', 'index': 42}))
        self.req('/api/job/' + j['id'], {'action': 'pick_idea', 'index': 3})
        self.assertEqual(j['stage'], 'sheet'); self.assertIn('secret 3', j['brief'])
        self.answer('sheet', SHEET)
        self.assertEqual(j['status'], 'waiting_review'); self.assertFalse(any(t['kind'] == 'chat_image' for t in s.STATE['tasks']), 'no image before validation')
        self.req('/api/job/' + j['id'], {'action': 'approve_sheet', 'title': 2, 'hook': 1, 'sheet': {'twist': 'Twist corrigé'}})
        self.assertEqual(j['stage'], 'script'); self.assertEqual(j['title'], 'La nuit')
        script = next(t for t in s.STATE['tasks'] if t['slot'] == 'script' and t['status'] == 'queued')
        self.assertIn('« Ouvre cette porte ! »', script['payload']['prompt']); self.assertIn('Twist corrigé', script['payload']['prompt'])

    def test_revise_sheet_with_remarks_and_more_ideas(self):
        j = self.create(mode='idea', brief='Une petite cerise refuse de manger le gâteau de sa mère.')
        self.assertEqual(j['stage'], 'sheet')
        self.answer('sheet', SHEET)
        self.assertIn('remarques', self.error('/api/job/' + j['id'], {'action': 'revise_sheet', 'note': ' '}))
        self.req('/api/job/' + j['id'], {'action': 'revise_sheet', 'note': 'Rends le père plus ambigu'})
        t = next(t for t in s.STATE['tasks'] if t['slot'] == 'sheet' and t['status'] == 'queued')
        self.assertIn('Rends le père plus ambigu', t['payload']['prompt']); self.assertIn('LA PORTE', t['payload']['prompt'])
        j2 = self.create(mode='ideas'); self.answer('ideas', IDEAS)
        self.req('/api/job/' + j2['id'], {'action': 'more_ideas'})
        self.assertTrue(any(t['slot'] == 'ideas' and t['status'] == 'queued' and t['job'] == j2['id'] for t in s.STATE['tasks']))
        self.assertIn('idée', self.error('/api/job', {'mode': 'idea', 'brief': 'court', 'config': {'provider': 'chatgpt', 'scene_count': 4}}))

    def test_auto_sheet_and_bad_reply_retried(self):
        j = self.create(mode='idea', brief='Un petit citron et un seul parachute dans la montgolfière.', auto_sheet=True)
        self.answer('sheet', {'logline': 'incomplet'})
        self.assertEqual(j['status'], 'running'); self.assertEqual(j['start_attempts'], 1)
        self.answer('sheet', SHEET)
        self.assertEqual(j['stage'], 'script'); self.assertEqual(j['sheet_choice'], {'title': 0, 'hook': 0})


if __name__ == '__main__':
    unittest.main()
