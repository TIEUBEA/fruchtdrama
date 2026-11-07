"""Le Filon: research-only refresh (manual or every 2 h), thumbnails restricted to the TikTok CDN."""
import importlib.util, json, os, pathlib, tempfile, threading, time, unittest, urllib.request

ROOT = pathlib.Path(__file__).parents[1]
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_filon', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)

ROWS = [{'url': f'https://www.tiktok.com/@a/video/{i}', 'title': 'KI Früchte', 'views': 1000 * (i + 1), 'thumb': f'https://p16-sign.tiktokcdn-us.com/img{i}.jpeg'} for i in range(4)] + \
       [{'url': 'https://www.tiktok.com/@b/video/99', 'title': 'x', 'views': 5, 'thumb': 'https://evil.example/tracker.png'}]


class FilonTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()

    def test_refresh_is_research_only(self):
        j = s.filon_refresh()
        self.assertTrue(j['filon_only']); self.assertEqual(s.STATE['tasks'][-1]['kind'], 'tiktok_search')
        with self.assertRaisesRegex(ValueError, 'déjà en cours'):
            s.filon_refresh()
        s.apply_research(j, ROWS)
        self.assertEqual(j['status'], 'done'); self.assertEqual(len(j['candidates']), 5)
        self.assertEqual([t for t in s.STATE['tasks'] if t['status'] == 'queued' and t['kind'] != 'tiktok_search'], [], 'no story started')
        thumbs = {c['url'][-2:]: c['thumb'] for c in j['candidates']}
        self.assertTrue(thumbs['/3'].startswith('https://p16-sign.tiktokcdn-us.com/')); self.assertIsNone(thumbs['99'], 'foreign host dropped')
        self.assertTrue(s.STATE['settings']['filon_refreshed'])

    def test_automatic_every_two_hours(self):
        self.assertIsNone(s.filon_tick(), 'off by default')
        s.STATE['settings']['filon_auto'] = True
        self.assertIsNotNone(s.filon_tick()); self.assertIsNone(s.filon_tick(), 'not twice')
        s.STATE['jobs'][-1]['status'] = 'done'
        self.assertIsNone(s.filon_tick(time.time() + 3600)); self.assertIsNotNone(s.filon_tick(time.time() + 2 * 3600 + 5))

    def test_http(self):
        http = s.http.server.ThreadingHTTPServer(('127.0.0.1', 0), s.Handler); s.PORT = http.server_port; base = f'http://127.0.0.1:{s.PORT}'
        threading.Thread(target=http.serve_forever, daemon=True).start()
        try:
            r = urllib.request.Request(base + '/api/filon', data=json.dumps({'auto': True, 'refresh': True}).encode(), headers={'Origin': base, 'Content-Type': 'application/json'})
            state = json.load(urllib.request.urlopen(r))
            self.assertTrue(state['settings']['filon_auto']); self.assertTrue(any(j.get('filon_only') for j in state['jobs']))
        finally:
            http.shutdown(); http.server_close()


if __name__ == '__main__':
    unittest.main()
