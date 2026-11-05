"""P1-2: one shared character sheet for the whole cast. Unit and HTTP integration tests."""
import importlib.util, io, json, os, pathlib, tempfile, threading, unittest, urllib.error, urllib.request

TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p1_sheet', pathlib.Path(__file__).parents[1] / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


def script(cast=('orange', 'kiwi')):
    names = {'orange': 'Oma', 'kiwi': 'Kiko', 'plum': 'Pia'}
    return {'title': 'Omas Reise', 'cover_title': 'WER FÄHRT?', 'description': 'Beschreibung',
            'characters': [{'id': c, 'name': names[c], 'appearance': f'{c} fruit', 'voice': 'v', 'image_prompt': f'{c} reference'} for c in cast],
            'scenes': [{'characters': [cast[0]], 'meaning': 'm', 'image_prompt': f'scene {i}', 'video_prompt': 'v', 'dialogue': [{'speaker': cast[0], 'text': 'Hallo'}]} for i in range(4)]}


def make_job(sheet=1, cast=('orange', 'kiwi')):
    j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'brief': 'b', 'characters': [], 'scenes': [], 'candidates': [], 'flow_profile': None,
         'config': {'scene_count': 4, 'provider': 'chatgpt', 'flow_cost': 10, 'language': 'Deutsch (de-DE)'}}
    if sheet:
        j['character_sheet'] = sheet
    s.STATE['jobs'].append(j); s.store_script(j, script(cast)); s.schedule(j); return j


def png(color=(200, 120, 20), size=(64, 128)):
    from PIL import Image
    buffer = io.BytesIO(); Image.new('RGB', size, color).save(buffer, 'PNG'); return buffer.getvalue()


def active():
    return [t for t in s.STATE['tasks'] if t['status'] in ('queued', 'claimed')]


class SheetTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_one_paid_image_for_the_whole_cast(self):
        j = make_job(cast=('orange', 'kiwi', 'plum'))
        tasks = active(); self.assertEqual([t['slot'] for t in tasks], ['characters'])
        prompt = tasks[0]['payload']['prompt']
        self.assertIn('ONE character reference sheet', prompt)
        for name in ('Oma (orange)', 'Kiko (kiwi)', 'Pia (plum)'):
            self.assertIn(name, prompt)
        self.assertEqual(tasks[0]['payload']['attachments'], [])

    def test_sheet_result_feeds_every_character_and_scene_images(self):
        j = make_job(); t = active()[0]; t['status'] = 'claimed'
        (s.job_dir(j) / 'sheet.png').write_bytes(png())
        s.accept_task_result(t, {'ok': True, 'file': 'sheet.png'})
        self.assertEqual(j['character_sheet_file'], 'sheet.png'); self.assertTrue(all(c['file'] == 'sheet.png' for c in j['characters']))
        self.assertEqual(j['stage'], 'images'); nxt = active()[0]
        self.assertEqual(nxt['slot'], 'image:0'); self.assertEqual(nxt['payload']['attachments'], [s.asset_url(j, 'sheet.png')], 'sheet attached once')

    def test_scene_identical_to_sheet_is_rejected(self):
        j = make_job(); t = active()[0]; t['status'] = 'claimed'
        (s.job_dir(j) / 'sheet.png').write_bytes(png()); s.accept_task_result(t, {'ok': True, 'file': 'sheet.png'})
        (s.job_dir(j) / 'copy.png').write_bytes(png()); image = active()[0]; image['status'] = 'claimed'
        with self.assertRaisesRegex(ValueError, 'copie exacte'):
            s.accept_task_result(image, {'ok': True, 'file': 'copy.png'})
        self.assertNotIn('image', j['scenes'][0])

    def test_single_character_and_legacy_jobs_keep_individual_references(self):
        single = make_job(cast=('orange',)); self.assertEqual([t['slot'] for t in active()], ['character:orange'])
        s.STATE = s.fresh()
        legacy = make_job(sheet=None); self.assertEqual([t['slot'] for t in active()], ['character:orange'])

    def test_partially_received_legacy_references_do_not_restart_a_sheet(self):
        j = make_job(); active()[0]['status'] = 'cancelled'
        j['characters'][0]['file'] = 'own.png'; s.schedule(j)
        self.assertEqual([t['slot'] for t in active()], ['character:kiwi'])

    def test_quality_review_attaches_sheet_once(self):
        j = make_job(); j['characters'][0]['file'] = j['characters'][1]['file'] = 'sheet.png'
        self.assertEqual(s.image_assets(j), [s.asset_url(j, 'sheet.png')])


class SheetHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh()

    def req(self, path, body=None, headers=None, raw=None):
        h = {'Origin': self.base, 'Content-Type': 'application/json', **(headers or {})}
        data = raw if raw is not None else json.dumps(body).encode() if body is not None else None
        with urllib.request.urlopen(urllib.request.Request(self.base + path, data=data, headers=h)) as r:
            return json.load(r)

    def test_new_productions_use_the_sheet(self):
        self.req('/api/job', {'brief': 'x', 'config': {}}); self.assertEqual(s.STATE['jobs'][0]['character_sheet'], 1)

    def test_characters_detail_switch_only_before_drawing(self):
        # Episode page « Simple | Détaillé »: changes the level while nothing is drawn, then only shows it.
        j = make_job(); j['config']['characters_detail'] = 'simple'
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/job/' + j['id'], {'action': 'characters_detail', 'level': 'detailed'})
        self.assertIn('en cours de dessin', json.load(e.exception)['error'], 'sheet already queued')
        for t in active():
            t['status'] = 'cancelled'
        self.req('/api/job/' + j['id'], {'action': 'characters_detail', 'level': 'detailed'})
        self.assertEqual(j['config']['characters_detail'], 'detailed')
        with self.assertRaises(urllib.error.HTTPError):
            self.req('/api/job/' + j['id'], {'action': 'characters_detail', 'level': 'ultra'})
        j['character_sheet_file'] = 'characters_x.png'
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/job/' + j['id'], {'action': 'characters_detail', 'level': 'simple'})
        self.assertIn('déjà dessinés', json.load(e.exception)['error']); self.assertEqual(j['config']['characters_detail'], 'detailed')

    def test_manual_sheet_upload_and_invalid_slot(self):
        j = make_job()
        self.req(f"/api/upload?job={j['id']}&slot=characters&ext=png", raw=png(), headers={'Content-Type': 'application/octet-stream'})
        self.assertTrue(j['character_sheet_file'].startswith('characters_')); self.assertEqual(j['stage'], 'images')
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req(f"/api/upload?job={j['id']}&slot=charactersx&ext=png", raw=png(), headers={'Content-Type': 'application/octet-stream'})
        self.assertIn('Emplacement', json.load(e.exception)['error'])
        with self.assertRaises(urllib.error.HTTPError):
            self.req(f"/api/upload?job={j['id']}&slot=characters&ext=mp4", raw=b'x', headers={'Content-Type': 'application/octet-stream'})

    def test_failed_sheet_is_offered_for_recovery_without_new_generation(self):
        pair = self.req('/api/bridge/pair', {'code': s.STATE['pair_code'], 'label': 'QA', 'role': 'creation', 'ai_provider': 'chatgpt'})
        auth = {'Authorization': 'Bearer ' + pair['token']}
        j = make_job(); t = self.req('/api/bridge/task?client=' + pair['client'], headers=auth); self.assertEqual(t['slot'], 'characters')
        self.req('/api/bridge/result', {'client': pair['client'], 'task': t['id'], 'result': {'ok': False, 'error': 'Image pas encore chargée'}}, auth)
        self.assertEqual(j['status'], 'attention')
        rows = self.req('/api/bridge/recoverable-media?client=' + pair['client'], headers=auth)
        self.assertEqual([r['slot'] for r in rows], ['characters'])
        recovered = self.req('/api/bridge/recover-media', {'client': pair['client'], 'previous_task': t['id']}, auth)
        self.assertEqual(recovered['kind'], 'chat_image_collect'); self.assertEqual(recovered['slot'], 'characters')
        upload = self.req(f"/api/bridge/upload?job={j['id']}&slot=characters&ext=png", raw=png(), headers={**auth, 'Content-Type': 'application/octet-stream'})
        self.req('/api/bridge/result', {'client': pair['client'], 'task': recovered['id'], 'result': {'ok': True, 'file': upload['file']}}, auth)
        self.assertEqual(j['character_sheet_file'], upload['file']); self.assertEqual(j['stage'], 'images')
        self.assertEqual(len([x for x in s.STATE['tasks'] if x['slot'] == 'characters' and x['kind'] == 'chat_image']), 1, 'no second paid sheet')


if __name__ == '__main__':
    unittest.main()
