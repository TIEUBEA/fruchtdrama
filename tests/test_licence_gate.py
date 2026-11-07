"""Consultation only is enforced by the studio itself, not only by the screen."""
import importlib.util, os, pathlib, sys, tempfile, unittest
from unittest import mock

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
TEMP = tempfile.TemporaryDirectory()
os.environ['FRUCHT_DATA'] = TEMP.name
SPEC = importlib.util.spec_from_file_location('studio_licence_gate', ROOT / 'server.py')
s = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(s)


class GateTests(unittest.TestCase):
    def job(self):
        return {'id': 'j1', 'status': 'running', 'stage': 'ideas', 'config': {'provider': 'chatgpt'}, 'events': [], 'scenes': []}

    def test_free_edition_is_untouched(self):
        self.assertTrue(s.LICENCE.allowed())
        self.assertEqual(s.public_state()['licence']['mode'], 'free')

    def test_consultation_only_blocks_new_work(self):
        blocked = {'mode': 'expired', 'allowed': False, 'message': 'Ton accès de 3 mois est terminé.'}
        with mock.patch.object(s.LICENCE, 'view', return_value=blocked):
            j = self.job()
            with mock.patch.object(s, 'add_task') as add:
                s.schedule(j)
                add.assert_not_called()
            with mock.patch.object(s.threading, 'Thread') as thread:
                s.start_render('j1')
                thread.assert_not_called()
            with self.assertRaisesRegex(ValueError, 'Consultation seule'):
                s.LICENCE.require()
            self.assertEqual(s.public_state()['licence']['mode'], 'expired')


if __name__ == '__main__':
    unittest.main()
