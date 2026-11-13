"""05/11/2026: a running episode that does not move says why (owner: « savoir pourquoi la vidéo ne progresse pas »)."""
import datetime as dt, importlib.util, os, pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_stall', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


def iso(minutes_ago):
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)).isoformat()


def setup(kind='chat_collect', status='claimed', seen=0, claimed=1, event=1):
    s.STATE = s.fresh()
    j = {'id': s.uid(), 'title': 'T', 'stage': 'script', 'status': 'running', 'events': [{'at': iso(event), 'text': 'x'}], 'config': {'provider': 'chatgpt'}}
    s.STATE['jobs'].append(j); s.STATE['clients']['w1'] = {'label': 'Fenêtre', 'seen': iso(seen), 'role': 'all'}
    t = {'id': s.uid(), 'job': j['id'], 'kind': kind, 'slot': 'script', 'status': status, 'client': 'w1' if status == 'claimed' else None,
         'claimed': iso(claimed), 'created': iso(claimed), 'payload': {'provider': 'chatgpt'}}
    s.STATE['tasks'].append(t)
    return j, t


class StallTests(unittest.TestCase):
    def test_moving_episode_is_not_blocked(self):
        j, _ = setup(); self.assertIsNone(s.stall_info(j))

    def test_window_gone_is_said_with_its_time(self):
        j, _ = setup(seen=40, claimed=42, event=41)
        info = s.stall_info(j)
        self.assertIn('ne répond plus depuis', info['reason']); self.assertTrue(info['retry']); self.assertFalse(info['paid'])

    def test_no_window_open_for_a_queued_step(self):
        j, _ = setup(status='queued', seen=30)
        self.assertIn('Aucune fenêtre FruchtDrama', s.stall_info(j)['reason'])

    def test_silence_too_long_with_the_window_online(self):
        j, _ = setup(kind='chat_text', seen=0, claimed=30, event=20)
        self.assertIn('Aucune nouvelle de ChatGPT depuis 20 min', s.stall_info(j)['reason'])

    def test_retry_drops_the_stuck_task_and_asks_again(self):
        import json, threading, urllib.request, urllib.error
        http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = http.server_port
        threading.Thread(target=http.serve_forever, daemon=True).start(); base = f'http://127.0.0.1:{http.server_port}'
        def post(body):
            r = urllib.request.Request(base + '/api/job/' + j['id'], data=json.dumps(body).encode(), headers={'Origin': base, 'Content-Type': 'application/json'})
            try:return json.load(urllib.request.urlopen(r))
            except urllib.error.HTTPError as e:return json.load(e)
        try:
            j, t = setup(seen=40, claimed=42, event=41)
            calls = []; previous = s.schedule; s.schedule = lambda job: calls.append(job['id'])
            try:post({'action': 'retry_step'})
            finally:s.schedule = previous
            self.assertEqual(t['status'], 'failed'); self.assertEqual(calls, [j['id']]); self.assertIn('Étape relancée', j['events'][-1]['text'])
            j, t = setup(kind='flow_video', seen=40, claimed=42, event=41)
            t['progress'] = 'Import de la planche dans Flow…'; t['progress_at'] = t['claimed']  # started: credits may be at stake
            self.assertIn('vérifie dans Flow', post({'action': 'retry_step'}).get('error', '')); self.assertEqual(t['status'], 'claimed')
            j, _ = setup()
            self.assertIn('rien à relancer', post({'action': 'retry_step'}).get('error', ''))
        finally:
            http.shutdown()

    def test_paid_clip_is_flagged(self):
        j, _ = setup(kind='flow_video', seen=40, claimed=42, event=41)
        self.assertTrue(s.stall_info(j)['paid'])


if __name__ == '__main__':
    unittest.main()
