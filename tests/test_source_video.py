"""Refaire une virale: the TikTok video is fetched once and shown to the AI (frames + transcription)."""
import base64, io, json, pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
import source_video as sv


def page(video):
    data = {'__DEFAULT_SCOPE__': {'webapp.video-detail': {'itemInfo': {'itemStruct': {'desc': 'Une pomme ment', 'video': video, 'author': {'uniqueId': 'oma'}}}}}}
    return ('<html><script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">' + json.dumps(data) + '</script></html>').encode()


class FakeOpener:
    def __init__(self, replies):
        self.replies, self.seen = list(replies), []

    def open(self, request, timeout=0):
        self.seen.append((request.full_url, dict(request.header_items())))
        return io.BytesIO(self.replies.pop(0))


class SourceVideoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.dest = pathlib.Path(self.tmp.name) / 'source.mp4'

    def test_download_with_page_session(self):
        mp4 = b'\x00\x00\x00\x18ftypmp42' + b'0' * 100
        op = FakeOpener([page({'playAddr': 'https://v16-webapp-prime.tiktok.com/video/x', 'duration': 24}), mp4])
        info = sv.download('https://www.tiktok.com/@oma/video/1', self.dest, op)
        self.assertEqual(info, {'desc': 'Une pomme ment', 'duration': 24, 'account': 'oma'})
        self.assertEqual(self.dest.read_bytes(), mp4)
        self.assertEqual(op.seen[1][1].get('Referer'), 'https://www.tiktok.com/', 'same session, TikTok referer')

    def test_refusals(self):
        cases = [([b'<html>nothing</html>'], 'illisible'),
                 ([page({'playAddr': 'https://evil.example/x.mp4', 'duration': 24})], 'inattendue'),
                 ([page({'playAddr': 'https://v16-webapp-prime.tiktok.com/v', 'duration': 900})], 'trop longue'),
                 ([page({'playAddr': 'https://v16-webapp-prime.tiktok.com/v', 'duration': 20}), b'<html>blocked</html>'], 'pas renvoyé')]
        for replies, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                sv.download('https://www.tiktok.com/@oma/video/1', self.dest, FakeOpener(replies))

    def test_captures(self):
        png = b'\x89PNG\r\n\x1a\n' + b'0' * 10
        jpg = base64.b64encode(b'\xff\xd8\xff' + b'1' * 5).decode()
        decoded = sv.decode_captures([{'data': 'data:image/png;base64,' + base64.b64encode(png).decode()}, jpg])
        self.assertEqual([e for e, _ in decoded], ['png', 'jpg'])
        self.assertEqual(len(sv.decode_captures([jpg] * 6)), 4, '4 captures at most')
        with self.assertRaisesRegex(ValueError, 'illisible'):
            sv.decode_captures([{'data': base64.b64encode(b'GIF89a').decode()}])
        with self.assertRaisesRegex(ValueError, 'trop lourde'):
            sv.decode_captures([base64.b64encode(b'\xff\xd8\xff' + b'0' * sv.CAPTURE_BYTES).decode()])
        names = sv.save_captures(decoded, pathlib.Path(self.tmp.name))
        self.assertEqual(names, ['source_capture_1.png', 'source_capture_2.jpg'])

    def test_guidance(self):
        a = {'desc': 'Une pomme ment', 'board': 'source_board.jpg', 'transcript': '[00:01] Menteuse !'}
        identical = sv.guidance('identical', a, 1)
        self.assertIn('RECRÉER À L’IDENTIQUE', identical); self.assertIn('Menteuse', identical); self.assertIn('1 capture(s)', identical)
        self.assertIn('Inspiration seulement', sv.guidance('inspired', a))
        self.assertIn('seul son lien est connu', sv.guidance('inspired', {}))


if __name__ == '__main__':
    unittest.main()
