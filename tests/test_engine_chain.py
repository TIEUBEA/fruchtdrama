"""0.1.93: bascule de moteur par clip (Flow, Arena, Vidogrid, Grok), prompt adouci au dernier tour, clip mis de côté
sans bloquer les autres, moteur gardé par clip pour le montage (owner 06/11/2026: « un essai par cas »)."""
import datetime as dt, importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile, time, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_engine_chain', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import engine_chain, engines


def fresh(sites=('chatgpt', 'arena', 'vidogrid', 'grok')):
    state = s.fresh(); at = dt.datetime.now(dt.timezone.utc).isoformat()
    state['readiness'] = {'sites': {n: {'state': 'ready', 'reason': '', 'at': at} for n in sites}, 'pending': []}
    return state


def clip_job(balance=100, engine='flow', n=4):
    from PIL import Image
    j = {'id': s.uid(), 'stage': 'script', 'status': 'running', 'events': [], 'brief': 'b', 'characters': [], 'scenes': [], 'candidates': [],
         'flow_profile': 'flow', 'selected': {'title': 'Référence', 'url': 'https://www.tiktok.com/@a/video/1'},
         'config': {'scene_count': n, 'provider': 'chatgpt', 'flow_cost': 12, 'language': 'Deutsch (de-DE)', 'video_engine': engine}}
    s.STATE['jobs'].append(j)
    s.store_script(j, {'title': 'Omas Reise', 'cover_title': 'WER?', 'description': 'd',
                       'characters': [{'id': 'orange', 'name': 'Oma', 'appearance': 'Orange', 'voice': 'v', 'image_prompt': 'p'}],
                       'scenes': [{'characters': ['orange'], 'meaning': 'm', 'image_prompt': 'i', 'video_prompt': 'The orange punches the door.',
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


class ChainUnitTests(unittest.TestCase):
    def test_order_and_validation(self):
        self.assertEqual(engine_chain.order({}), ['flow', 'arena', 'vidogrid', 'grok'])
        self.assertEqual(engine_chain.order({'engine_chain': ['arena', 'flow']}, {'video_engine': 'flow'}), ['arena', 'flow'], 'Flow is the default, not a choice')
        self.assertEqual(engine_chain.order({}, {'video_engine': 'grok'}), ['grok', 'flow', 'arena', 'vidogrid'], 'the episode engine first')
        self.assertEqual(engine_chain.validate(['grok', 'grok', 'flow']), ['grok', 'flow'])
        for bad in ([], ['sora'], 'flow'):
            with self.assertRaises(ValueError):
                engine_chain.validate(bad)

    def test_pick_advance_and_soften(self):
        scene = {}; chain = ['flow', 'arena', 'vidogrid', 'grok']
        ready = lambda e: e != 'vidogrid'
        self.assertEqual(engine_chain.pick(scene, chain, ready), 'flow')
        engine_chain.record(scene, 'flow', 'refusal', 'Flow : refusé. Diagnostic {x}', 'now')
        self.assertEqual(scene['engine_tries'][0]['reason'], 'refusé')
        self.assertEqual(engine_chain.advance(scene, chain, ready), 'arena')
        engine_chain.record(scene, 'arena', 'timeout', 'x', 'now')
        self.assertEqual(engine_chain.advance(scene, chain, ready), 'grok', 'an engine without a ready account is skipped')
        engine_chain.record(scene, 'grok', 'other', 'x', 'now')
        self.assertEqual(engine_chain.advance(scene, chain, ready), 'flow', 'last round: Flow again')
        self.assertEqual(engine_chain.round_of(scene), 1)
        engine_chain.record(scene, 'flow', 'refusal', 'x', 'now')
        self.assertIsNone(engine_chain.advance(scene, chain, ready), 'one try only in the last round')
        self.assertIn('Flow (prompt adouci) : x', engine_chain.summary(scene))
        soft = engine_chain.soften('The orange punches the thief with a knife, blood everywhere.')
        self.assertTrue(soft.startswith('All-audiences family animation clip'))
        for word in ('punches', 'knife', 'blood'):
            self.assertNotIn(word, soft.split('\n', 1)[1].split('\nIf a detail')[0])
        self.assertEqual(engine_chain.line(2, 'flow', 'refusal', 'Contenu non conforme.', 'arena'), 'Clip 3 : Flow a refusé (Contenu non conforme) → essai sur Arena.')

    def test_montage_length_follows_each_clip_engine(self):
        j = {'config': {'video_engine': 'flow'}}
        self.assertEqual(engines.clip_length(j, 7.6, {'engine': 'flow'}), 8.0)
        self.assertEqual(engines.clip_length(j, 6.04, {'engine': 'grok'}), 6.04)
        self.assertEqual(engines.clip_length(j, 10.04, {'engine': 'vidogrid'}), 10.04)
        self.assertEqual(engines.clip_length(j, 7.2, {'engine': 'arena'}), 7.2)
        self.assertEqual(engines.clip_length(j, 7.2, {}), 8.0, 'older clips: the episode engine')
        self.assertEqual(engines.clip_range(j, {'engine': 'vidogrid'}), (5.5, 10.5))


class ChainScheduleTests(unittest.TestCase):
    def setUp(self):
        s.STATE = fresh()

    def test_restored_1080p_episode_queues_native_720p_without_changing_media(self):
        j=clip_job();j['config'].update(flow_model='gemini_omni_flash',flow_resolution='1080p')
        images=[x['image'] for x in j['scenes']]
        s.schedule(j)
        self.assertEqual(queued(j)[0]['payload']['resolution'],'720p')
        self.assertEqual(j['config']['flow_resolution_requested'],'1080p')
        self.assertEqual([x['image'] for x in j['scenes']],images)
        self.assertEqual(s.frame_size(j),(1080,1920))

    def test_slow_grok_gets_one_more_try_and_a_grok_refusal_is_final(self):
        # 11/11/2026, crèche clip 5: « Grok n'a pas rendu le clip à temps » left the clip for the owner.
        tries=lambda *k:{'engine_tries':[{'engine':'flow','kind':'refusal'},{'engine':'flow','kind':'refusal'}]+[{'engine':'grok','kind':x} for x in k]}
        self.assertEqual(engine_chain.flow_grok_next(tries('timeout')),'grok')
        self.assertEqual(engine_chain.flow_grok_next(tries('interface')),'grok')
        self.assertIsNone(engine_chain.flow_grok_next(tries('timeout','timeout')),'two Grok tries at most')
        self.assertIsNone(engine_chain.flow_grok_next(tries('refusal')),'a refusal by Grok is final')
        # A clip already held for the owner goes again by itself under the new rule.
        s.STATE['settings']['clip_routing']='flow_grok_per_clip'
        j=clip_job(n=2);j['scenes'][1].update(tries('timeout'),engine_exhausted=True)
        self.assertNotIn(1,s.held_clips(j));self.assertNotIn('engine_exhausted',j['scenes'][1])

    def test_flow_refusal_uses_grok_for_only_that_clip_then_returns_to_flow(self):
        s.STATE['settings'].update(clip_routing='flow_grok_per_clip',parallel_clips=False)
        j=clip_job(engine='grok',n=2)
        self.assertEqual(engine_chain.order(s.STATE['settings'],j['config']),['flow','grok'])
        s.schedule(j);t=queued(j)[0]
        self.assertEqual((t['slot'],engine_of(t)),('clip:0','flow'))
        fail(t,{'ok':False,'error_kind':'refusal','generation_submitted':False,'error':'Flow : contenu refusé.'})
        rewrite=queued(j)[0]
        self.assertEqual(rewrite['slot'],'flow_rewrite:0')
        self.assertEqual(j['scenes'][0]['image'],'scene0.png')
        rewrite['status']='claimed'
        adapted={'image_prompt':'Original desk with a folded letter','video_prompt':'Oma walks to the desk and opens the letter',
                 'deplacement':'Oma walks from the door to the desk'}
        s.accept_task_result(rewrite,{'ok':True,'text':json.dumps({'production_id':j['id'],'generation_task_id':rewrite['id'],'scene_rewrite':adapted})})
        board=queued(j)[0]
        self.assertEqual(board['slot'],'image:0')
        self.assertIn(adapted['deplacement'],board['payload']['prompt'])
        from PIL import Image
        Image.new('RGB',(32,64),(180,90,10)).save(s.job_dir(j)/'adapted.png')
        board['status']='claimed'
        s.accept_task_result(board,{'ok':True,'file':'adapted.png'})
        retry=queued(j)[0]
        self.assertEqual((retry['slot'],engine_of(retry)),('clip:0','flow'))
        self.assertIn(adapted['deplacement'],retry['payload']['prompt'])
        fail(retry,{'ok':False,'error_kind':'refusal','generation_submitted':True,'flow_failed':True,'error':'Flow : nouveau refus.'})
        t=queued(j)[0];self.assertEqual((t['slot'],engine_of(t)),('clip:0','grok'))
        deliver(j,t)
        self.assertEqual(j['scenes'][0]['engine'],'grok')
        t=queued(j)[0];self.assertEqual((t['slot'],engine_of(t)),('clip:1','flow'))
        deliver(j,t)
        self.assertEqual(j['scenes'][1]['engine'],'flow')

    def test_faithful_remake_follows_flow_adaptation_flow_then_grok_keeping_the_source_words(self):
        # Owner 10/11/2026 (« LA BOUTEILLE SOUS LE LIT », clip 17 refused twice, production stopped): the same rule as
        # every episode — Flow, adaptation by ChatGPT, Flow again, then Grok — and the source words never change.
        s.STATE['settings'].update(clip_routing='flow_grok_per_clip',parallel_clips=False)
        j=clip_job(n=2)
        j['selected']['source']='owner_link';j['config'].update(recreate='identical',remake_exact=True)
        j['source_analysis']={'duration':16,'exact_windows':[[(0.5,'Hallo Welt')],[(8.5,'Hallo Welt')]]}
        self.assertTrue(s.exact_remake(j))
        s.schedule(j);t=queued(j)[0];self.assertEqual((t['slot'],engine_of(t)),('clip:0','flow'))
        fail(t,{'ok':False,'error_kind':'refusal','generation_submitted':True,'flow_failed':True,'error':'Flow : contenu refusé.'})
        self.assertNotEqual(j['status'],'attention','no stop at the first refusal')
        rewrite=queued(j)[0];self.assertEqual(rewrite['slot'],'flow_rewrite:0')
        self.assertIn('Ne change pas les paroles',rewrite['payload']['prompt'])
        rewrite['status']='claimed'
        adapted={'image_prompt':'Kitchen seen from the window','video_prompt':'Oma turns away from the bed and walks to the window',
                 'dialogue':[{'speaker':'orange','text':'Ganz andere Worte'}]}
        s.accept_task_result(rewrite,{'ok':True,'text':json.dumps({'production_id':j['id'],'generation_task_id':rewrite['id'],'scene_rewrite':adapted})})
        self.assertEqual(j['scenes'][0]['dialogue'][0]['text'],'Hallo Welt','the source words stay')
        self.assertEqual(j['scenes'][0]['video_prompt'],adapted['video_prompt'])
        board=queued(j)[0];self.assertEqual(board['slot'],'image:0')
        from PIL import Image
        Image.new('RGB',(32,64),(10,90,180)).save(s.job_dir(j)/'adapted.png')
        board['status']='claimed';s.accept_task_result(board,{'ok':True,'file':'adapted.png'})
        retry=queued(j)[0];self.assertEqual((retry['slot'],engine_of(retry)),('clip:0','flow'))
        fail(retry,{'ok':False,'error_kind':'refusal','generation_submitted':True,'flow_failed':True,'error':'Flow : nouveau refus.'})
        t=queued(j)[0];self.assertEqual((t['slot'],engine_of(t)),('clip:0','grok'))
        self.assertNotEqual(j['status'],'attention')
        self.assertIn('finished within the first 8 seconds',t['payload']['prompt'],'Grok 10 s, the 8 s segment is said in time')

    def test_a_flow_refusal_never_pauses_the_other_clips(self):
        # Owner 10/11/2026: « si Flow refuse, ça ne met pas en pause » — the refused scene is adapted by ChatGPT while the
        # next scenes keep going on Flow; Flow stays first for every scene, Grok only after two refusals of that scene.
        for exact in (False,True):
            s.STATE=fresh();s.STATE['settings'].update(clip_routing='flow_grok_per_clip',flow_auto=True)
            j=clip_job(n=4,balance=200)
            s.STATE['clients']={'win':{'id':'win','role':'all','auto':True,'seen':s.now()}}
            s.STATE['profiles']=[{'id':p,'label':p+'@x.com','flow_email':p+'@x.com','flow_client':'win','auto_enabled':True,'balance':100,'slot':k,
                                  'flow_url':f'https://flow.google.com/u/{k}/project/p{k}'} for k,p in enumerate(('a','b','c'))]
            j['flow_profile']='a'
            if exact:
                j['selected']['source']='owner_link';j['config'].update(recreate='identical',remake_exact=True)
                j['source_analysis']={'duration':32,'exact_windows':[[(0.5,'Hallo Welt')]]*4}
            s.schedule(j)
            t0=next(t for t in queued(j) if t['slot']=='clip:0')
            fail(t0,{'ok':False,'error_kind':'refusal','generation_submitted':True,'flow_failed':True,'error':'Flow : refusé.'})
            s.schedule(j)
            active={t['slot']:engine_of(t) if t['kind']!='chat_text' else 'chatgpt' for t in queued(j)}
            self.assertEqual(j['status'],'running','no pause, no « Action requise »')
            self.assertEqual(active.get('flow_rewrite:0'),'chatgpt','the refused scene goes to ChatGPT at once')
            self.assertTrue({active.get(f'clip:{k}') for k in (1,2,3)}=={'flow'},'the next scenes go on with Flow meanwhile')

    def test_flow_technical_error_and_empty_credit_do_not_spend_grok(self):
        s.STATE['settings']['clip_routing']='flow_grok_per_clip'
        j=clip_job(n=2);s.schedule(j);t=queued(j)[0]
        fail(t,{'ok':False,'error_kind':'interface','generation_submitted':False,'error':'Paramètres Flow indisponibles ; aucun envoi effectué.'})
        # 10/11/2026: a technical failure before anything was sent gets one more Flow try, never Grok…
        retry=queued(j)[0]
        self.assertEqual((retry['slot'],engine_of(retry)),('clip:0','flow'))
        self.assertNotEqual(j['status'],'attention')
        fail(retry,{'ok':False,'error_kind':'interface','generation_submitted':False,'error':'Réglage resolution non reconnu ; aucun envoi effectué.'})
        # …then the owner fixes the shared settings once, before the same failure repeats on every clip.
        self.assertFalse(any(engine_of(t)=='grok' for t in queued(j)))
        self.assertTrue(j['scenes'][0]['engine_exhausted'])
        self.assertEqual(j['status'],'attention','Fix shared Flow settings before repeating the same failure on every clip')
        self.assertEqual(queued(j),[])
        s.STATE=fresh();s.STATE['settings']['clip_routing']='flow_grok_per_clip'
        j=clip_job(balance=0);s.schedule(j)
        self.assertFalse(any(engine_of(t)=='grok' for t in queued(j)))

    def test_two_clip_specific_flow_failures_go_to_grok(self):
        # 12/11/2026 (« La méchante éducatrice », clip 2): image stuck in Flow, then its tab gone. Nothing sent, nothing
        # wrong with the shared settings: the clip goes to Grok instead of stopping the episode.
        import engine_chain
        scene={'engine_tries':[{'engine':'flow','kind':'interface','reason':'image toujours en traitement, rien ne progresse depuis 90 s'}]}
        self.assertEqual(engine_chain.flow_grok_next(scene),'flow')
        scene['engine_tries'].append({'engine':'flow','kind':'other','reason':'No tab with id: 12'})
        self.assertEqual(engine_chain.flow_grok_next(scene),'grok')
        scene['engine_tries'].append({'engine':'grok','kind':'refusal','reason':'refus'})
        self.assertIsNone(engine_chain.flow_grok_next(scene), 'a Grok refusal is final')

    def test_flow_account_without_settings_is_set_aside_and_the_next_account_takes_the_clip(self):
        s.STATE['settings'].update(clip_routing='flow_grok_per_clip',flow_auto=True)
        j=clip_job(n=1)
        win={'id':'win','role':'all','auto':True,'seen':s.now()};s.STATE['clients']={'win':win}
        s.STATE['profiles']=[{'id':p,'label':p+'@x.com','flow_email':p+'@x.com','flow_client':'win','auto_enabled':True,'balance':100,'slot':k,
                              'flow_url':f'https://flow.google.com/u/{k}/project/p{k}'} for k,p in enumerate(('a','b'))]
        j['flow_profile']='a';s.schedule(j);t=queued(j)[0];self.assertEqual(t['profile'],'a')
        fail(t,{'ok':False,'error_kind':'interface','generation_submitted':False,'flow_blocked':'not_ready',
                'not_ready':{'state':'fix','reason':'Flow ne montre pas ses réglages sur ce compte'},'error':'Paramètres Flow indisponibles après 15 s sur ce compte ; aucun envoi effectué.'})
        self.assertEqual(s.profile_by('a')['readiness']['state'],'fix','marked « À régler » in Mes comptes')
        nxt=queued(j)[0]
        self.assertEqual((engine_of(nxt),nxt['profile']),('flow','b'))
        self.assertNotEqual(j['status'],'attention')

    def test_uncertain_flow_submission_is_never_replayed_on_grok(self):
        s.STATE['settings']['clip_routing']='flow_grok_per_clip'
        j=clip_job(n=2);s.schedule(j);t=queued(j)[0]
        fail(t,{'ok':False,'error_kind':'restart','generation_submitted':True,'error':'Connexion interrompue après envoi.'})
        self.assertTrue(t['uncertain'])
        self.assertFalse(any(engine_of(t)=='grok' for t in queued(j)))

    def test_one_try_per_engine_then_softened_flow_then_owner(self):
        s.STATE["settings"]["grok_auto"] = True; j = clip_job(); s.schedule(j)
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:0', 'flow'))
        fail(t, {'ok': False, 'generation_submitted': False, 'error': 'Flow : coût affiché différent du budget prévu. Aucun envoi effectué.'})
        self.assertEqual(s.STATE['profiles'][0]['balance'], 100, 'nothing sent: reservation given back')
        self.assertEqual(j['status'], 'running'); self.assertFalse([a for a in j.get('alerts', []) if a['level'] == 'action'], 'no « Action requise »')
        self.assertIn('Clip 1 : Flow a échoué (coût affiché différent du budget prévu) → essai sur Arena.', [e['text'] for e in j['events']])
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:0', 'arena'))
        self.assertIn('8 seconds', t['payload']['prompt'])
        fail(t, {'ok': False, 'error_kind': 'refusal', 'generation_submitted': True, 'error': 'LMArena vidéo : génération refusée par la modération.'})
        t = queued(j)[0]; self.assertEqual(engine_of(t), 'vidogrid'); self.assertIn('10 seconds', t['payload']['prompt'])
        fail(t, {'ok': False, 'generation_submitted': True, 'error': 'Vidogrid : génération échouée (STATUS 503). Rien à attendre de plus.'})
        t = queued(j)[0]; self.assertEqual(engine_of(t), 'grok')
        self.assertNotIn('All-audiences', t['payload']['prompt'], 'first round: prompt unchanged')
        fail(t, {'ok': False, 'error_kind': 'timeout', 'generation_submitted': True, 'error': 'Grok Imagine : vidéo non détectée après 4 minutes.'})
        t = queued(j)[0]; self.assertEqual(engine_of(t), 'flow')
        self.assertIn('All-audiences family animation clip', t['payload']['prompt']); self.assertNotIn('punches', t['payload']['prompt'])
        self.assertIn('prompt adouci, nouvel essai sur Flow', j['events'][-2]['text'] + j['events'][-1]['text'])
        fail(t, {'ok': False, 'generation_submitted': False, 'error': 'Flow : image toujours en traitement, rien ne progresse depuis 90 s. Aucun envoi de génération effectué.'})
        self.assertEqual(s.held_clips(j), {0})
        alert = j['alerts'][-1]; self.assertEqual(alert['level'], 'action')
        for name in ('Flow', 'Arena', 'Vidogrid', 'Grok', 'prompt adouci'):
            self.assertIn(name, alert['text'])
        # The other clips go on.
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:1', 'flow')); self.assertEqual(j['status'], 'running')
        for k in (1, 2, 3):
            deliver(j, next(x for x in queued(j) if x['slot'] == f'clip:{k}'))
        self.assertEqual(j['status'], 'attention'); self.assertIn('Aucun moteur', j['events'][-1]['text'])
        self.assertEqual(queued(j), [])
        # « Refaire » with the owner's instruction: every engine again, Flow first.
        s.redo(j, 'clip:0', 'sans bagarre')
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:0', 'flow'))
        self.assertIn('sans bagarre', t['payload']['prompt']); self.assertNotIn('All-audiences', t['payload']['prompt'])

    def test_received_clip_keeps_its_engine_and_the_next_clip_starts_from_flow(self):
        j = clip_job(); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'generation_submitted': False, 'error': 'Flow : page indisponible.'})
        deliver(j, queued(j)[0])
        self.assertEqual(j['scenes'][0]['engine'], 'arena'); self.assertNotIn('engine_tries', j['scenes'][0])
        t = queued(j)[0]; self.assertEqual((t['slot'], engine_of(t)), ('clip:1', 'flow'))
        deliver(j, t); self.assertEqual(j['scenes'][1]['engine'], 'flow')

    def test_flow_without_credits_is_skipped_without_a_try(self):
        j = clip_job(balance=0); s.schedule(j)
        t = queued(j)[0]; self.assertEqual(engine_of(t), 'arena'); self.assertNotEqual(j['status'], 'waiting_credit')
        self.assertNotIn('engine_tries', j['scenes'][0])

    def test_engine_to_fix_is_skipped(self):
        s.STATE['readiness']['sites']['arena'] = {'state': 'fix', 'reason': 'Connexion requise', 'at': dt.datetime.now(dt.timezone.utc).isoformat()}
        j = clip_job(balance=0); s.schedule(j)
        self.assertEqual(engine_of(queued(j)[0]), 'vidogrid')

    def test_nothing_ready_keeps_the_old_wait_for_credits(self):
        s.STATE = fresh(sites=('chatgpt',))
        j = clip_job(balance=0); s.schedule(j)
        self.assertEqual(j['status'], 'waiting_credit'); self.assertEqual(queued(j), [])

    def test_uncertain_flow_submission_is_held_and_others_go_on(self):
        j = clip_job(); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'error': 'Génération trop longue ou média non détecté.'})
        self.assertEqual(s.STATE['profiles'][0]['balance'], 88, 'maybe charged: no silent refund')
        self.assertEqual(s.held_clips(j), {0}); self.assertEqual(j['alerts'][-1]['level'], 'action')
        self.assertIn('incertain', j['alerts'][-1]['text'])
        self.assertEqual([t['slot'] for t in queued(j)], ['clip:1'], 'never sent again by chance; the next clip goes')

    def test_flow_failure_message_is_not_uncertain(self):
        """dev 0.1.92.1: Flow shows why a generation failed (flow_failed): not charged, next engine at once."""
        j = clip_job(); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'error_kind': 'refusal', 'generation_submitted': True, 'flow_failed': True, 'error': 'Flow a refusé ce clip : Impossible de générer cette vidéo.'})
        self.assertEqual(s.uncertain_clip_tasks(j), []); self.assertEqual(s.STATE['profiles'][0]['balance'], 100)
        self.assertEqual(engine_of(queued(j)[0]), 'arena')
        self.assertIn('Clip 1 : Flow a refusé (Impossible de générer cette vidéo) → essai sur Arena.', [e['text'] for e in j['events']])

    def test_quota_walls_the_account_then_next_engine(self):
        s.engine_accounts.add(s.STATE, 'arena', 'A', 'compte-a@example.com')
        j = clip_job(balance=0); s.schedule(j)
        t = queued(j)[0]; self.assertEqual(t['payload']['account']['email'], 'compte-a@example.com')
        fail(t, {'ok': False, 'error_kind': 'quota', 'retry_after': 3600, 'generation_submitted': True, 'error': 'LMArena vidéo : limite du compte atteinte.'})
        self.assertTrue(s.engine_accounts.walled(s.engine_accounts.accounts(s.STATE, 'arena')[0], time.time()))
        self.assertEqual(engine_of(queued(j)[0]), 'vidogrid')

    def test_quota_with_nothing_else_keeps_the_wait(self):
        s.STATE = fresh(sites=('chatgpt',)); s.STATE['settings']['engine_chain'] = ['arena']
        s.engine_accounts.add(s.STATE, 'arena', 'A', 'compte-a@example.com')
        j = clip_job(balance=0, engine='arena'); s.schedule(j)
        fail(queued(j)[0], {'ok': False, 'error_kind': 'quota', 'retry_after': 600, 'generation_submitted': True, 'error': 'limite'})
        self.assertEqual(j['status'], 'waiting_quota')

    def test_one_clip_at_a_time_per_site(self):
        j = clip_job(balance=0)
        s.STATE['tasks'].append({'id': 'x', 'job': 'other', 'kind': 'engine_video', 'slot': 'clip:0', 'status': 'claimed', 'payload': {'engine': 'arena'}})
        self.assertTrue(s.engine_busy('arena')); self.assertFalse(s.engine_busy('vidogrid'))
        self.assertFalse(s.schedule_engine_clip(j, 1, 'arena', early=True, parallel=True))

    def test_engine_order_setting(self):
        s.STATE['settings']['engine_chain'] = engine_chain.validate(['vidogrid', 'flow'])
        j = clip_job(); s.schedule(j)
        self.assertEqual(engine_of(queued(j)[0]), 'vidogrid')


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg requis')
class MixedMontageTests(unittest.TestCase):
    def test_clips_of_four_engines_keep_their_length(self):
        s.STATE = fresh(); j = clip_job(); folder = s.job_dir(j)
        for i, (engine, seconds, size) in enumerate((('flow', 8, '72x128'), ('grok', 6, '48x84'), ('vidogrid', 10, '72x128'), ('arena', 8, '128x72'))):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=red:s={size}:r=10', '-f', 'lavfi', '-i', 'sine=f=440:r=16000',
                            '-t', str(seconds), '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', str(folder / f'clip{i}.mp4')], check=True)
            j['scenes'][i].update(clip=f'clip{i}.mp4', engine=engine)
        j.update(stage='edit', status='rendering')
        s.render_job(j['id'])
        self.assertEqual(j['status'], 'done', j['events'][-1]['text'])
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=width,height', '-of', 'csv=p=0', str(folder / 'final.mp4')], capture_output=True, text=True).stdout
        self.assertIn('1080,1920', out, 'every clip reframed to 1080 x 1920, even a landscape one')
        duration = float([x for x in out.split() if '.' in x and ',' not in x][-1])
        self.assertAlmostEqual(duration, 32, delta=0.7, msg='8 + 6 + 10 + 8 s')
        ass = (folder / 'subtitles.ass').read_text('utf-8-sig')
        self.assertIn('Dialogue: 0,0:00:24.', ass, 'last scene captions start after 8 + 6 + 10 s')


if __name__ == '__main__':
    unittest.main()


class ThirdPartyRedraw(unittest.TestCase):
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


class GrokNeedsOwner(unittest.TestCase):
    def test_grok_is_never_ready_without_the_owner(self):
        s.STATE = s.fresh()
        j = {'id': 'g', 'events': [], 'config': {}, 'scenes': [{}]}
        self.assertFalse(s.engine_ready(j, 'grok'))
        s.ask_grok(j, 0)
        self.assertEqual(j['alerts'][-1]['command'], 'allow_grok')
        n = len(j['alerts']); s.ask_grok(j, 0); self.assertEqual(len(j['alerts']), n, 'asked once')
