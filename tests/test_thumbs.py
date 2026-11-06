"""Le Filon covers: read from the public video page, cached, failures remembered, links checked."""
import json, pathlib, sys, tempfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import thumbs

URL = 'https://www.tiktok.com/@oma/video/7689550752078908705'
JPEG = b'\xff\xd8\xff' + b'0' * 50


class ThumbTests(unittest.TestCase):
    def test_cover_from_page_then_cache(self):
        calls = []
        def fetch(u, timeout=8):
            calls.append(u)
            if 'tiktokcdn' in u:
                return JPEG, 'image/jpeg'
            return ('<script>{"cover":"https:\\u002F\\u002Fp16-common-sign.tiktokcdn.com\\u002Fa.jpg?x=1"}</script>').encode(), 'text/html'
        d = tempfile.mkdtemp()
        p = thumbs.get(URL + '?lang=fr', d, fetch)
        self.assertTrue(p.is_file()); self.assertEqual(calls[0], URL); self.assertEqual(calls[1], 'https://p16-common-sign.tiktokcdn.com/a.jpg?x=1')
        thumbs.get(URL, d, fetch); self.assertEqual(len(calls), 2, 'served from cache')

    def test_untrusted_host_and_failure_cached(self):
        calls = []
        def fetch(u, timeout=8):
            calls.append(u); return b'{"cover":"https://evil.test/a.jpg"}', 'text/html'
        d = tempfile.mkdtemp()
        self.assertIsNone(thumbs.get(URL, d, fetch)); self.assertIsNone(thumbs.get(URL, d, fetch))
        self.assertEqual(len(calls), 1, 'failure remembered')
        with self.assertRaises(ValueError):
            thumbs.get('https://evil.test/@a/video/123456', d, fetch)
        with self.assertRaises(ValueError):
            thumbs.get('file:///etc/passwd', d, fetch)


class FigureTests(unittest.TestCase):
    def test_page_figures_history_and_growth(self):
        item = {'id': '7689550752078908705', 'desc': 'Une fraise #fruitstory', 'createTime': '1000', 'textLanguage': 'fr',
                'statsV2': {'playCount': '10000', 'diggCount': '600', 'commentCount': '30', 'shareCount': '20', 'collectCount': '5'},
                'video': {'duration': 75, 'originCover': 'https://p16-sign.tiktokcdn.com/c.jpg'},
                'author': {'uniqueId': 'oma', 'nickname': 'Oma', 'avatarThumb': 'https://p16-sign.tiktokcdn.com/a.jpg'}, 'authorStatsV2': {'followerCount': '557700'}}
        views = [10000]
        def fetch(u, timeout=8):
            if 'tiktokcdn' in u:
                return JPEG, 'image/jpeg'
            item['statsV2']['playCount'] = str(views[0])
            data = {'__DEFAULT_SCOPE__': {'webapp.video-detail': {'itemInfo': {'itemStruct': item}}}}
            return ('<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">' + json.dumps(data) + '</script>').encode(), 'text/html'
        d = tempfile.mkdtemp(); clock = [1000 + 3600 * 10]
        m = thumbs.refresh(URL, d, fetch, lambda: clock[0])
        self.assertEqual((m['views'], m['duration'], m['account'], m['followers'], m['language']), (10000, 75, 'oma', 557700, 'fr'))
        self.assertTrue(thumbs.get(URL, d, fetch, lambda: clock[0], kind='avatar').is_file())
        views[0] = 13000; clock[0] += 1800
        self.assertEqual(thumbs.refresh(URL, d, fetch, lambda: clock[0])['views'], 10000, 'not re-read before 2 h')
        clock[0] += 7200
        thumbs.refresh(URL, d, fetch, lambda: clock[0])
        f = thumbs.all_figures(d, lambda: clock[0])['7689550752078908705']
        self.assertEqual(f['growth'], 3000); self.assertEqual(f['engagement'], round(650 / 13000 * 100, 1))
        self.assertEqual(f['per_hour'], round(13000 / ((clock[0] - 1000) / 3600)))


if __name__ == '__main__':
    unittest.main()
