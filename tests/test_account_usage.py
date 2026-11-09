"""0.1.95: « quel compte est utilisé, quelle IA et à quel moment » (owner 06/11/2026). Stable Flow account numbers,
the account at work for each task, last use, readable switch lines, and the account kept under each received clip."""
import importlib.util, os, pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_account_usage', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)
import account_usage as u


def flow(pid, balance, **extra):
    return {'id': pid, 'label': pid + '@example.com', 'flow_email': pid + '@example.com', 'balance': balance, **extra}


class Numbers(unittest.TestCase):
    def test_first_numbers_follow_credits_then_never_move(self):
        st = {'profiles': [flow('aa', 10), flow('bb', 50), flow('cc', 30)]}
        u.number_flow(st)
        self.assertEqual([p['number'] for p in st['profiles']], [3, 1, 2])
        st['profiles'][1]['balance'] = 0; u.number_flow(st)
        self.assertEqual([p['number'] for p in st['profiles']], [3, 1, 2], 'spending credits never renumbers')

    def test_new_account_takes_the_smallest_free_number(self):
        st = {'profiles': [flow('aa', 10, number=1), flow('cc', 30, number=3), flow('dd', 99)]}
        u.number_flow(st)
        self.assertEqual(st['profiles'][2]['number'], 2)


class Usage(unittest.TestCase):
    def setUp(self):
        self.st = {'profiles': [flow('ar', 38, number=2)], 'jobs': [{'id': 'j', 'title': 'BANANITO'}], 'tasks': [
            {'id': 't1', 'job': 'j', 'kind': 'flow_video', 'profile': 'ar', 'slot': 'clip:2', 'status': 'claimed', 'claimed': '2026-11-06T10:00:00+00:00'},
            {'id': 't2', 'job': 'j', 'kind': 'chat_image', 'slot': 'image:6', 'status': 'claimed', 'payload': {'provider': 'chatgpt'}},
            {'id': 't3', 'job': 'j', 'kind': 'engine_video', 'slot': 'clip:3', 'status': 'claimed', 'payload': {'engine': 'grok', 'account': {'email': 'grok.one@example.com'}}},
            {'id': 't4', 'job': 'j', 'kind': 'chat_text', 'slot': 'script', 'status': 'queued', 'payload': {'provider': 'claude'}},
            {'id': 't5', 'job': 'j', 'kind': 'tiktok_search', 'slot': 'research', 'status': 'claimed', 'payload': {}}]}

    def test_who_works_now_and_for_what(self):
        rows = u.in_use(self.st)
        self.assertEqual([(r['key'], r['what']) for r in rows], [
            ('flow:ar', 'Clip 3 de BANANITO'), ('site:chatgpt', 'Planche 7 de BANANITO'), ('engine:grok:grok.one@example.com', 'Clip 4 de BANANITO')])
        self.assertEqual((rows[0]['number'], rows[0]['credits'], rows[0]['short']), (2, 38, 'Clip 3'))
        self.assertEqual(rows[2]['email'], 'grok.one@example.com')

    def test_last_used_is_kept_per_account(self):
        for t in self.st['tasks']:
            u.touch(self.st, t, 1000.0)
        self.assertEqual(self.st['last_used'], {'flow:ar': 1000.0, 'site:chatgpt': 1000.0, 'engine:grok:grok.one@example.com': 1000.0, 'site:claude': 1000.0})

    def test_labels_and_ai_text(self):
        self.assertEqual(u.what({'slot': 'script'}), 'Scénario')
        self.assertEqual(u.ai_text(self.st, self.st['tasks'][0]), 'Flow · compte 2 (ar•••@example.com, 38 crédits)')
        self.assertEqual(u.ai_text(self.st, self.st['tasks'][1]), 'ChatGPT')
        self.assertEqual(u.ai_text(self.st, self.st['tasks'][2]), 'Grok · gr•••e@example.com')
        self.assertEqual(u.claim_line(self.st, self.st['tasks'][1]), 'En cours : Planche 7 · IA : ChatGPT.')

    def test_switch_line(self):
        empty, next_one = flow('one', 2, number=2), flow('three', 38, number=3)
        self.assertEqual(u.switch_line(empty, next_one), 'Compte Flow 2 (on•••@example.com, 2 crédits, vide) → compte 3 (th•••e@example.com, 38 crédits) ; clips reçus conservés.')
        self.assertIn('sans accès à Flow', u.switch_line({**empty, 'blocked': 'unavailable'}, next_one))


class ReceivedClip(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def job(self):
        j = {'id': s.uid(), 'title': 'T', 'stage': 'clips', 'status': 'running', 'events': [], 'characters': [], 'config': {'scene_count': 2, 'flow_cost': 12},
             'scenes': [{'image': 'i.png', 'dialogue': [], 'video_prompt': 'p'} for _ in range(2)]}  # one clip left: no montage
        s.STATE['jobs'].append(j); return j

    def deliver(self, j, t):
        (s.job_dir(j) / 'c.mp4').write_bytes(b'clip'); t['status'] = 'claimed'; s.STATE['tasks'].append(t)
        s.accept_task_result(t, {'ok': True, 'file': 'c.mp4'})

    def test_flow_clip_keeps_its_account(self):
        s.STATE['profiles'] = [flow('ar', 38, number=2)]; j = self.job()
        self.deliver(j, {'id': 't', 'job': j['id'], 'kind': 'flow_video', 'profile': 'ar', 'slot': 'clip:0', 'payload': {'cost': 12}})
        self.assertEqual((j['scenes'][0]['engine'], j['scenes'][0]['account']), ('flow', {'profile': 'ar', 'email': 'ar@example.com'}))

    def test_grok_clip_keeps_its_account(self):
        j = self.job()
        self.deliver(j, {'id': 't', 'job': j['id'], 'kind': 'engine_video', 'slot': 'clip:0', 'payload': {'engine': 'grok', 'account': {'email': 'g@example.com'}}})
        self.assertEqual((j['scenes'][0]['engine'], j['scenes'][0]['account']), ('grok', {'email': 'g@example.com'}))

    def test_public_state_numbers_accounts(self):
        s.STATE['profiles'] = [flow('aa', 10), flow('bb', 50)]
        view = s.public_state()
        self.assertEqual([p['number'] for p in view['profiles']], [2, 1])
        self.assertEqual(view['usage'], {'in_use': [], 'last_used': {}})


if __name__ == '__main__':
    unittest.main()


class SwitchReason(unittest.TestCase):
    def test_account_left_with_credits_is_not_called_empty(self):
        import account_usage as u
        rich = {'number': 1, 'flow_email': 'one@example.com', 'balance': 50, 'readiness': {'state': 'fix'}}
        nxt = {'number': 10, 'flow_email': 'two@example.com', 'balance': 38}
        line = u.switch_line(rich, nxt, 30)
        self.assertIn('50 crédits, à régler', line); self.assertNotIn('vide', line)
        self.assertIn('moins de 30 crédits', u.switch_line({**rich, 'balance': 14, 'readiness': {}}, nxt, 30))
