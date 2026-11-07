"""0.1.91: « Préparer mes comptes », accounts before starting, « À régler » during production, parallel Flow clips.

Real case 06/11/2026: in the middle of a production two Flow clips failed « Page du fournisseur indisponible ou vide après
90 secondes (connexion requise, vérification anti-robot ou blocage) » and the episode went to « Action requise »."""
import datetime as dt, importlib.util, json, os, pathlib, sys, tempfile, threading, time, unittest, urllib.error, urllib.request
from unittest.mock import patch

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_readiness', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import flow_accounts, readiness


def iso(ago=0):
    return dt.datetime.fromtimestamp(time.time() - ago, dt.timezone.utc).isoformat()


def profile(name, slot, balance=50, state=None):
    p = {'id': name, 'label': name + '@example.com', 'flow_email': name + '@example.com', 'flow_client': 'win', 'balance': balance,
         'flow_url': f'https://flow.google.com/u/{slot}/project/{name}', 'auto_enabled': True, 'slot': slot}
    if state:
        p['readiness'] = {'state': state, 'reason': 'Vérification anti-robot à faire', 'at': iso()}
    return p


def studio(*profiles, chatgpt='ready'):
    s.STATE = s.fresh(); s.STATE['settings']['flow_auto'] = True
    s.STATE['clients'] = {'win': {'id': 'win', 'auto': True, 'role': 'all', 'seen': iso(2)}}
    s.STATE['profiles'] = list(profiles)
    if chatgpt:
        s.STATE['readiness'] = {'sites': {'chatgpt': {'state': chatgpt, 'reason': 'Connexion requise' if chatgpt != 'ready' else '', 'at': iso()}}, 'pending': []}


def clip_job(scenes=3):
    j = {'id': s.uid(), 'title': 'Épisode', 'stage': 'clips', 'status': 'running', 'events': [], 'flow_profile': 'a',
         'config': {'flow_cost': 12, 'provider': 'chatgpt', 'video_engine': 'flow'}, 'characters': [],
         'scenes': [{'image': f'image{i}.png', 'dialogue': [], 'video_prompt': 'scene'} for i in range(scenes)]}
    s.STATE['jobs'].append(j); return j


def queued(j):
    return [t for t in s.STATE['tasks'] if t['job'] == j['id'] and t['status'] in ('queued', 'claimed')]


class FirstStep(unittest.TestCase):
    def test_nothing_starts_before_chatgpt_and_a_clip_engine(self):
        studio(chatgpt=None)
        self.assertEqual([m['service'] for m in readiness.setup_missing(s.STATE)], ['chatgpt', 'flow'])
        s.STATE['sites'] = {'chatgpt': {'connected': True}}
        self.assertEqual([m['service'] for m in readiness.setup_missing(s.STATE)], ['flow'])
        s.STATE['profiles'] = [profile('a', 0)]
        self.assertEqual(readiness.setup_missing(s.STATE), [])
        s.STATE['profiles'] = [profile('a', 0, state='fix')]
        self.assertEqual(len(readiness.setup_missing(s.STATE)), 1, 'an account « À régler » is not a ready account')
        s.STATE['readiness'] = {'sites': {'grok': {'state': 'ready', 'at': iso()}}}
        self.assertEqual(readiness.setup_missing(s.STATE), [], 'Grok is a clip engine too')

    def test_mask_keeps_the_domain_only(self):
        self.assertEqual(readiness.mask('olga.fruit@example.com'), 'ol•••t@example.com')


class Gate(unittest.TestCase):
    def test_known_problem_blocks_and_unknown_is_checked_first(self):
        studio(profile('a', 0, state='fix'), profile('b', 1, state='fix'))
        j = clip_job()
        found = s.gate_blockers(j, setup=False)
        self.assertEqual({b['key'] for b in found}, {'flow:a', 'flow:b'})
        self.assertIn('anti-robot', readiness.describe(found))
        # One account ready: the others are simply left out of the rotation, nothing blocks.
        s.STATE['profiles'][1]['readiness']['state'] = 'ready'
        self.assertEqual(s.gate_blockers(j, setup=False), [])
        # Never checked: no blocker, a short check first.
        studio(profile('a', 0), profile('b', 1), profile('c', 2))
        j = clip_job()
        self.assertEqual(s.gate_blockers(j), [])
        self.assertFalse(s.start_check(j))
        req = s.STATE['bridge_requests'][-1]
        self.assertEqual(req['type'], 'readiness'); self.assertEqual(len(req['profiles']), 2, 'two accounts at most before starting')
        self.assertNotIn('password', json.dumps(req))
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.schedule(j)
        self.assertEqual(queued(j), [], 'nothing is queued while the check runs')

    def test_check_answer_starts_or_stops_cleanly(self):
        studio(profile('a', 0), profile('b', 1))
        j = clip_job(); s.start_check(j); rid = j['accounts_check']['id']
        readiness.apply_report(s.STATE, {'id': rid, 'profiles': {'a': {'state': 'fix', 'reason': 'Connexion requise'}, 'b': {'state': 'ready', 'balance': 40}}}, iso(), time.time())
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.end_check(j)
        self.assertEqual(j['status'], 'running')
        self.assertEqual({t['profile'] for t in queued(j)}, {'b'}, 'the account « À régler » is skipped')
        self.assertEqual(s.profile_by('b')['balance'], 40)
        # Every account able to pay is « À régler »: clean stop with the list, nothing queued.
        studio(profile('a', 0), profile('b', 1))
        j = clip_job(); s.start_check(j)
        readiness.apply_report(s.STATE, {'profiles': {'a': {'state': 'fix', 'reason': 'Connexion requise'}, 'b': {'state': 'fix', 'reason': 'Page vide'}}}, iso(), time.time())
        s.end_check(j)
        self.assertEqual(j['status'], 'attention'); self.assertEqual(queued(j), [])
        self.assertIn('Comptes à régler avant de commencer', j['alerts'][-1]['text'])

    def test_no_answer_does_not_block_for_ever(self):
        studio(profile('a', 0))
        j = clip_job(); s.start_check(j)
        j['accounts_check']['at'] = iso(readiness.CHECK_TIMEOUT + 5)
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            self.assertTrue(s.readiness_tick())
        self.assertNotIn('accounts_check', j); self.assertTrue(queued(j))

    def test_no_window_online_starts_at_once(self):
        studio(profile('a', 0)); s.STATE['clients']['win']['seen'] = iso(3600)
        self.assertTrue(s.start_check(clip_job()))


class DuringProduction(unittest.TestCase):
    def claim(self, client='win', lane='video'):
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            for j in s.STATE['jobs']:
                s.schedule(j)
        for t in s.STATE['tasks']:
            if t['status'] == 'queued':
                p = s.profile_by(t['profile'])
                if any(o['status'] == 'claimed' and o.get('profile') == t['profile'] for o in s.STATE['tasks']):
                    continue
                t['status'] = 'claimed'; t['client'] = client; p['balance'] -= 12
                t['reservation'] = {'profile': p['id'], 'amount': 12, 'refunded': False}
                return t

    def test_page_that_does_not_open_marks_the_account_and_switches(self):
        studio(profile('a', 0), profile('b', 1)); s.STATE['settings']['parallel_flow'] = 1
        j = clip_job(1)
        t = self.claim()
        self.assertEqual(t['profile'], 'a')
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.accept_task_result(t, {'ok': False, 'error': 'Page du fournisseur indisponible ou vide après 90 secondes (Vérification anti-robot à faire)',
                                     'generation_submitted': False, 'flow_blocked': 'not_ready', 'not_ready': {'state': 'fix', 'reason': 'Vérification anti-robot à faire'}})
        a = s.profile_by('a')
        self.assertEqual(a['readiness']['state'], 'fix'); self.assertEqual(a['balance'], 50, 'reservation cancelled: nothing sent')
        self.assertNotIn('blocked', a, 'kept for later, not marked empty')
        self.assertEqual(j['status'], 'running', 'no « Action requise » while an account is ready')
        self.assertEqual([x['profile'] for x in queued(j)], ['b'])

    def test_action_required_only_when_no_account_is_ready(self):
        studio(profile('a', 0), profile('b', 1, state='fix'))
        j = clip_job(1)
        t = self.claim()
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.accept_task_result(t, {'ok': False, 'error': 'Page du fournisseur indisponible', 'generation_submitted': False,
                                     'flow_blocked': 'not_ready', 'not_ready': {'state': 'fix', 'reason': 'Connexion requise'}})
        self.assertEqual(j['status'], 'attention'); self.assertEqual(queued(j), [])
        self.assertIn('Aucun compte Google Flow prêt', j['alerts'][-1]['text'])
        self.assertIn('b•••@example.com', j['alerts'][-1]['text'])

    def test_chat_page_marks_chatgpt(self):
        studio(profile('a', 0))
        j = clip_job(1); j['stage'] = 'images'
        t = {'id': 't1', 'job': j['id'], 'kind': 'chat_image', 'slot': 'image:0', 'status': 'claimed', 'payload': {'provider': 'chatgpt'}}
        s.STATE['tasks'].append(t)
        s.accept_task_result(t, {'ok': False, 'error': 'Page du fournisseur indisponible', 'not_ready': {'state': 'fix', 'reason': 'Connexion requise'}})
        self.assertEqual(s.STATE['readiness']['sites']['chatgpt']['state'], 'fix')
        self.assertTrue(s.gate_blockers(j, setup=False), 'Reprendre is refused while ChatGPT is « À régler »')

    def test_success_marks_the_account_ready(self):
        studio(profile('a', 0, state='fix'))
        s.STATE['profiles'][0]['readiness']['at'] = iso(3600)
        t = {'id': 't2', 'job': 'x', 'kind': 'flow_video', 'profile': 'a'}
        j = clip_job(2); t['job'] = j['id']; t['slot'] = 'clip:0'; t['status'] = 'claimed'; s.STATE['tasks'].append(t)
        (s.job_dir(j) / 'c.mp4').write_bytes(b'x')
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.accept_task_result(t, {'ok': True, 'file': 'c.mp4'})
        self.assertEqual(s.profile_by('a')['readiness']['state'], 'ready')


class ParallelClips(unittest.TestCase):
    def test_two_clips_on_two_accounts_never_the_same_account(self):
        studio(profile('a', 0), profile('b', 1), profile('c', 2, balance=5))
        j = clip_job(3)
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.schedule(j); s.schedule(j); s.schedule(j)
        tasks = queued(j)
        self.assertEqual(len(tasks), 2, 'parallel clips: 2 by default')
        self.assertEqual({t['profile'] for t in tasks}, {'a', 'b'})
        self.assertEqual({t['slot'] for t in tasks}, {'clip:0', 'clip:1'})
        self.assertEqual(j['flow_profile'], 'a', 'the extra clip does not change the episode account')

    def test_setting_one_keeps_one_clip(self):
        studio(profile('a', 0), profile('b', 1)); s.STATE['settings']['parallel_flow'] = 1
        j = clip_job(3)
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.schedule(j); s.schedule(j)
        self.assertEqual(len(queued(j)), 1)

    def test_one_account_ready_one_clip(self):
        studio(profile('a', 0), profile('b', 1, state='fix'))
        j = clip_job(3)
        with patch.object(s, 'flow_reference', return_value='r.jpg'):
            s.schedule(j); s.schedule(j)
        self.assertEqual([t['profile'] for t in queued(j)], ['a'])
        self.assertEqual(j['status'], 'running')


class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = cls.http.server_port
        cls.base = f'http://127.0.0.1:{s.PORT}'; threading.Thread(target=cls.http.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close()

    def req(self, path, body=None, bridge=False):
        headers = {'Content-Type': 'application/json', 'Origin': self.base}
        if bridge:
            headers['Authorization'] = 'Bearer ' + s.STATE['token']
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with urllib.request.urlopen(r) as x:
            return json.load(x)

    def test_create_refused_with_the_list_and_nothing_created(self):
        studio(chatgpt=None); s.STATE['clients'] = {}
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/job', {'brief': 'Une histoire de fruits assez longue', 'config': {}})
        self.assertEqual(e.exception.code, 409)
        body = json.load(e.exception)
        self.assertEqual([b['service'] for b in body['blockers']], ['chatgpt', 'flow'])
        self.assertEqual(s.STATE['jobs'], [])

    def test_resume_refused_while_chatgpt_is_to_fix(self):
        studio(profile('a', 0), chatgpt='fix')
        j = clip_job(1); j['status'] = 'paused'; j['stage'] = 'images'
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.req('/api/job/' + j['id'], {'action': 'resume'})
        self.assertEqual(e.exception.code, 409)
        self.assertEqual(json.load(e.exception)['blockers'][0]['key'], 'site:chatgpt')
        self.assertEqual(j['status'], 'paused')

    def test_prepare_fix_recheck_and_report(self):
        studio(profile('a', 0))
        state = self.req('/api/sites', {'action': 'prepare'})
        req = s.STATE['bridge_requests'][-1]
        self.assertEqual(req['sites'], ['chatgpt']); self.assertEqual([p['id'] for p in req['profiles']], ['a'])
        self.assertIn('flow:a', state['readiness']['pending'])
        # « Régler maintenant » only shows the tab; « C'est fait » checks that account again.
        self.req('/api/sites', {'action': 'fix', 'target': 'flow:a'})
        self.assertEqual(s.STATE['bridge_requests'][-1]['type'], 'show')
        self.req('/api/sites', {'action': 'recheck', 'target': 'site:chatgpt'})
        self.req('/api/bridge/readiness', {'client': 'win', 'sites': {'chatgpt': {'state': 'ready', 'email': 'olga@example.com'}},
                                           'profiles': {'a': {'state': 'fix', 'reason': 'Connexion requise'}}}, bridge=True)
        self.assertEqual(s.profile_by('a')['readiness']['reason'], 'Connexion requise')
        self.assertEqual(s.STATE['readiness']['pending'], [])
        self.assertEqual(s.STATE['identities'][0]['email'], 'olga@example.com', 'the ChatGPT account joins Mes comptes by itself')

    def test_light_requests_only_show_tabs(self):
        studio(profile('a', 0))
        s.STATE['bridge_requests'] = [{'type': 'readiness', 'id': 'x'}, {'type': 'show', 'site': 'chatgpt'}]
        r = urllib.request.Request(self.base + '/api/bridge/requests?client=win&light=1', headers={'Authorization': 'Bearer ' + s.STATE['token']})
        with urllib.request.urlopen(r) as x:
            self.assertEqual([i['type'] for i in json.load(x)], ['show'])
        self.assertEqual([i['type'] for i in s.STATE['bridge_requests']], ['readiness'])

    def test_remove_all_of_one_service(self):
        studio(profile('a', 0), profile('b', 1))
        r = self.req('/api/account', {'remove_all_service': 'flow'})
        self.assertEqual(r['removed'], 2); self.assertEqual(s.STATE['profiles'], [])

    def test_claim_never_twice_the_same_account(self):
        studio(profile('a', 0), profile('b', 1))
        j = clip_job(3)
        def take():
            r = urllib.request.Request(self.base + '/api/bridge/task?client=win&lane=video', headers={'Authorization': 'Bearer ' + s.STATE['token']})
            with patch.object(s, 'flow_reference', return_value='r.jpg'), urllib.request.urlopen(r) as x:
                return json.load(x)
        t1, t2, t3 = take(), take(), take()
        self.assertIsNotNone(t1); self.assertIsNotNone(t2); self.assertIsNone(t3, 'two video tasks at most per window')
        self.assertNotEqual(t1['profile'], t2['profile'])
        self.assertEqual(s.profile_by('a')['balance'] + s.profile_by('b')['balance'], 76, 'one reservation per account')


if __name__ == '__main__':
    unittest.main()
