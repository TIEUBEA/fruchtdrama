"""Moteur V09 (owner, 09/11/2026): faithful copy of the source (fruit-france MOTEUR §S), clip 1 on Grok (Flow when Grok
is not available), clips 2 to the end on Flow Omni 1.2 Flash in 10 s, Vidogrid once or twice when Flow refuses a scene,
Arena never used."""
import datetime as dt, importlib.util, os, pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_moteur_v09', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import engine_chain, engines, moteur_v09, source_video

TRANSCRIPT = '\n'.join(['[00:00.4] Mais c’est quoi ce délire ?', '[00:04.0] Quelqu’un veut nous détruire ?',
                        '[00:12.5] Tu as fouillé sous mon lit ?', '[00:27.0] Je vais tout dire à ta femme.'])


def state(sites=('chatgpt', 'grok', 'vidogrid')):
    st = s.fresh(); at = dt.datetime.now(dt.timezone.utc).isoformat()
    st['readiness'] = {'sites': {n: {'state': 'ready', 'reason': '', 'at': at} for n in sites}, 'pending': []}
    st['settings'].update(clip_routing=engine_chain.V09, parallel_clips=False)
    return st


def clip_job(n=3, identical=True):
    from PIL import Image
    j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'brief': '', 'characters': [], 'scenes': [], 'candidates': [],
         'flow_profile': 'flow', 'selected': {'title': 'Vidéo', 'url': 'https://www.tiktok.com/@a/video/1', 'source': 'owner_link'},
         'config': {'scene_count': n, 'provider': 'chatgpt', 'flow_cost': 30, 'flow_model': engines.OMNI_12, 'flow_resolution': '720p',
                    'language': 'Français (fr-FR)', 'video_engine': 'flow', 'clip_routing': engine_chain.V09,
                    'recreate': 'identical' if identical else 'inspired'}}
    s.STATE['jobs'].append(j)
    s.store_script(j, {'title': 'La bouteille', 'cover_title': 'QUI ?', 'description': 'd',
                       'characters': [{'id': 'prunelle', 'name': 'Prunelle', 'appearance': 'adult plum woman', 'voice': 'soft', 'image_prompt': 'p'},
                                      {'id': 'goyo', 'name': 'Goyo', 'appearance': 'adult guava man', 'voice': 'deep', 'image_prompt': 'p'}],
                       'scenes': [{'ref': f'00:{10 * k:02d}-00:{10 * k + 10:02d}', 'characters': ['prunelle', 'goyo'], 'meaning': 'm', 'image_prompt': 'i',
                                   'video_prompt': '10 seconds, vertical 9:16, ONE continuous shot, NO hard cuts: slow push-in. [00:00-00:05] PRUNELLE (plum head) pulls out the bottle: « Mais c’est quoi ce délire ? »',
                                   'dialogue': [{'speaker': 'prunelle', 'text': 'Mais c’est quoi ce délire ?'}]} for k in range(n)]})
    j['stage'] = 'clips'
    for i, scene in enumerate(j['scenes']):
        Image.new('RGB', (32, 64), (i * 50, 9, 9)).save(s.job_dir(j) / f'scene{i}.png'); scene['image'] = f'scene{i}.png'
    s.STATE['profiles'].append({'id': 'flow', 'label': 'Flow', 'balance': 300})
    return j


def queued(j):
    return [t for t in s.STATE['tasks'] if t['job'] == j['id'] and t['status'] == 'queued']


def engine_of(t):
    return 'flow' if t['kind'] == 'flow_video' else t['payload']['engine']


def fail(t, result):
    t['status'] = 'claimed'
    if t['kind'] == 'flow_video':
        p = s.profile_by(t['profile']); p['balance'] -= t['payload']['cost']
        t['reservation'] = {'profile': p['id'], 'amount': t['payload']['cost'], 'refunded': False}
    s.accept_task_result(t, result)


def deliver(j, t):
    name = t['slot'].replace(':', '_') + '_' + s.uid() + '.mp4'; (s.job_dir(j) / name).write_bytes(b'clip')
    t['status'] = 'claimed'; s.accept_task_result(t, {'ok': True, 'file': name})


class RoutingUnit(unittest.TestCase):
    def test_clip_1_grok_then_flow_never_grok_after(self):
        self.assertEqual(engine_chain.v09_next({}, 0, True), 'grok')
        self.assertEqual(engine_chain.v09_next({}, 0, False), 'flow', 'Grok not available: Flow')
        sc = {'engine_tries': [{'engine': 'grok', 'kind': 'quota'}]}
        self.assertEqual(engine_chain.v09_next(sc, 0, True), 'flow', 'Grok failed: Flow')
        for k in range(1, 6):
            self.assertEqual(engine_chain.v09_next({}, k, True), 'flow', 'Grok never makes clip 2 or later')
        sc = {'engine_tries': [{'engine': 'flow', 'kind': 'refusal'}]}
        self.assertEqual(engine_chain.v09_next(sc, 3, True, True), 'flow', 'one adapted Flow retry')
        sc['engine_tries'].append({'engine': 'flow', 'kind': 'refusal'})
        self.assertEqual(engine_chain.v09_next(sc, 3, True, True), 'vidogrid')
        sc['engine_tries'].append({'engine': 'vidogrid', 'kind': 'refusal'})
        self.assertEqual(engine_chain.v09_next(sc, 3, True, True), 'vidogrid', 'Vidogrid a second time')
        sc['engine_tries'].append({'engine': 'vidogrid', 'kind': 'refusal'})
        self.assertIsNone(engine_chain.v09_next(sc, 3, True, True), 'two Vidogrid tries at most')
        tech = {'engine_tries': [{'engine': 'flow', 'kind': 'interface'}]}
        self.assertIsNone(engine_chain.v09_next(tech, 2, True, True), 'Vidogrid only for refused scenes')
        self.assertIsNone(engine_chain.v09_next({'engine_tries': [{'engine': 'flow', 'kind': 'refusal'}] * 2}, 2, True, False))
        self.assertNotIn('arena', engine_chain.order({}, {'clip_routing': engine_chain.V09}))
        self.assertNotIn('arena', engines.AVAILABLE)

    def test_omni_12_is_ten_seconds(self):
        j = {'config': {'flow_model': engines.OMNI_12}}
        self.assertEqual(engines.flow_seconds(j), 10); self.assertEqual(engines.seconds(j, 'grok'), 10)
        self.assertEqual(engines.clip_length(j, 9.97, {'engine': 'flow'}), 10.0)
        self.assertEqual(engines.word_limit(j), 30)
        self.assertEqual(engines.flow_seconds({'config': {'flow_model': 'gemini_omni_flash'}}), 8, 'older episodes keep 8 s')


class Decoupage(unittest.TestCase):
    def test_one_scene_per_ten_seconds_plus_the_call(self):
        self.assertEqual(moteur_v09.scene_count(60, 10), 7)
        self.assertEqual(moteur_v09.scene_count(61, 10), 7, 'a last second alone makes no scene')
        self.assertEqual(moteur_v09.scene_count(63, 10), 8)
        self.assertEqual(moteur_v09.scene_count(228, 10), 24)
        rows = moteur_v09.decoupage(TRANSCRIPT, 30, 10, 4)
        self.assertEqual([r['ref'] for r in rows], ['00:00-00:10', '00:10-00:20', '00:20-00:30'])
        self.assertEqual(len(rows[0]['lines']), 2); self.assertIn('lit', rows[1]['lines'][0]); self.assertIn('femme', rows[2]['lines'][0])

    def test_guidance_is_the_v09_faithful_copy(self):
        g = source_video.guidance('identical', {'duration': 30, 'transcript': TRANSCRIPT}, 0, 4, clip_seconds=10, language='Français (fr-FR)')
        for needle in ('COPIE FIDÈLE', 'À L’IDENTIQUE', 'ref 00:10-00:20', 'Scène 4 — APPEL', 'Amen', 'mêmes répliques', '100 % fruit', 'traduites fidèlement'):
            self.assertIn(needle, g)
        self.assertNotIn('reformulées', g)


class ScheduleV09(unittest.TestCase):
    def setUp(self):
        s.STATE = state()

    def test_clip_1_on_grok_clips_2_on_flow_omni_12(self):
        j = clip_job(); s.schedule(j)
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:0', 'grok'))
        self.assertEqual(t['payload']['seconds'], 10)
        prompt = t['payload']['prompt']
        self.assertIn('10 seconds', prompt); self.assertIn('Only the character who speaks moves his or her lips', prompt)
        self.assertIn('never human skin', prompt); self.assertIn('Language: Français (fr-FR) only', prompt)
        deliver(j, t)
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:1', 'flow'))
        self.assertEqual((t['payload']['model'], t['payload']['seconds'], t['payload']['cost'], t['payload']['resolution']), (engines.OMNI_12, 10, 30, '720p'))
        deliver(j, t)
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:2', 'flow'))

    def test_grok_not_ready_clip_1_goes_to_flow(self):
        s.STATE = state(sites=('chatgpt',))
        j = clip_job(); s.schedule(j)
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:0', 'flow'))

    def test_grok_failure_moves_clip_1_to_flow_and_grok_never_comes_back(self):
        j = clip_job(); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'error_kind': 'quota', 'retry_after': 3600, 'generation_submitted': False, 'error': 'Grok Imagine : limite du compte atteinte.'})
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:0', 'flow'))
        self.assertIn('Clip 1 : Grok est à sa limite', j['events'][-2]['text'] + j['events'][-1]['text'])
        fail(t, {'ok': False, 'error_kind': 'interface', 'generation_submitted': False, 'error': 'Flow : page indisponible.'})
        for task in queued(j):
            self.assertNotEqual(engine_of(task), 'grok')

    def test_refused_scene_gets_vidogrid_after_flow(self):
        j = clip_job(); j['scenes'][1]['engine_tries'] = [{'engine': 'flow', 'kind': 'refusal', 'round': 0, 'reason': 'x'}] * 2
        deliver(j, (s.schedule(j), queued(j)[0])[1])  # clip 1 (Grok)
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:1', 'vidogrid'))
        self.assertEqual(t['payload']['seconds'], 10)


if __name__ == '__main__':
    unittest.main()


class CharacterStyles(unittest.TestCase):
    def test_at_least_ten_styles_from_tiktok_and_never_twice_in_a_row(self):
        import character_styles as cs
        self.assertGreaterEqual(len(cs.STYLES), 10)
        for k, v in cs.STYLES.items():
            self.assertTrue(v['source'].startswith('https://www.tiktok.com/@'), k)
            self.assertFalse(moteur_v09.BRANDS.search(v['make']), k)
        self.assertEqual(cs.pick('chats', ['chats']), 'chats', 'the owner may choose the same style on purpose')
        recent = []
        for _ in range(12):
            recent.insert(0, cs.pick('auto', recent))
        self.assertEqual(len(set(recent)), 12, 'auto goes through every style before repeating one')
        self.assertNotEqual(cs.pick('auto', ['verre_liquide']), 'verre_liquide')
        with self.assertRaises(ValueError):
            cs.pick('sora', [])

    def test_style_reaches_writer_boards_and_clips(self):
        s.STATE = state()
        j = clip_job(); j['config']['character_style'] = 'verre_liquide'
        s.STATE['jobs'].remove(j); s.STATE['jobs'].append(j)
        j['source_analysis'] = {'duration': 30, 'transcript': TRANSCRIPT}
        prompt = s.script_prompt(j)
        self.assertIn('personnages en verre', prompt); self.assertIn('STYLE DES PERSONNAGES IMPOSÉ', prompt)
        self.assertNotIn('humanoïde-fruit : la tête EST le fruit', prompt)
        self.assertIn('transparent glossy glass body', s.plan_image_block(j, j['scenes'][0]))
        self.assertIn('transparent glossy glass body', s.sheet_prompt(j))
        self.assertIn('transparent glossy glass body', s.clip_prompt(j, 1, 'flow'))
