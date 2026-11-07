"""Atelier-like scene tools: board changed after its clip, redo those clips, edit a scene's words."""
import importlib.util, os, pathlib, sys, tempfile, unittest
from unittest import mock

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_scene_tools', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


class SceneTools(unittest.TestCase):
    def setUp(self):
        s.STATE = s.fresh()
        self.j = {'id': self.id().split('.')[-1][:24], 'title': 'T', 'status': 'done', 'stage': 'done', 'config': {'video_engine': 'flow'}, 'events': [],
                  'characters': [], 'scenes': [
                      {'image': 'b0.png', 'clip': 'c0.mp4', 'clip_from': 'b0.png', 'dialogue': [{'speaker': 'a', 'text': 'Bonjour maman'}]},
                      {'image': 'b1_new.png', 'clip': 'c1.mp4', 'clip_from': 'b1_old.png', 'dialogue': [{'speaker': 'a', 'text': 'Où est la lettre ?'}]},
                      {'image': 'b2.png', 'clip': 'c2.mp4', 'dialogue': []}]}
        s.STATE['jobs'].append(self.j)

    def test_board_changed_after_clip(self):
        self.assertEqual(s.stale_clips(self.j), [1], 'only a clip that knows its board, and whose board changed')

    def test_clip_remembers_its_board(self):
        j = self.j; j['scenes'][2].pop('clip'); j['status'] = 'running'; j['stage'] = 'clips'
        (s.job_dir(j) / 'c2b.mp4').write_bytes(b'x')
        s.accept_task_result({'job': j['id'], 'slot': 'clip:2'}, {'ok': True, 'file': 'c2b.mp4'})
        self.assertEqual(j['scenes'][2]['clip_from'], 'b2.png')

    def test_redo_stale_clips(self):
        with mock.patch.object(s, 'schedule') as sched:
            done = s.redo_clips(self.j, [])
        sched.assert_called_once_with(self.j)
        self.assertEqual(done, [1]); self.assertNotIn('clip', self.j['scenes'][1])
        self.assertIn('c1.mp4', [h['file'] for h in self.j['redo_history']], 'old clip kept for « Remettre »')
        self.assertEqual(self.j['scenes'][0]['clip'], 'c0.mp4', 'up-to-date clips untouched')
        with self.assertRaisesRegex(ValueError, 'Aucun clip'):
            s.redo_clips(self.j, [0])

    def test_edit_scene_words(self):
        s.edit_scene(self.j, 0, ['  Bonsoir   maman  '])
        self.assertEqual(self.j['scenes'][0]['dialogue'][0]['text'], 'Bonsoir maman')
        self.assertTrue(self.j['scenes'][0]['text_after_clip'], 'the clip still says the old words')
        for args, msg in (((5, ['x']), 'Scène inconnue'), ((0, ['a', 'b']), 'Une réplique par ligne'), ((0, ['  ']), 'vide'),
                          ((0, ['mot ' * 60]), 'Trop long')):
            with self.subTest(msg=msg), self.assertRaisesRegex(ValueError, msg):
                s.edit_scene(self.j, *args)


if __name__ == '__main__':
    unittest.main()
