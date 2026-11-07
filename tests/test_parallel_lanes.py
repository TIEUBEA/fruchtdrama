"""0.1.89: clips in parallel with the boards (Atelier: « les clips partent chez Grok pendant que ChatGPT dessine les planches »).
Two lanes per episode, chat and video, one active task each; a clip leaves only for a drawn and validated board."""
import importlib.util, json, os, pathlib, sys, tempfile, threading, unittest, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_lanes', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


def job(n=3, drawn=0, engine='grok', **config):
    """Episode at the boards stage: n scenes, the first `drawn` boards already received."""
    from PIL import Image
    j = {'id': s.uid(), 'stage': 'images', 'status': 'running', 'events': [], 'brief': 'b', 'candidates': [], 'flow_profile': 'flow' if engine == 'flow' else None,
         'title': 'T', 'quality_version': 1, 'script': {'title': 'T', 'cover_title': 'C', 'description': 'd'},
         'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'a', 'voice': 'v', 'image_prompt': 'p', 'file': 'ref.png'}],
         'scenes': [{'characters': ['orange'], 'meaning': f'm{i}', 'image_prompt': 'i', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': 'Hallo'}]} for i in range(n)],
         'config': {'scene_count': n, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)', 'video_engine': engine, 'clip_seconds': 6, 'controls': 'none', **config}}
    s.STATE['jobs'].append(j); folder = s.job_dir(j)
    Image.new('RGB', (64, 112), 'orange').save(folder / 'ref.png')
    for i in range(drawn):
        board(j, i)
    return j


def board(j, i):
    from PIL import Image
    name = f'board{i}_{s.uid()}.png'
    Image.new('RGB', (64, 112), (40 * i + 20, 90, 150)).save(s.job_dir(j) / name)
    j['scenes'][i]['image'] = name
    return name


def active(j, lane=None):
    return [t for t in s.STATE['tasks'] if t['job'] == j['id'] and t['status'] in ('queued', 'claimed') and (lane is None or s.lane_of(t) == lane)]


def deliver(t):
    """The extension returns the board or clip of task t."""
    j = s.job_by(t['job'])
    if t['slot'].startswith('image:'):
        from PIL import Image
        i = int(t['slot'].split(':')[1]); name = f'drawn{i}_{s.uid()}.png'
        Image.new('RGB', (64, 112), (20, 30 * i + 10, 200 - 20 * i)).save(s.job_dir(j) / name)
    else:
        name = t['slot'].replace(':', '_') + '_' + s.uid() + '.mp4'; (s.job_dir(j) / name).write_bytes(b'clip')
    t['status'] = 'claimed'; s.accept_task_result(t, {'ok': True, 'file': name})


class Lanes(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_clip_queued_while_next_board_is_drawn(self):
        j = job(); s.schedule(j)
        self.assertEqual([t['slot'] for t in active(j)], ['image:0'], 'no board yet: no clip')
        deliver(active(j)[0])
        chat, video = active(j, 'chat'), active(j, 'video')
        self.assertEqual([t['slot'] for t in chat], ['image:1'], 'the next board is drawn')
        self.assertEqual([(t['slot'], t['kind']) for t in video], [('clip:0', 'engine_video')], 'board 1 already animated meanwhile')
        self.assertEqual(j['stage'], 'images')
        self.assertIn(s.asset_url(j, s.flow_reference(j, j['scenes'][0]['image'])), video[0]['payload']['attachments'])

    def test_one_task_per_lane(self):
        j = job(n=4, drawn=3); s.schedule(j)
        for _ in range(3):
            s.schedule(j)
        self.assertEqual([t['slot'] for t in active(j, 'chat')], ['image:3'])
        self.assertEqual([t['slot'] for t in active(j, 'video')], ['clip:0'], 'one clip at a time, even with three boards ready')
        deliver(active(j, 'video')[0])
        self.assertEqual([t['slot'] for t in active(j, 'video')], ['clip:1'], 'next ready board animated at once')
        self.assertEqual([t['slot'] for t in active(j, 'chat')], ['image:3'], 'board in progress untouched')

    def test_clip_waits_for_a_board_not_yet_drawn(self):
        j = job(n=2); s.schedule(j); deliver(active(j)[0])
        deliver(active(j, 'video')[0])  # clip 1 done while board 2 is still drawn
        self.assertEqual(active(j, 'video'), [], 'board 2 missing: no clip 2')
        deliver(active(j, 'chat')[0])
        self.assertEqual([t['slot'] for t in active(j, 'video')], ['clip:1'])
        self.assertEqual(j['stage'], 'clips', 'every board drawn: clips stage, waiting for the clip in progress')
        deliver(active(j, 'video')[0])
        self.assertEqual(j['stage'], 'cover', 'all clips: quality (controls off) then the cover, as before')
        self.assertEqual([t['slot'] for t in active(j)], ['cover'])

    def test_never_a_clip_before_the_grouped_board_check(self):
        j = job(n=3, drawn=3, board_controls='redo'); s.schedule(j)
        self.assertEqual([t['slot'] for t in active(j)], ['board_review'], 'boards drawn but not validated: no clip')
        review = active(j)[0]
        text = json.dumps({'production_id': j['id'], 'generation_task_id': review['id'], 'board_review': {'boards': [
            {'index': 0, 'status': 'issue', 'detail': 'personnage en trop'}, {'index': 1, 'status': 'pass', 'detail': 'ok'}, {'index': 2, 'status': 'pass', 'detail': 'ok'}]}})
        review['status'] = 'claimed'; s.accept_task_result(review, {'ok': True, 'text': text})
        self.assertEqual([t['slot'] for t in active(j, 'chat')], ['image:0'], 'refused board redrawn')
        self.assertEqual([t['slot'] for t in active(j, 'video')], ['clip:1'], 'first validated board animated, never the refused one')
        deliver(active(j, 'video')[0])
        self.assertEqual([t['slot'] for t in active(j, 'video')], ['clip:2'])
        deliver(active(j, 'video')[0])
        self.assertEqual(active(j, 'video'), [], 'board 1 still being redrawn: its clip waits')
        self.assertFalse(j['scenes'][0].get('clip'))
        deliver(active(j, 'chat')[0])
        self.assertEqual([t['slot'] for t in active(j, 'video')], ['clip:0'], 'redrawn board animated after its redraw')
        self.assertEqual(j['stage'], 'clips')

    def test_report_level_validates_after_the_verdict_only(self):
        j = job(n=2, drawn=2, board_controls='report'); s.schedule(j)
        self.assertEqual(active(j, 'video'), [])

    def test_redone_board_never_animated_before_its_new_version(self):
        j = job(n=2, drawn=2); j['stage'] = 'clips'
        for i in range(2):
            j['scenes'][i]['clip'] = f'c{i}.mp4'; j['scenes'][i]['clip_from'] = j['scenes'][i]['image']
        s.redo(j, 'image:1', 'plus de lumière', include_clip=True)
        self.assertEqual(j['stage'], 'images')
        self.assertEqual([t['slot'] for t in active(j)], ['image:1'], 'old board gone: its clip does not leave')
        deliver(active(j)[0])
        clip = active(j, 'video')
        self.assertEqual([t['slot'] for t in clip], ['clip:1'])
        self.assertIn('plus de lumière', clip[0]['payload']['prompt'])
        self.assertEqual(j['stage'], 'clips')

    def test_dry_run_keeps_clips_after_the_boards(self):
        j = job(n=2, drawn=1, dry_run=True); s.schedule(j)
        self.assertEqual([t['slot'] for t in active(j)], ['image:1'])

    def test_switch_off(self):
        s.STATE['settings']['parallel_clips'] = False
        j = job(n=2, drawn=1); s.schedule(j)
        self.assertEqual([t['slot'] for t in active(j)], ['image:1'])

    def test_flow_without_credits_waits_for_the_clips_stage(self):
        s.STATE['profiles'].append({'id': 'flow', 'label': 'Flow', 'balance': 5})
        j = job(n=2, drawn=1, engine='flow'); s.schedule(j)
        self.assertEqual([t['slot'] for t in active(j)], ['image:1'])
        self.assertEqual(j['status'], 'running', 'boards go on: no credit wait during the boards')
        deliver(active(j)[0])
        self.assertEqual(j['stage'], 'clips'); self.assertEqual(j['status'], 'waiting_credit', 'the clips stage waits and says why')

    def test_flow_clip_ahead_with_credits(self):
        s.STATE['profiles'].append({'id': 'flow', 'label': 'Flow', 'balance': 40})
        j = job(n=2, drawn=1, engine='flow'); s.schedule(j)
        video = active(j, 'video')
        self.assertEqual([(t['slot'], t['kind'], t['profile']) for t in video], [('clip:0', 'flow_video', 'flow')])
        self.assertEqual(s.STATE['profiles'][0]['balance'], 40, 'credits reserved at the claim only')

    def test_uncertain_clip_blocks_clips_ahead_not_boards(self):
        s.STATE['profiles'].append({'id': 'flow', 'label': 'Flow', 'balance': 40})
        j = job(n=3, drawn=1, engine='flow')
        s.STATE['tasks'].append({'id': s.uid(), 'job': j['id'], 'kind': 'flow_video', 'slot': 'clip:0', 'status': 'failed', 'payload': {}, 'reservation': {'profile': 'flow', 'amount': 12, 'refunded': False}})
        s.schedule(j)
        self.assertEqual([t['slot'] for t in active(j)], ['image:1'], 'maybe-paid clip: nothing sent again on a guess')

    def test_engine_limit_during_boards_keeps_the_boards_going(self):
        j = job(n=3, drawn=1); s.schedule(j)
        clip = active(j, 'video')[0]; clip['status'] = 'claimed'
        s.accept_task_result(clip, {'ok': False, 'error_kind': 'quota', 'error': 'Limite atteinte'})
        # 0.1.97: the clip is reported (« clip à refaire »), the engine is remembered at its limit; the boards go on.
        self.assertEqual(j['status'], 'running'); self.assertEqual(s.held_clips(j), {0})
        self.assertEqual([t['slot'] for t in active(j)], ['image:1'])
        deliver(active(j)[0])
        self.assertEqual(active(j, 'video'), [], 'no clip ahead after the limit')
        deliver(active(j)[0])
        self.assertEqual(j['stage'], 'clips'); self.assertNotIn('early_clips_off', j)
        self.assertEqual(j['status'], 'waiting_quota', 'the clips stage waits for the renewal and says so')
        self.assertEqual(active(j), [])

    def test_failed_clip_error_kept_when_a_board_arrives(self):
        j = job(n=3, drawn=1); s.schedule(j)
        clip = active(j, 'video')[0]; clip['status'] = 'claimed'
        s.accept_task_result(clip, {'ok': False, 'error': 'Interface non reconnue'})
        self.assertEqual(j['status'], 'running', 'the boards go on')
        deliver(active(j, 'chat')[0])
        self.assertEqual(j['last_error']['task'], clip['id'], 'a board received does not erase the clip failure')

    def test_stall_names_the_silent_lane(self):
        import datetime as dt
        def iso(minutes):
            return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes)).isoformat()
        j = job(n=2, drawn=1); s.STATE['clients']['w'] = {'id': 'w', 'seen': iso(0), 'role': 'all'}; s.schedule(j)
        image, clip = active(j, 'chat')[0], active(j, 'video')[0]
        image.update(status='claimed', client='w', claimed=iso(30), progress_at=iso(25))
        clip.update(status='claimed', client='w', claimed=iso(3), progress_at=iso(0))
        j['events'].append({'at': iso(0), 'text': 'clip en cours'})
        info = s.stall_info(j)
        self.assertEqual(info['task'], image['id'], 'the clip news does not hide the silent board')
        self.assertFalse(info['paid'])


class LaneHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def setUp(self):
        s.STATE = s.fresh()
        pair = self.req('/api/bridge/pair', {'code': s.STATE['pair_code'], 'label': 'QA', 'role': 'all'})
        self.client = pair['client']; self.auth = {'Authorization': 'Bearer ' + pair['token']}

    def req(self, path, body=None):
        h = {'Origin': self.base, 'Content-Type': 'application/json', **self.auth} if hasattr(self, 'auth') else {'Origin': self.base, 'Content-Type': 'application/json'}
        request = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=h)
        with urllib.request.urlopen(request) as r:
            return json.load(r)

    def claim(self, lane=None):
        return self.req('/api/bridge/task?client=' + self.client + ('&lane=' + lane if lane else ''))

    def test_each_lane_claims_its_own_task(self):
        j = job(n=3, drawn=1)
        video = self.claim('video'); chat = self.claim('chat')
        self.assertEqual((video['slot'], video['kind']), ('clip:0', 'engine_video'))
        self.assertEqual((chat['slot'], chat['kind']), ('image:1', 'chat_image'))
        self.assertIsNone(self.claim('video'), 'one video task per episode')
        self.assertIsNone(self.claim('chat'), 'one chat task per episode')
        self.assertEqual(len(active(j)), 2)

    def test_without_lane_one_task_at_a_time_as_before(self):
        j = job(n=3, drawn=1)
        first = self.claim(); second = self.claim()
        self.assertEqual({first['slot'], second['slot']}, {'image:1', 'clip:0'}, 'an older extension still receives both, one after the other')
        self.assertIsNone(self.claim())

    def test_unknown_lane_refused(self):
        job(n=2, drawn=1)
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.claim('flow')
        self.assertEqual(e.exception.code, 400)

    def test_chat_lane_never_receives_a_clip(self):
        j = job(n=2, drawn=2)  # every board drawn: the episode moves to the clips stage
        chat = self.claim('chat')
        self.assertIsNone(chat); self.assertEqual(j['stage'], 'clips')
        self.assertEqual(self.claim('video')['slot'], 'clip:0')

    def test_flow_claim_without_credits_during_boards(self):
        s.STATE['profiles'].append({'id': 'flow', 'label': 'Flow', 'balance': 40})
        s.STATE['clients'][self.client]['flow_profile'] = 'flow'
        j = job(n=3, drawn=1, engine='flow'); s.schedule(j)
        s.STATE['profiles'][0]['balance'] = 6  # spent elsewhere after the clip was queued
        self.assertIsNone(self.claim('video'))
        self.assertEqual(j['status'], 'running', 'the boards are not stopped'); self.assertTrue(j['early_clips_off'])
        self.assertEqual(s.STATE['profiles'][0]['balance'], 6, 'nothing reserved')
        self.assertEqual(self.claim('chat')['slot'], 'image:1')
        self.assertIsNone(self.claim('video'), 'no clip ahead again')

    def test_retry_step_only_drops_the_silent_lane(self):
        import datetime as dt
        def iso(minutes):
            return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes)).isoformat()
        j = job(n=3, drawn=1)
        video = self.claim('video'); chat = self.claim('chat')
        live_chat = next(t for t in s.STATE['tasks'] if t['id'] == chat['id']); live_video = next(t for t in s.STATE['tasks'] if t['id'] == video['id'])
        live_chat.update(claimed=iso(30), progress_at=iso(25)); live_video.update(progress_at=iso(0))
        self.req('/api/job/' + j['id'], {'action': 'retry_step'})
        self.assertEqual(live_chat['status'], 'failed'); self.assertEqual(live_video['status'], 'claimed', 'the clip in progress keeps going')
        self.assertEqual([t['slot'] for t in active(j, 'chat')], ['image:1'], 'the board is asked again')


if __name__ == '__main__':
    unittest.main()


class ChatQuotaKeepsClips(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_clips_go_on_while_chatgpt_images_are_at_their_limit(self):
        j = job(drawn=2)
        j['status'] = 'waiting_quota'; j['quota_lane'] = 'chat'; j['wait_until'] = 9e12
        s.schedule(j)
        self.assertEqual([t['slot'] for t in active(j)], ['clip:0'], 'boards wait, the clip of board 1 leaves')
        deliver(active(j)[0])
        # The clip received re-runs the schedule: the boards ask ChatGPT again (its limit is checked in add_task).
        self.assertIn('clip:1', [t['slot'] for t in active(j)])

    def test_a_video_limit_does_not_send_clips(self):
        j = job(drawn=2)
        j['status'] = 'waiting_quota'; j['quota_lane'] = 'video'; j['wait_until'] = 9e12
        s.schedule(j)
        self.assertEqual(active(j), [])


class FailedEarlyClip(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_boards_go_on_when_an_early_clip_fails(self):
        j = job(n=3, drawn=1); s.schedule(j)
        clip = next(t for t in active(j) if t['slot'] == 'clip:0'); clip['status'] = 'claimed'
        s.accept_task_result(clip, {'ok': False, 'error': 'Génération trop longue ou média non détecté.'})
        self.assertEqual(j['status'], 'running')
        self.assertIn('image:1', [t['slot'] for t in active(j)], 'the boards go on')
        # 0.1.97: Grok tried, Flow cannot pay here: the clip is reported at once, nothing softened or asked.
        self.assertEqual(s.held_clips(j), {0})
        self.assertEqual(active(j, 'video'), [])
        self.assertEqual(j['alerts'][-1]['level'], 'action'); self.assertIn('Clip 1 : Grok', j['alerts'][-1]['text'])
        self.assertIn('clip à refaire', j['alerts'][-1]['text'])
        # The owner's instruction (« Refaire » on the clip) starts the engines again, even while the boards go on.
        s.redo(j, 'clip:0', 'moins de bagarre', start=False)
        self.assertEqual(s.held_clips(j), set())


class TakeOver(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_reloaded_window_takes_over_when_the_old_one_is_gone(self):
        import datetime as dt
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).isoformat()
        s.STATE['clients'] = {'a': {'id': 'a', 'auto': True, 'role': 'all', 'seen': old},
                              'b': {'id': 'b', 'auto': True, 'role': 'all', 'seen': s.now(), 'disabled': True}}
        s.STATE['profiles'] = [{'id': 'p', 'flow_client': 'a'}]
        self.assertTrue(s.take_over(s.STATE['clients']['b']))
        self.assertFalse(s.STATE['clients']['b']['disabled']); self.assertTrue(s.STATE['clients']['a']['disabled'])
        self.assertEqual(s.STATE['profiles'][0]['flow_client'], 'b')

    def test_no_take_over_while_the_old_one_is_online(self):
        s.STATE['clients'] = {'a': {'id': 'a', 'auto': True, 'role': 'all', 'seen': s.now()},
                              'b': {'id': 'b', 'auto': True, 'role': 'all', 'seen': s.now(), 'disabled': True}}
        self.assertFalse(s.take_over(s.STATE['clients']['b']))
        self.assertTrue(s.STATE['clients']['b']['disabled'])
