"""Migration to the owner's MacBook (11/11/2026): Mac-specific code paths and the migration archive."""
import json, pathlib, subprocess, sys, tempfile, unittest, unittest.mock, zipfile

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
import flow_accounts, licence, power, preparer_migration_mac as migration


class MacCodeTests(unittest.TestCase):
    def test_licence_uses_the_mac_hardware_uuid(self):
        out = '+-o IOPlatformExpertDevice\n  | "IOPlatformUUID" = "1234ABCD-0000-1111-2222-333344445555"\n'
        run = unittest.mock.Mock(return_value=subprocess.CompletedProcess([], 0, out, ''))
        with unittest.mock.patch.object(licence.os, 'name', 'posix'), unittest.mock.patch.object(licence.sys, 'platform', 'darwin'), \
                unittest.mock.patch.object(licence.subprocess, 'run', run):
            first = licence.machine_id()
        with unittest.mock.patch.object(licence.os, 'name', 'posix'), unittest.mock.patch.object(licence.sys, 'platform', 'darwin'), \
                unittest.mock.patch.object(licence.subprocess, 'run', run), unittest.mock.patch.object(licence.uuid, 'getnode', return_value=42):
            self.assertEqual(licence.machine_id(), first, 'stable: not the network card')
        self.assertEqual(run.call_args[0][0][:2], ['ioreg', '-rd1'])

    def test_mac_opens_a_chrome_profile_in_the_background(self):
        app = pathlib.Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        popen = unittest.mock.Mock()
        with unittest.mock.patch.object(flow_accounts.sys, 'platform', 'darwin'), \
                unittest.mock.patch.object(flow_accounts, 'chrome_executable', return_value=app), \
                unittest.mock.patch.object(flow_accounts.subprocess, 'Popen', popen):
            flow_accounts.launch({'flow_url': 'https://flow.google.com/u/1/project/abc', 'chrome_profile': 'Profile 2'})
        args = popen.call_args[0][0]
        self.assertEqual(args[:3], ['open', '-gna', '/Applications/Google Chrome.app'])
        self.assertIn('--profile-directory=Profile 2', args)

    def test_mac_keeps_awake_with_caffeinate(self):
        proc = unittest.mock.Mock(); proc.poll.return_value = None
        popen = unittest.mock.Mock(return_value=proc)
        power._caffeinate = None
        power.mac_awake(True, popen); power.mac_awake(True, popen)
        self.assertEqual(popen.call_count, 1, 'one caffeinate at a time')
        self.assertEqual(popen.call_args[0][0][:3], ['caffeinate', '-i', '-w'])
        power.mac_awake(False, popen)
        proc.terminate.assert_called_once()


class MigrationArchiveTests(unittest.TestCase):
    def state(self):
        return {'token': 't', 'pair_code': 'p', 'clients': {'c1': {'role': 'all'}}, 'bridge_requests': [{'type': 'scan_flow'}],
                'profiles': [{'id': 'p1', 'label': 'a@x.com', 'flow_email': 'a@x.com', 'balance': 50, 'flow_client': 'c1', 'chrome_profile': 'Profile 2',
                              'slot': 1, 'auto_enabled': True, 'readiness': {'state': 'no_access'}, 'flow_url': 'https://flow.google.com/u/1/project/x'}],
                'tasks': [{'id': 't1', 'status': 'claimed'}, {'id': 't2', 'status': 'done'}],
                'jobs': [{'id': 'j1', 'status': 'running', 'events': []}, {'id': 'j2', 'status': 'done', 'events': []}],
                'night': {'active': True, 'ids': ['j1']}}

    def test_state_for_mac_forgets_this_pc_only(self):
        original = self.state(); mac = migration.for_mac(original)
        self.assertEqual(original['clients'], {'c1': {'role': 'all'}}, 'the PC keeps its own state')
        self.assertEqual(mac['clients'], {}); self.assertEqual(mac['bridge_requests'], [])
        p = mac['profiles'][0]
        self.assertEqual((p['flow_email'], p['balance'], p['slot'], p['auto_enabled']), ('a@x.com', 50, None, False))
        self.assertNotIn('chrome_profile', p); self.assertNotIn('flow_client', p)
        self.assertEqual([t['status'] for t in mac['tasks']], ['cancelled', 'done'])
        self.assertEqual([j['status'] for j in mac['jobs']], ['paused', 'done'])
        self.assertFalse(mac['night']['active']); self.assertEqual(mac['token'], 't')

    def test_archives(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d); data = d / 'data'; (data / 'jobs' / 'j1').mkdir(parents=True)
            (data / 'state.json').write_text(json.dumps(self.state()), 'utf-8')
            (data / 'jobs' / 'j1' / 'final.mp4').write_bytes(b'video'); (data / 'server-errors.log').write_text('x')
            count, _ = migration.zip_data(d / 'data.zip', data=data)
            with zipfile.ZipFile(d / 'data.zip') as z:
                names = z.namelist(); state = json.loads(z.read('fruchtdrama-studio/data/state.json'))
            self.assertIn('fruchtdrama-studio/data/jobs/j1/final.mp4', names)
            self.assertNotIn('fruchtdrama-studio/data/server-errors.log', names)
            self.assertEqual(state['clients'], {})
            migration.zip_code(d / 'code.zip')
            with zipfile.ZipFile(d / 'code.zip') as z:
                names = z.namelist(); mode = z.getinfo('fruchtdrama-studio/Installer-Mac.command').external_attr >> 16
            self.assertIn('fruchtdrama-studio/extension/manifest.json', names)
            self.assertFalse(any('/.venv/' in n or '/data/' in n or '__pycache__' in n for n in names))
            self.assertTrue(mode & 0o111, 'the Mac scripts stay executable')
            self.assertNotIn(b'\r\n', (ROOT / 'Installer-Mac.command').read_bytes(), 'Unix line endings for the Mac')


if __name__ == '__main__':
    unittest.main()
