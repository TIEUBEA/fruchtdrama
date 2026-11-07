"""P0 reliability requirements (docs/sudf/P0-fiabilite.md). Unit, HTTP integration and real ffmpeg montage tests."""
import contextlib, importlib.util, io, json, os, pathlib, shutil, subprocess, tempfile, threading, time, unittest, urllib.error, urllib.request

TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_p0', pathlib.Path(__file__).parents[1] / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
from tests import accounts_ready; accounts_ready.install(s)  # 0.1.91: accounts ready before starting
FFMPEG = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))


def script(n=4, language_word='Meer'):
    return {'title': 'Omas Reise', 'cover_title': 'MUSS OMA GEHEN?', 'description': 'Eine originelle KI-Geschichte.',
            'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'Orange, cremefarbener Cardigan', 'voice': 'Warme ältere Stimme', 'image_prompt': 'Figurenreferenz, Orange'}],
            'scenes': [{'characters': ['orange'], 'meaning': 'Ein Koffer steht neben Oma.', 'image_prompt': 'Oma mit Koffer', 'video_prompt': 'Ein ruhiger Plan.',
                        'dialogue': [{'speaker': 'orange', 'text': f'Wir fahren heute gemeinsam ans {language_word}.'}]} for _ in range(n)]}


def make_job(**extra):
    j = {'id': s.uid(), 'stage': 'research', 'status': 'running', 'events': [], 'config': {'scene_count': 4, 'provider': 'chatgpt', 'flow_cost': 10, 'query': 'früchte deutsch', 'language': 'Deutsch (de-DE)'},
         'brief': 'Omas Reise', 'characters': [], 'scenes': [], 'candidates': [], 'flow_profile': None,
         'selected': {'title': 'Référence', 'url': 'https://www.tiktok.com/@a/video/1'}, **extra}
    s.STATE['jobs'].append(j); return j


def scene_images(j):
    from PIL import Image
    for i, scene in enumerate(j['scenes']):
        name = f'scene{i}.png'; Image.new('RGB', (32, 64), (i * 50, 100, 200)).save(s.job_dir(j) / name); scene['image'] = name


def clip_job(n=4):
    """A production at the Flow stage with a funded, selected profile."""
    j = make_job(); s.store_script(j, script(n)); j['config']['scene_count'] = n; j['stage'] = 'clips'; scene_images(j)
    s.STATE['profiles'].append({'id': 'flow', 'label': 'Flow', 'balance': 100}); j['flow_profile'] = 'flow'
    return j


def uncertain_task(j, index=0, amount=10):
    """A flow_video whose submission outcome is unknown (e.g. failed after restart)."""
    t = {'id': s.uid(), 'job': j['id'], 'kind': 'flow_video', 'slot': f'clip:{index}', 'status': 'failed', 'profile': 'flow',
         'payload': {'prompt': 'x', 'cost': amount}, 'reservation': {'profile': 'flow', 'amount': amount, 'refunded': False}}
    s.STATE['tasks'].append(t); return t


def make_clip(path, seconds=2, audio=True):
    args = ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=orange:s=360x640:r=30:d={seconds}']
    if audio: args += ['-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}']
    args += ['-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p'] + (['-c:a', 'aac'] if audio else []) + ['-shortest', str(path)]
    subprocess.run(args, check=True, capture_output=True)


class Base(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh(); self.renders = []
        self._render = s.start_render; s.start_render = self.renders.append

    def tearDown(self):
        s.start_render = self._render


class MontageRecoveryTests(Base):
    """P0-01 and P0-02."""

    def test_failed_montage_is_retried_by_resume_without_new_tasks(self):
        j = make_job(stage='edit', status='attention'); s.store_script(j, script()); j['stage'] = 'edit'; j['status'] = 'attention'
        tasks_before = list(s.STATE['tasks'])
        s.schedule(j); self.assertEqual(self.renders, [], 'attention must wait for the owner')
        j['status'] = 'running'; s.schedule(j)
        self.assertEqual(self.renders, [j['id']]); self.assertEqual(j['status'], 'rendering')
        self.assertEqual(s.STATE['tasks'], tasks_before, 'a montage retry never queues a generation')
        s.schedule(j); self.assertEqual(self.renders, [j['id']], 'no double render while rendering')

    def test_finished_episode_is_not_rendered_again(self):
        j = make_job(stage='edit', status='running', final='/media/x/final.mp4'); s.schedule(j)
        self.assertEqual(self.renders, [])

    def test_restart_during_montage_restarts_render_only(self):
        rendering = make_job(stage='edit', status='rendering'); done = make_job(stage='done', status='done', final='/media/x/final.mp4')
        claimed = make_job(stage='clips', status='running'); s.store_script(claimed, script()); claimed['stage'] = 'clips'
        t = {'id': s.uid(), 'job': claimed['id'], 'kind': 'flow_video', 'slot': 'clip:0', 'status': 'claimed'}; s.STATE['tasks'].append(t)
        s.recover_after_restart()
        self.assertEqual(self.renders, [rendering['id']]); self.assertEqual(rendering['status'], 'rendering')
        self.assertIn('Redémarrage pendant le montage', rendering['events'][-2]['text'])
        self.assertEqual(done['status'], 'done'); self.assertEqual(t['status'], 'claimed', '0.1.99: the clip stays with its window, nothing sent again'); self.assertEqual(claimed['status'], 'running')
        self.assertTrue((pathlib.Path(TEMP.name) / 'state.json').is_file(), 'recovery is persisted')


class UncertainSubmissionTests(Base):
    """P0-03 and P0-04: never pay twice for a scene."""

    def test_schedule_never_resubmits_an_uncertain_scene(self):
        j = clip_job(); uncertain_task(j, 0)
        s.schedule(j)
        # 0.1.97: the uncertain scene never goes back to Flow; with Flow alone in the chain it is set aside, the others go on.
        self.assertEqual([t['slot'] for t in s.STATE['tasks'] if t['status'] == 'queued'], ['clip:1'])
        self.assertEqual(s.STATE['profiles'][0]['balance'], 100, 'no reservation')
        for i in (1, 2, 3):
            j['scenes'][i]['clip'] = f'clip{i}.mp4'
        for t in s.STATE['tasks']:
            if t['status'] == 'queued':t['status'] = 'cancelled'
        s.schedule(j)
        self.assertEqual([t for t in s.STATE['tasks'] if t['status'] == 'queued'], [], 'never the uncertain scene')
        self.assertEqual(j['status'], 'attention'); self.assertIn('Clip 1 :', j['events'][-1]['text'])

    def test_refunded_or_received_or_acknowledged_tasks_are_not_uncertain(self):
        j = clip_job()
        refunded = uncertain_task(j, 0); refunded['reservation']['refunded'] = True
        received = uncertain_task(j, 1); j['scenes'][1]['clip'] = 'clip1.mp4'
        acknowledged = uncertain_task(j, 2); acknowledged['acknowledged'] = s.now()
        no_reservation = uncertain_task(j, 3); no_reservation.pop('reservation')
        self.assertEqual(s.uncertain_clip_tasks(j), [])
        s.schedule(j); queued = [t for t in s.STATE['tasks'] if t['status'] == 'queued']
        self.assertEqual([t['slot'] for t in queued], ['clip:0'])

    def test_other_jobs_are_not_blocked(self):
        blocked = clip_job(); uncertain_task(blocked, 0)
        other = clip_job(); s.schedule(other)
        self.assertEqual(other['status'], 'running'); self.assertEqual(s.uncertain_clip_tasks(other), [])

    def test_public_state_lists_uncertain_scenes(self):
        j = clip_job(); uncertain_task(j, 2); uncertain_task(j, 2)
        public = next(x for x in s.public_state()['jobs'] if x['id'] == j['id'])
        self.assertEqual(public['uncertain_clips'], [2]); self.assertNotIn('uncertain_clips', j, 'state itself is unchanged')


class PromptTests(Base):
    """P0-05, P0-13."""

    def test_flow_prompt_has_no_german_label_in_other_languages(self):
        for language in s.CREATION_LANGUAGES:
            with self.subTest(language=language):
                s.STATE = s.fresh(); j = clip_job(); j['config']['language'] = language; s.schedule(j)
                prompt = s.STATE['tasks'][-1]['payload']['prompt']
                self.assertNotIn('Stimme:', prompt); self.assertIn('Voice: Warme ältere Stimme', prompt)

    def test_announced_word_limit_matches_validator(self):
        j = make_job(editorial_version=2, retention_version=1, hook_version=1, selected={'title': 'x', 'url': 'https://www.tiktok.com/@a/video/1'})
        prompt = s.script_prompt(j)
        self.assertIn('Au plus 20 mots parlés par scène', prompt); self.assertNotIn('Au plus 25 mots', prompt)
        legacy = make_job(selected={'title': 'x', 'url': 'https://www.tiktok.com/@a/video/1'})
        self.assertIn('Au plus 25 mots parlés par scène', s.script_prompt(legacy))


class ScriptRetryTests(Base):
    """P0-09."""

    def test_invalid_json_is_rewritten_at_most_twice(self):
        j = make_job(stage='script')
        for attempt, text in enumerate(['pas de JSON', '{"title": "incomplet"}', '{bad json']):
            t = {'id': str(attempt), 'job': j['id'], 'kind': 'chat_text', 'slot': 'script', 'status': 'claimed'}; s.STATE['tasks'].append(t)
            s.accept_task_result(t, {'ok': True, 'text': text})
            self.assertEqual(t['status'], 'failed'); self.assertEqual(j['characters'], [])
            queued = [x for x in s.STATE['tasks'] if x['status'] == 'queued']
            if attempt < 2:
                self.assertEqual(len(queued), 1); self.assertEqual(j['status'], 'running'); queued[0]['status'] = 'cancelled'
            else:
                self.assertEqual(queued, [])
        self.assertEqual(j['status'], 'attention'); self.assertEqual(j['editorial_attempts'], 3)

    def test_paused_production_is_not_rewritten(self):
        j = make_job(stage='script', status='paused'); t = {'id': 'x', 'job': j['id'], 'kind': 'chat_text', 'slot': 'script', 'status': 'claimed'}
        s.STATE['tasks'].append(t); s.accept_task_result(t, {'ok': True, 'text': 'pas de JSON'})
        self.assertEqual(j['status'], 'paused'); self.assertEqual([x for x in s.STATE['tasks'] if x['status'] == 'queued'], [])

    def test_valid_script_still_accepted(self):
        j = make_job(stage='script'); t = {'id': 'ok', 'job': j['id'], 'kind': 'chat_text', 'slot': 'script', 'status': 'claimed'}; s.STATE['tasks'].append(t)
        s.accept_task_result(t, {'ok': True, 'text': json.dumps(script())})
        self.assertEqual(t['status'], 'done'); self.assertEqual(j['stage'], 'characters')


class DispatchTests(Base):
    """P0-06, P0-07."""

    def test_dispatch_errors_are_logged_once_per_minute_and_loop_survives(self):
        s.LAST_ERRORS.clear(); original = s.flow_dispatch_tick
        s.flow_dispatch_tick = lambda: (_ for _ in ()).throw(RuntimeError('compte indisponible'))
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                s.dispatch_once(); s.dispatch_once()
        finally:
            s.flow_dispatch_tick = original
        self.assertEqual(err.getvalue().count('RuntimeError: compte indisponible'), 1)
        self.assertIn('Boucle de dispatch Flow', err.getvalue())

    def test_launch_failure_is_recorded_on_live_profile_under_lock(self):
        s.STATE['settings']['flow_auto'] = True
        s.STATE['clients']['browser'] = {'id': 'browser', 'role': 'flow', 'seen': '2000-01-01T00:00:00+00:00'}
        s.STATE['profiles'].append({'id': 'p', 'label': 'A', 'balance': 0, 'auto_enabled': True, 'flow_email': 'a@example.com',
                                    'flow_client': 'browser', 'flow_url': 'https://flow.google.com/project/abc'})
        # 0.1.90: only a production waiting for credits may start Chrome; a background reading never does.
        s.STATE['jobs'].append({'id': 'waiting', 'stage': 'clips', 'status': 'waiting_credit', 'events': [], 'config': {'flow_cost': 12}})
        original = s.flow_accounts.launch; locked = []

        def failing(profile):
            locked.append(s.LOCK._is_owned()); raise ValueError('Chrome introuvable')
        s.flow_accounts.launch = failing
        try:
            s.flow_dispatch_tick()
        finally:
            s.flow_accounts.launch = original
        p = s.STATE['profiles'][0]
        self.assertEqual(len(locked), 1, 'one launch attempt')
        self.assertIn('Chrome introuvable', p['credit_error']); self.assertEqual(p['credit_probe']['status'], 'failed')
        self.assertIn('credit_next_check', p)


class HttpTests(unittest.TestCase):
    """Integration through the real HTTP handler: P0-04, P0-10, P0-11."""

    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh(); self.renders = []; self._render = s.start_render; s.start_render = self.renders.append

    def tearDown(self):
        s.start_render = self._render

    def req(self, path, body=None, headers=None, raw=None):
        h = {'Origin': self.base, 'Content-Type': 'application/json', **(headers or {})}
        data = raw if raw is not None else json.dumps(body).encode() if body is not None else None
        with urllib.request.urlopen(urllib.request.Request(self.base + path, data=data, headers=h)) as r:
            return json.load(r)

    def error(self, path, body):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req(path, body)
        return e.exception.code, json.load(e.exception)['error']

    def test_uncertain_clip_never_resent_to_flow_until_owner_confirms_no_clip(self):
        j = clip_job(); j['status'] = 'attention'; t = uncertain_task(j, 1)
        # Reprendre makes the other clips (never the uncertain one on Flow).
        self.req('/api/job/' + j['id'], {'action': 'resume'})
        self.assertEqual([x['slot'] for x in s.STATE['tasks'] if x['status'] == 'queued'], ['clip:0'])
        for x in s.STATE['tasks']:
            if x['status'] == 'queued':x['status'] = 'cancelled'
        for i in (0, 2, 3):
            j['scenes'][i]['clip'] = f'clip{i}.mp4'
        j['status'] = 'attention'
        # 0.1.97: Reprendre is never refused; with Flow alone in the chain the uncertain clip is set aside and said.
        self.req('/api/job/' + j['id'], {'action': 'resume'})
        self.assertEqual([x for x in s.STATE['tasks'] if x['status'] == 'queued'], []); self.assertEqual(j['status'], 'attention')
        self.assertIn('Clip 2 :', j['alerts'][-1]['text'])
        code, message = self.error('/api/job/' + j['id'], {'action': 'confirm_no_clip', 'slot': 'clip:3'})
        self.assertIn('Aucun envoi Flow incertain', message)
        state = self.req('/api/job/' + j['id'], {'action': 'confirm_no_clip', 'slot': 'clip:1'})
        self.assertTrue(t['acknowledged']); self.assertFalse(t['reservation']['refunded'], 'no silent refund')
        self.assertEqual(next(x for x in state['jobs'] if x['id'] == j['id'])['uncertain_clips'], [])
        self.req('/api/job/' + j['id'], {'action': 'resume'})
        queued = [x for x in s.STATE['tasks'] if x['status'] == 'queued']
        self.assertEqual([x['slot'] for x in queued], ['clip:1']); self.assertEqual(j['status'], 'running')

    def test_confirm_requires_same_origin(self):
        j = clip_job(); uncertain_task(j, 0)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/job/' + j['id'], {'action': 'confirm_no_clip', 'slot': 'clip:0'}, {'Origin': 'https://evil.example'})
        self.assertEqual(e.exception.code, 403); self.assertTrue(s.uncertain_clip_tasks(j))

    def test_manual_upload_keeps_generation_running_on_another_scene(self):
        from PIL import Image
        j = clip_job(); j['stage'] = 'images'; j['scenes'][2].pop('image')
        running = {'id': s.uid(), 'job': j['id'], 'kind': 'flow_video', 'slot': 'clip:0', 'status': 'claimed', 'client': 'b'}
        same = {'id': s.uid(), 'job': j['id'], 'kind': 'chat_image', 'slot': 'image:2', 'status': 'claimed', 'client': 'b'}
        waiting = {'id': s.uid(), 'job': j['id'], 'kind': 'chat_image', 'slot': 'image:3', 'status': 'queued'}
        s.STATE['tasks'] += [running, same, waiting]
        buffer = io.BytesIO(); Image.new('RGB', (32, 64), (9, 9, 9)).save(buffer, 'PNG')
        self.req(f"/api/upload?job={j['id']}&slot=image:2&ext=png", raw=buffer.getvalue(), headers={'Content-Type': 'application/octet-stream'})
        self.assertEqual(running['status'], 'claimed', 'paid generation on another scene keeps running')
        self.assertEqual(same['status'], 'done'); self.assertEqual(waiting['status'], 'cancelled')
        self.assertTrue(j['scenes'][2]['image'].startswith('image_2_'))

    def test_default_research_query_follows_language(self):
        expected = {'Deutsch (de-DE)': 'KI Früchte Geschichten deutsch', 'Français (fr-FR)': 'histoires fruits IA français', 'English (en-US)': 'AI fruit drama stories English'}
        for language, query in expected.items():
            with self.subTest(language=language):
                self.req('/api/job', {'brief': 'x', 'config': {'language': language}})
                self.assertEqual(s.STATE['jobs'][0]['config']['query'], query)
                self.req('/api/job', {'brief': 'x', 'config': {'language': language, 'query': 'KI Früchte Geschichten deutsch'}})
                self.assertEqual(s.STATE['jobs'][0]['config']['query'], query, 'untouched German default follows language')
        self.req('/api/job', {'brief': 'x', 'config': {'language': 'Français (fr-FR)', 'query': '  fruits drame cuisine  '}})
        self.assertEqual(s.STATE['jobs'][0]['config']['query'], 'fruits drame cuisine', 'custom query kept')


@unittest.skipUnless(FFMPEG, 'ffmpeg and ffprobe required')
class RealMontageTests(unittest.TestCase):
    """P0-01 end to end with the real ffmpeg pipeline."""

    def setUp(self):
        s.STATE = s.fresh()

    def wait(self, j, statuses, timeout=180):
        end = time.time() + timeout
        while time.time() < end:
            if j['status'] in statuses and j['id'] not in s.BUSY:
                return
            time.sleep(.2)
        self.fail('montage timeout: ' + j['status'])

    def test_failed_montage_succeeds_after_resume_with_same_media(self):
        j = make_job(); j['config']['scene_count'] = 2; s.store_script(j, script(2)); j['stage'] = 'edit'; scene_images(j)
        folder = s.job_dir(j)
        make_clip(folder / 'clip0.mp4'); j['scenes'][0]['clip'] = 'clip0.mp4'; j['scenes'][1]['clip'] = 'clip1.mp4'
        j['status'] = 'running'; s.schedule(j); self.wait(j, ('attention',))
        self.assertEqual(j['stage'], 'edit'); self.assertIn('Montage', j['events'][-1]['text'])
        make_clip(folder / 'clip1.mp4', audio=False)
        j['status'] = 'running'; s.schedule(j); self.wait(j, ('done',))
        self.assertEqual(j['stage'], 'done'); self.assertEqual(j['final'], s.asset_url(j, 'final.mp4'))
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height', '-of', 'json', str(folder / 'final.mp4')], capture_output=True, text=True, check=True)
        meta = json.loads(probe.stdout); video = next(x for x in meta['streams'] if x['codec_type'] == 'video')
        self.assertEqual((video['width'], video['height']), (1080, 1920), 'best resolution for TikTok')
        self.assertAlmostEqual(float(meta['format']['duration']), 16, delta=0.5)
        self.assertTrue(any(x['codec_type'] == 'audio' for x in meta['streams']))
        self.assertTrue((folder / 'cover.jpg').is_file()); self.assertEqual(s.STATE['tasks'], [])


if __name__ == '__main__':
    unittest.main()
