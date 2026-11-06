"""« Remettre » (like the Atelier): an earlier board or clip of a scene comes back, nothing is lost."""
import importlib.util, os, pathlib, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_restore', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


class RestoreTests(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()
        self.j = {'id': 'r1', 'title': 'T', 'status': 'done', 'stage': 'done', 'config': {}, 'events': [], 'final': '/media/r1/final.mp4',
                  'scenes': [{'image': 'image_new.png', 'clip': 'clip_new.mp4'}],
                  'redo_history': [{'slot': 'image:0', 'file': 'image_old.png', 'note': 'trop sombre', 'at': '2026-11-04T10:00:00+00:00'},
                                   {'slot': 'clip:0', 'file': 'clip_old.mp4', 'note': '', 'at': '2026-11-04T10:05:00+00:00'}]}
        s.STATE['jobs'].append(self.j)
        d = s.job_dir(self.j)
        for f in ('image_new.png', 'image_old.png', 'clip_new.mp4', 'clip_old.mp4'):
            (d / f).write_bytes(b'x')

    def test_restore_swaps_and_keeps_both(self):
        s.restore_version(self.j, 'clip:0', 'clip_old.mp4')
        self.assertEqual(self.j['scenes'][0]['clip'], 'clip_old.mp4')
        self.assertIn('clip_new.mp4', [h['file'] for h in self.j['redo_history'] if h['slot'] == 'clip:0'], 'today’s clip kept')
        self.assertNotIn('clip_old.mp4', [h['file'] for h in self.j['redo_history']])
        self.assertTrue(self.j['montage_stale'], 'the final video must be remade to include it')
        s.restore_version(self.j, 'clip:0', 'clip_new.mp4')
        self.assertEqual(self.j['scenes'][0]['clip'], 'clip_new.mp4', 'and back again')
        s.restore_version(self.j, 'image:0', 'image_old.png')
        self.assertEqual(self.j['scenes'][0]['image'], 'image_old.png')

    def test_refusals(self):
        for slot, file, msg in (('cover', 'x.png', 'Seules'), ('clip:3', 'clip_old.mp4', 'Scène inconnue'),
                                ('clip:0', 'image_old.png', 'introuvable'), ('clip:0', '../state.json', 'introuvable')):
            with self.subTest(slot=slot, file=file), self.assertRaisesRegex(ValueError, msg):
                s.restore_version(self.j, slot, file)
        s.STATE['tasks'].append({'job': 'r1', 'slot': 'clip:0', 'status': 'claimed'})
        with self.assertRaisesRegex(ValueError, 'en cours de fabrication'):
            s.restore_version(self.j, 'clip:0', 'clip_old.mp4')
        self.assertEqual(self.j['scenes'][0]['clip'], 'clip_new.mp4', 'nothing changed')


if __name__ == '__main__':
    unittest.main()
