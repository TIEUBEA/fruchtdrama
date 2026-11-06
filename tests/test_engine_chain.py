"""0.1.97: bascule de moteur par clip, Flow puis Grok seulement (owner 06/11/2026 au soir : « Pour chaque scène : un
premier essai sur Flow. Si le clip n'est pas généré, bascule DIRECTEMENT sur Grok. Si après un essai Flow et un essai
Grok il y a un problème, rapporte directement l'erreur dans le studio et CONTINUE. »). Clip mis de côté sans bloquer
les autres, envoi Flow incertain passé à Grok, moteur gardé par clip pour le montage, plans Flow de 10 s."""
import datetime as dt, importlib.util, os, pathlib, shutil, subprocess, sys, tempfile, time, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_engine_chain', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import engine_chain, engines


def fresh(sites=('chatgpt', 'grok')):
    state = s.fresh(); at = dt.datetime.now(dt.timezone.utc).isoformat()
    state['readiness'] = {'sites': {n: {'state': 'ready', 'reason': '', 'at': at} for n in sites}, 'pending': []}
    return state


def clip_job(balance=100, engine='flow', n=4, flow_seconds=10):
    from PIL import Image
    j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'brief': 'b', 'characters': [], 'scenes': [], 'candidates': [],
         'flow_profile': 'flow', 'selected': {'title': 'Référence', 'url': 'https://www.tiktok.com/@a/video/1'},
         'config': {'scene_count': n, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)', 'video_engine': engine, 'flow_seconds': flow_seconds}}
    s.STATE['jobs'].append(j)
    s.store_script(j, {'title': 'Omas Reise', 'cover_title': 'WER?', 'description': 'd',
                       'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'Orange', 'voice': 'v', 'image_prompt': 'p'}],
                       'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'The orange opens the door.',
                                   'dialogue': [{'speaker': 'orange', 'text': 'Hallo Welt'}]} for _ in range(n)]})
    j['stage'] = 'clips'
    for i, scene in enumerate(j['scenes']):
        Image.new('RGB', (32, 64), (i * 50, 9, 9)).save(s.job_dir(j) / f'scene{i}.png'); scene['image'] = f'scene{i}.png'
    s.STATE['profiles'].append({'id': 'flow', 'label': 'Flow', 'balance': balance})
    return j


def queued(j):
    return [t for t in s.STATE['tasks'] if t['job'] == j['id'] and t['status'] == 'queued']


def engine_of(t):
    return 'flow' if t['kind'] == 'flow_video' else t['payload']['engine']


def fail(t, result):
    t['status'] = 'claimed'
    if t['kind'] == 'flow_video':
        # What the bridge does when the clip is claimed: a prudent local reservation.
        p = s.profile_by(t['profile']); p['balance'] -= t['payload']['cost']
        t['reservation'] = {'profile': p['id'], 'amount': t['payload']['cost'], 'refunded': False}
    s.accept_task_result(t, result)


def deliver(j, t):
    name = t['slot'].replace(':', '_') + '_' + s.uid() + '.mp4'; (s.job_dir(j) / name).write_bytes(b'clip')
    t['status'] = 'claimed'; s.accept_task_result(t, {'ok': True, 'file': name})
    return name


NOTHING_SENT = {'ok': False, 'generation_submitted': False, 'error': 'Flow : coût affiché différent du budget prévu. Aucun envoi effectué.'}


class ChainUnitTests(unittest.TestCase):
    def test_order_and_validation(self):
        self.assertEqual(engine_chain.order({}), ['flow', 'grok'])
        self.assertEqual(engine_chain.order({'engine_chain': ['arena', 'vidogrid', 'flow']}), ['flow', 'grok'], 'removed engines ignored, Grok always kept')
        self.assertEqual(engine_chain.order({'engine_chain': ['grok', 'flow']}, {'video_engine': 'flow'}), ['grok', 'flow'], 'Flow is the default, not a choice')
        self.assertEqual(engine_chain.order({}, {'video_engine': 'grok'}), ['grok', 'flow'], 'the episode engine first')
        self.assertEqual(engine_chain.order({}, {'video_engine': 'arena'}), ['flow', 'grok'], 'an old Arena episode: Flow then Grok')
        self.assertEqual(engine_chain.validate(['grok', 'grok', 'flow']), ['grok', 'flow'])
        for bad in ([], ['sora'], ['arena'], ['vidogrid'], 'flow'):
            with self.assertRaises(ValueError):
                engine_chain.validate(bad)

    def test_one_try_each_then_none(self):
        scene = {}; chain = ['flow', 'grok']; ready = lambda e: True
        self.assertEqual(engine_chain.pick(scene, chain, ready), 'flow')
        engine_chain.record(scene, 'flow', 'refusal', 'Flow : refusé. Diagnostic {x}', 'now')
        self.assertEqual(scene['engine_tries'][0]['reason'], 'refusé')
        self.assertEqual(engine_chain.advance(scene, chain, ready), 'grok')
        engine_chain.record(scene, 'grok', 'timeout', 'Grok Imagine : vidéo non détectée après 4 minutes.', 'now')
        self.assertIsNone(engine_chain.advance(scene, chain, ready), 'no softened round, no third try')
        self.assertEqual(engine_chain.summary(scene), 'Flow (refusé) puis Grok (vidéo non détectée après 4 minutes)')
        self.assertEqual(engine_chain.failure(2, scene), 'Clip 3 : Flow (refusé) puis Grok (vidéo non détectée après 4 minutes) — clip à refaire. Les autres clips continuent.')
        self.assertEqual(engine_chain.line(2, 'flow', 'refusal', 'Contenu non conforme.', 'grok'), 'Clip 3 : Flow a refusé (Contenu non conforme) → essai sur Grok.')
        self.assertEqual(engine_chain.line(0, 'flow', 'uncertain', '', 'grok'), 'Clip 1 : Flow n’a pas confirmé l’envoi → essai sur Grok.')
        self.assertFalse(hasattr(engine_chain, 'soften'), 'no softened prompt any more')
        engine_chain.reset(scene); self.assertNotIn('engine_tries', scene)

    def test_engine_not_ready_is_skipped(self):
        self.assertEqual(engine_chain.pick({}, ['flow', 'grok'], lambda e: e == 'grok'), 'grok')
        self.assertIsNone(engine_chain.pick({'engine_tries': [{'engine': 'flow'}]}, ['flow', 'grok'], lambda e: e == 'flow'))

    def test_montage_length_follows_each_clip_engine(self):
        new, old = {'config': {'video_engine': 'flow', 'flow_seconds': 10}}, {'config': {'video_engine': 'flow'}}
        self.assertEqual(engines.clip_length(new, 9.7, {'engine': 'flow'}), 10.0, 'Flow: 10 s plans since 0.1.97')
        self.assertEqual(engines.clip_length(old, 7.6, {'engine': 'flow'}), 8.0, 'an existing episode keeps its 8 s')
        self.assertEqual(engines.clip_length(new, 6.04, {'engine': 'grok'}), 6.04)
        self.assertEqual(engines.clip_length(new, 7.2, {'engine': 'arena'}), 7.2, 'a clip already made by Arena keeps its length')
        self.assertEqual(engines.clip_length(new, 7.2, {}), 10.0, 'older clips: the episode engine')
        self.assertEqual(engines.clip_range(new, {'engine': 'flow'}), (9.5, 10.5))
        self.assertEqual(engines.clip_range(old, {'engine': 'flow'}), (7.5, 8.5))
        self.assertEqual(engines.clip_range(new, {'engine': 'vidogrid'}), (5.5, 10.5))


class ChainScheduleTests(unittest.TestCase):
    def setUp(self):
        s.STATE = fresh()

    def test_flow_then_grok_then_reported_and_the_others_go_on(self):
        j = clip_job(); s.schedule(j)
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:0', 'flow'))
        self.assertIn('10 seconds', t['payload']['prompt']); self.assertEqual(t['payload']['seconds'], 10)
        fail(t, NOTHING_SENT)
        self.assertEqual(s.STATE['profiles'][0]['balance'], 100, 'nothing sent: reservation given back')
        self.assertEqual(j['status'], 'running'); self.assertFalse([a for a in j.get('alerts', []) if a['level'] == 'action'], 'no « Action requise »')
        self.assertIn('Clip 1 : Flow a échoué (coût affiché différent du budget prévu) → essai sur Grok.', [e['text'] for e in j['events']])
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:0', 'grok'), 'Grok at once, no validation asked')
        self.assertIn('10 seconds', t['payload']['prompt']); self.assertNotIn('All-audiences', t['payload']['prompt'])
        fail(t, {'ok': False, 'error_kind': 'timeout', 'generation_submitted': True, 'error': 'Grok Imagine : vidéo non détectée après 4 minutes.'})
        self.assertEqual(s.held_clips(j), {0}); self.assertEqual(j['stage'], 'clips', 'no board redrawn')
        alert = j['alerts'][-1]; self.assertEqual(alert['level'], 'action')
        self.assertEqual(alert['text'], 'Clip 1 : Flow (coût affiché différent du budget prévu) puis Grok (vidéo non détectée après 4 minutes) — clip à refaire. Les autres clips continuent.')
        self.assertNotIn('command', alert, 'no « Utiliser Grok » button')
        # The other clips go on.
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:1', 'flow')); self.assertEqual(j['status'], 'running')
        for k in (1, 2, 3):
            deliver(j, next(x for x in queued(j) if x['slot'] == f'clip:{k}'))
        # 0.1.102: no stop at the end; the board, slowly zoomed, stands in for the clip and the episode goes on.
        self.assertNotEqual(j['status'], 'attention'); self.assertEqual(queued(j), [])
        self.assertTrue(j['scenes'][0]['still']); self.assertTrue((s.job_dir(j) / j['scenes'][0]['clip']).is_file())
        self.assertIn('planche animée', j['alerts'][-1]['text']); self.assertEqual(j['alerts'][-1]['level'], 'auto')
        self.assertEqual(s.failed_clips(j), []); self.assertNotEqual(j['stage'], 'clips')
        # « Refaire » with the owner's instruction: Flow first again.
        j['status'] = 'done'; s.BUSY.discard(j['id'])  # the (test) montage ends; « Refaire » then works as before
        s.redo(j, 'clip:0', 'sans bagarre')
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:0', 'flow'))
        self.assertIn('sans bagarre', t['payload']['prompt'])
        self.assertFalse([a for a in j['alerts'] if 'clip(s) en échec' in a['text'] or a['text'].startswith('Clip 1 : ')])

    def test_tab_cut_by_extension_reload_is_not_a_try(self):
        # 0.1.102 (06/11/2026 23:13): clips « failed » while the extension reloaded itself.
        s.STATE = fresh(); j = clip_job(); s.schedule(j)
        fail(queued(j)[0], NOTHING_SENT)
        t = queued(j)[0]; self.assertEqual(engine_of(t), 'grok')
        fail(t, {'ok': False, 'error': 'Could not establish connection. Receiving end does not exist.'})
        self.assertEqual(engine_chain.tried(j['scenes'][0]), ['flow'], 'not counted')
        s.schedule(j); self.assertTrue(any(x['slot'] == 'clip:0' and engine_of(x) == 'grok' for x in queued(j)), 'Grok again')
        self.assertFalse(s.held_clips(j))

    def test_clip_set_aside_is_redone_while_the_others_run(self):
        s.STATE = fresh(sites=('chatgpt',)); j = clip_job(); s.schedule(j)
        fail(queued(j)[0], NOTHING_SENT)
        self.assertEqual(s.held_clips(j), {0}, 'Grok not ready: set aside at once')
        self.assertIn('Grok (aucun compte Grok prêt)', j['alerts'][-1]['text'])
        self.assertEqual([t['slot'] for t in queued(j)], ['clip:1'])
        s.redo(j, 'clip:0', 'autre angle', start=False)
        self.assertEqual(s.held_clips(j), set()); self.assertEqual(j['scenes'][0].get('engine_tries'), None)

    def test_received_clip_keeps_its_engine_and_the_next_clip_starts_from_flow(self):
        j = clip_job(); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'generation_submitted': False, 'error': 'Flow : page indisponible.'})
        deliver(j, queued(j)[0])
        self.assertEqual(j['scenes'][0]['engine'], 'grok'); self.assertNotIn('engine_tries', j['scenes'][0])
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:1', 'flow'))
        deliver(j, t); self.assertEqual(j['scenes'][1]['engine'], 'flow')

    def test_flow_without_credits_goes_to_grok_without_a_try(self):
        j = clip_job(balance=0); s.schedule(j)
        t = queued(j)[0]; self.assertEqual(engine_of(t), 'grok'); self.assertNotEqual(j['status'], 'waiting_credit')
        self.assertNotIn('engine_tries', j['scenes'][0])

    def test_nothing_ready_keeps_the_old_wait_for_credits(self):
        s.STATE = fresh(sites=('chatgpt',))
        j = clip_job(balance=0); s.schedule(j)
        self.assertEqual(j['status'], 'waiting_credit'); self.assertEqual(queued(j), [])

    def test_uncertain_flow_submission_goes_to_grok_and_never_stops_the_episode(self):
        """Real case 06/11/2026: « Envoi Flow incertain pour la scène 1, 3, 4, 7, 16 », episode in Action requise."""
        j = clip_job(); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'error': 'Génération trop longue ou média non détecté.'})
        self.assertEqual(s.STATE['profiles'][0]['balance'], 88, 'maybe charged: reservation kept')
        self.assertEqual(j['status'], 'running'); self.assertEqual(s.held_clips(j), set())
        self.assertFalse([a for a in j.get('alerts', []) if a['level'] == 'action'])
        self.assertIn('incertain', j['alerts'][-1]['text']); self.assertEqual(j['alerts'][-1]['level'], 'auto')
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:0', 'grok'))
        self.assertTrue(s.flow_in_doubt(j, 0))
        # Grok fails too: set aside, the doubt stays; « Refaire » never sends this clip to Flow again.
        fail(t, {'ok': False, 'error_kind': 'refusal', 'generation_submitted': True, 'error': 'Grok Imagine : contenu modéré.'})
        self.assertEqual(s.held_clips(j), {0}); self.assertIn('Flow (', j['alerts'][-1]['text']); self.assertIn('puis Grok (contenu modéré)', j['alerts'][-1]['text'])
        flows = [x for x in queued(j) if x['slot'] == 'clip:1']; self.assertEqual(len(flows), 1, 'the next clip goes on')
        flows[0]['status'] = 'cancelled'
        s.redo(j, 'clip:0', 'plus calme')
        self.assertEqual(engine_of(next(x for x in queued(j) if x['slot'] == 'clip:0')), 'grok', 'never sent to Flow again while in doubt')

    def test_resume_never_refused_for_an_uncertain_clip(self):
        j = clip_job(n=1); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'error': 'Génération trop longue ou média non détecté.'})
        self.assertEqual(engine_of(queued(j)[0]), 'grok'); self.assertEqual(j['status'], 'running')

    def test_flow_clip_found_later_replaces_the_grok_clip(self):
        j = clip_job(n=2); s.schedule(j)
        flow = queued(j)[0]; flow['client'] = 'c'
        fail(flow, {'ok': False, 'error': 'Génération trop longue ou média non détecté.'})
        grok_file = deliver(j, next(x for x in queued(j) if x['slot'] == 'clip:0'))
        self.assertEqual(j['scenes'][0]['engine'], 'grok'); self.assertEqual(j['status'], 'running')
        self.assertTrue(s.recoverable_flow(j, flow), 'the Flow clip may still be fetched while the episode goes on')
        collect = {'id': s.uid(), 'job': j['id'], 'kind': 'flow_collect', 'profile': 'flow', 'slot': 'clip:0', 'status': 'claimed', 'client': 'c', 'payload': flow['payload'], 'recovers': flow['id']}
        s.STATE['tasks'].append(collect)
        self.assertFalse(s.recoverable_flow(j, flow), 'never twice at once')
        name = 'flow_found.mp4'; (s.job_dir(j) / name).write_bytes(b'clip')
        s.accept_task_result(collect, {'ok': True, 'file': name})
        self.assertEqual(j['scenes'][0]['clip'], name); self.assertEqual(j['scenes'][0]['engine'], 'flow')
        self.assertIn(grok_file, [h['file'] for h in j['redo_history']], 'the Grok clip stays in the earlier versions')
        self.assertTrue(flow.get('acknowledged')); self.assertFalse(s.recoverable_flow(j, flow))

    def test_failed_recovery_stops_nothing(self):
        j = clip_job(n=2); s.schedule(j)
        flow = queued(j)[0]
        fail(flow, {'ok': False, 'error': 'Génération trop longue ou média non détecté.'})
        collect = {'id': s.uid(), 'job': j['id'], 'kind': 'flow_collect', 'profile': 'flow', 'slot': 'clip:0', 'status': 'claimed', 'payload': flow['payload'], 'recovers': flow['id']}
        s.STATE['tasks'].append(collect)
        s.accept_task_result(collect, {'ok': False, 'error': 'Téléchargement impossible.'})
        self.assertEqual(j['status'], 'running'); self.assertEqual(flow['recover_tries'], 1)

    def test_flow_failure_message_is_not_uncertain(self):
        """dev 0.1.92.1: Flow shows why a generation failed (flow_failed): not charged, Grok at once."""
        j = clip_job(); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'error_kind': 'refusal', 'generation_submitted': True, 'flow_failed': True, 'error': 'Flow a refusé ce clip : Impossible de générer cette vidéo.'})
        self.assertEqual(s.uncertain_clip_tasks(j), []); self.assertEqual(s.STATE['profiles'][0]['balance'], 100)
        self.assertEqual(engine_of(queued(j)[0]), 'grok')
        self.assertIn('Clip 1 : Flow a refusé (Impossible de générer cette vidéo) → essai sur Grok.', [e['text'] for e in j['events']])

    def test_third_party_refusal_no_longer_redraws_the_board(self):
        j = clip_job(); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'error_kind': 'refusal', 'generation_submitted': True, 'flow_failed': True,
                            'error': 'Flow a refusé ce clip : en raison des intérêts des fournisseurs de contenu tiers.'})
        fail(queued(j)[0], {'ok': False, 'error_kind': 'refusal', 'generation_submitted': True, 'error': 'Grok Imagine : contenu modéré.'})
        self.assertEqual(j['stage'], 'clips'); self.assertTrue(j['scenes'][0].get('image')); self.assertEqual(s.held_clips(j), {0})

    def test_grok_login_with_nothing_else_asks_the_owner(self):
        """A sign-in only the owner can do, with Flow unable to pay: « Action requise » with the reason, as before."""
        j = clip_job(balance=0); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'error_kind': 'login', 'generation_submitted': False, 'error': 'Grok Imagine : connexion requise.'})
        self.assertEqual(j['status'], 'attention'); self.assertIn('Connexion requise', j['events'][-1]['text'])

    def test_flow_login_goes_to_grok(self):
        j = clip_job(); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'error_kind': 'login', 'generation_submitted': False, 'error': 'Flow : connexion requise.'})
        self.assertEqual(engine_of(queued(j)[0]), 'grok'); self.assertEqual(j['status'], 'running')

    def test_quota_walls_the_grok_account_and_reports(self):
        s.engine_accounts.add(s.STATE, 'grok', 'A', 'compte-a@example.com')
        j = clip_job(balance=0); s.schedule(j)
        t = queued(j)[0]; self.assertEqual(t['payload']['account']['email'], 'compte-a@example.com')
        fail(t, {'ok': False, 'error_kind': 'quota', 'retry_after': 3600, 'generation_submitted': True, 'error': 'Grok Imagine : limite du compte atteinte.'})
        self.assertTrue(s.engine_accounts.walled(s.engine_accounts.accounts(s.STATE, 'grok')[0], time.time()))
        self.assertEqual(s.held_clips(j), {0}, 'never kept waiting: reported, set aside')

    def test_one_grok_account_at_its_limit_switches_account_for_a_grok_episode(self):
        a = s.engine_accounts.add(s.STATE, 'grok', 'A', 'compte-a@example.com'); s.engine_accounts.add(s.STATE, 'grok', 'B', 'compte-b@example.com')
        j = clip_job(balance=0, engine='grok'); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'error_kind': 'quota', 'retry_after': 3600, 'generation_submitted': True, 'error': 'limite'})
        self.assertEqual(s.held_clips(j), set()); self.assertEqual(j['status'], 'waiting_account')

    def test_one_clip_at_a_time_on_grok(self):
        j = clip_job(balance=0)
        s.STATE['tasks'].append({'id': 'x', 'job': 'other', 'kind': 'engine_video', 'slot': 'clip:0', 'status': 'claimed', 'payload': {'engine': 'grok'}})
        self.assertTrue(s.engine_busy('grok'))
        self.assertFalse(s.schedule_engine_clip(j, 1, 'grok', early=True, parallel=True))

    def test_grok_needs_no_validation(self):
        j = clip_job()
        self.assertTrue(s.engine_ready(j, 'grok'), 'a ready Grok account takes the clip, no « Utiliser Grok »')
        self.assertFalse(hasattr(s, 'ask_grok'))
        self.assertFalse(s.engine_ready(j, 'arena')); self.assertFalse(s.engine_ready(j, 'vidogrid'))

    def test_old_arena_accounts_are_ignored(self):
        s.STATE['engine_accounts'] = [{'id': 'a', 'engine': 'arena', 'label': 'A', 'email': 'vieux@example.com'},
                                      {'id': 'v', 'engine': 'vidogrid', 'label': 'V', 'email': 'vieux@example.com'}]
        j = clip_job(); s.schedule(j)
        self.assertEqual(engine_of(queued(j)[0]), 'flow')
        s.public_state()  # no crash with old rows

    def test_engine_order_setting(self):
        s.STATE['settings']['engine_chain'] = engine_chain.validate(['grok', 'flow'])
        j = clip_job(); s.schedule(j)
        self.assertEqual(engine_of(queued(j)[0]), 'grok')


class StallTests(unittest.TestCase):
    """« Dès qu'une étape prend plus de temps qu'elle est censée prendre, reporte directement l'erreur au niveau du studio »."""
    def setUp(self):
        s.STATE = fresh()

    def old(self, minutes):
        return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes)).isoformat()

    def test_running_with_nothing_in_flight_is_said_blocked(self):
        j = {'id': s.uid(), 'status': 'running', 'stage': 'script', 'config': {}, 'events': [{'at': self.old(5), 'text': 'x'}]}
        s.STATE['jobs'].append(j)
        info = s.stall_info(j)
        self.assertIn('Rien ne tourne pour le scénario depuis 5 min', info['reason']); self.assertTrue(info['retry']); self.assertEqual(info['minutes'], 5)
        j['events'][-1]['at'] = self.old(1); self.assertIsNone(s.stall_info(j))

    def test_long_scenario_is_said_blocked_with_its_step(self):
        s.STATE['clients']['c'] = {'id': 'c', 'seen': s.now()}
        j = {'id': s.uid(), 'status': 'running', 'stage': 'script', 'config': {}, 'events': [{'at': self.old(11), 'text': 'x'}]}
        s.STATE['jobs'].append(j)
        s.STATE['tasks'].append({'id': 't', 'job': j['id'], 'kind': 'chat_text', 'slot': 'script', 'status': 'claimed', 'client': 'c', 'claimed': self.old(11), 'payload': {'provider': 'chatgpt'}})
        info = s.stall_info(j)
        self.assertEqual(info['step'], 'le scénario'); self.assertGreaterEqual(info['minutes'], 10); self.assertEqual(info['task'], 't')

    def test_long_engine_clip_is_said_blocked_sooner(self):
        s.STATE['clients']['c'] = {'id': 'c', 'seen': s.now()}
        j = {'id': s.uid(), 'status': 'running', 'stage': 'clips', 'config': {}, 'events': [{'at': self.old(9), 'text': 'x'}]}
        s.STATE['jobs'].append(j)
        s.STATE['tasks'].append({'id': 't', 'job': j['id'], 'kind': 'engine_video', 'slot': 'clip:2', 'status': 'claimed', 'client': 'c', 'claimed': self.old(9), 'payload': {'engine': 'grok'}})
        self.assertEqual(s.stall_info(j)['step'], 'le clip 3')

    def test_montage_too_long_is_said_blocked(self):
        j = {'id': s.uid(), 'status': 'rendering', 'stage': 'edit', 'config': {}, 'events': [{'at': self.old(25), 'text': 'Montage local démarré.'}]}
        s.STATE['jobs'].append(j)
        info = s.stall_info(j); self.assertEqual(info['step'], 'le montage'); self.assertTrue(info['retry']); self.assertFalse(info['paid'])
        j['events'][-1]['at'] = self.old(2); self.assertIsNone(s.stall_info(j))

    def test_paused_is_never_a_stall(self):
        j = {'id': s.uid(), 'status': 'paused', 'stage': 'script', 'config': {}, 'events': [{'at': self.old(60), 'text': 'x'}]}
        self.assertIsNone(s.stall_info(j))


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg requis')
class MixedMontageTests(unittest.TestCase):
    def test_flow_grok_and_older_clips_keep_their_length(self):
        s.STATE = fresh(); j = clip_job(); folder = s.job_dir(j)
        for i, (engine, seconds, size) in enumerate((('flow', 10, '72x128'), ('grok', 6, '48x84'), ('arena', 8, '128x72'), ('flow', 10, '72x128'))):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=red:s={size}:r=10', '-f', 'lavfi', '-i', 'sine=f=440:r=16000',
                            '-t', str(seconds), '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', str(folder / f'clip{i}.mp4')], check=True)
            j['scenes'][i].update(clip=f'clip{i}.mp4', engine=engine)
        j.update(stage='edit', status='rendering')
        s.render_job(j['id'])
        self.assertEqual(j['status'], 'done', j['events'][-1]['text'])
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=width,height', '-of', 'csv=p=0', str(folder / 'final.mp4')], capture_output=True, text=True).stdout
        self.assertIn('1080,1920', out, 'every clip reframed to 1080 x 1920, even a landscape one')
        duration = float([x for x in out.split() if '.' in x and ',' not in x][-1])
        self.assertAlmostEqual(duration, 34, delta=0.7, msg='10 + 6 + 8 + 10 s')
        ass = (folder / 'subtitles.ass').read_text('utf-8-sig')
        self.assertIn('Dialogue: 0,0:00:24.', ass, 'last scene captions start after 10 + 6 + 8 s')


class ThirdPartyRedraw(unittest.TestCase):
    """redraw_refused_board is kept for a later decision, but no longer called (0.1.97)."""
    def test_board_refused_as_third_party_content_is_drawn_again(self):
        j = {'id': 'tp', 'events': [], 'stage': 'clips', 'status': 'running', 'config': {}, 'scenes': [
            {'image': 'board.png', 'engine_tries': [{'engine': 'flow', 'kind': 'refusal', 'reason': 'Impossible de générer la vidéo demandée pour le moment en raison des intérêts des fournisseurs de contenu tiers.'}]}]}
        self.assertTrue(s.redraw_refused_board(j, 0))
        self.assertNotIn('image', j['scenes'][0]); self.assertEqual(j['stage'], 'images')
        self.assertIn('third-party', j['corrections']['image:0'])
        self.assertNotIn('engine_tries', j['scenes'][0])
        j['scenes'][0]['image'] = 'b2.png'; j['scenes'][0]['engine_tries'] = [{'reason': 'contenu tiers'}]
        self.assertTrue(s.redraw_refused_board(j, 0))
        j['scenes'][0]['image'] = 'b3.png'; j['scenes'][0]['engine_tries'] = [{'reason': 'contenu tiers'}]
        self.assertFalse(s.redraw_refused_board(j, 0), 'twice at most')

    def test_other_refusals_do_not_redraw(self):
        j = {'id': 'tq', 'events': [], 'config': {}, 'scenes': [{'image': 'b.png', 'engine_tries': [{'reason': 'Page vide'}]}]}
        self.assertFalse(s.redraw_refused_board(j, 0))


class TenSecondPlans(unittest.TestCase):
    """Owner 06/11/2026: TikTok Creator Rewards pays videos of at least 1 minute; 10 s clips save resources."""
    def setUp(self):
        s.STATE = fresh()

    def test_one_minute_is_seven_plans_of_ten_seconds(self):
        import montage
        self.assertEqual(montage.scenes_for(60, engines.ENGINES['flow']['seconds']), 7)
        self.assertEqual(engines.words_in(10), 30)

    def test_viral_remake_is_condensed_into_one_minute(self):
        j = {'id': s.uid(), 'brief': '', 'events': [], 'selected': {'source': 'owner_link', 'url': 'https://www.tiktok.com/@a/video/1'},
             'config': {'scene_count': 7, 'language': 'Français (fr-FR)', 'recreate': 'identical', 'flow_seconds': 10, 'clip_seconds': 10, 'video_engine': 'flow'}}
        prompt = s.script_prompt(j)
        self.assertIn('Exactement 7 scènes de 10 secondes', prompt)
        # 0.1.104 (owner 07/11/2026): a remake keeps the original's length and every line, reworded, 2-3 shots per scene.
        self.assertIn('rien n’est condensé', prompt); self.assertIn('LÉGÈREMENT TRANSPOSÉE', prompt); self.assertIn('2 ou 3 PLANS', prompt)
        j['config']['recreate'] = 'inspired'
        self.assertIn('7 plans de 10 secondes (environ 70 s', s.script_prompt(j))
        self.assertIn('Au plus 30 mots parlés par scène', prompt)

    def test_scenario_of_thirty_words_is_accepted_for_ten_seconds(self):
        j = clip_job(n=1)
        j['stage'] = 'script'; j['scenes'] = []
        words = ' '.join(['Wort'] * 30)
        s.store_script(j, {'title': 'T', 'cover_title': 'C', 'description': 'd',
                           'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'Orange', 'voice': 'v', 'image_prompt': 'p'}],
                           'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'v', 'dialogue': [{'speaker': 'orange', 'text': words}]}]})
        self.assertEqual(j['stage'], 'characters')


if __name__ == '__main__':
    unittest.main()
