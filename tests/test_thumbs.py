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


if __name__ == '__main__':
    unittest.main()
