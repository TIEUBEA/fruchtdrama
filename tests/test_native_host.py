"""0.1.69: the extension starts the studio through a Chrome native host, wherever the folder is installed."""
import base64, hashlib, io, json, os, pathlib, struct, subprocess, sys, tempfile, unittest
from unittest import mock

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
import native_host, native_setup


def frame(message):
    body = json.dumps(message).encode()
    return struct.pack('<I', len(body)) + body


class ProtocolTests(unittest.TestCase):
    def test_round_trip(self):
        out = io.BytesIO(); native_host.write(out, {'ok': True, 'é': 1})
        self.assertEqual(native_host.read(io.BytesIO(out.getvalue())), {'ok': True, 'é': 1})
        self.assertIsNone(native_host.read(io.BytesIO(b'')))

    def test_start_needs_installation(self):
        called = []
        r = native_host.handle({'cmd': 'start'}, start=lambda: called.append(1), accepted=True, installed=False)
        self.assertFalse(r['ok']); self.assertIn('Installer.cmd', r['error']); self.assertEqual(called, [])
        r = native_host.handle({'cmd': 'start'}, start=lambda: called.append(1), accepted=False, installed=True)
        self.assertFalse(r['ok']); self.assertEqual(called, [])

    def test_start_runs_server_and_reports_failure(self):
        called = []
        self.assertEqual(native_host.handle({'cmd': 'start'}, start=lambda: called.append(1), accepted=True, installed=True), {'ok': True})
        self.assertEqual(called, [1])
        def busy(): raise RuntimeError('Port 8840 utilise par une autre installation.')
        r = native_host.handle({'cmd': 'start'}, start=busy, accepted=True, installed=True)
        self.assertFalse(r['ok']); self.assertIn('8840', r['error'])
        self.assertFalse(native_host.handle({'cmd': 'rm'}, accepted=True, installed=True)['ok'])

    def test_real_process_answers_on_stdout_only(self):
        p = subprocess.run([sys.executable, str(ROOT / 'native_host.py')], input=frame({'cmd': 'ping'}), capture_output=True, timeout=30, cwd=tempfile.gettempdir())
        size = struct.unpack('<I', p.stdout[:4])[0]
        self.assertEqual(len(p.stdout), 4 + size, 'nothing but the framed reply on stdout')
        self.assertTrue(json.loads(p.stdout[4:])['ok'])


class SetupTests(unittest.TestCase):
    def test_extension_id_comes_from_manifest_key(self):
        key = json.loads((ROOT / 'extension' / 'manifest.json').read_text('utf-8'))['key']
        digest = hashlib.sha256(base64.b64decode(key)).hexdigest()[:32]
        self.assertEqual(''.join(chr(ord('a') + int(c, 16)) for c in digest), native_setup.EXTENSION_ID)
        server = (ROOT / 'server.py').read_text('utf-8')
        self.assertIn(f"OFFICIAL_ORIGIN='chrome-extension://{native_setup.EXTENSION_ID}'", server)

    def test_manifest_points_into_this_folder(self):
        m = native_setup.manifest()
        self.assertEqual(m['name'], 'com.fruchtdrama.studio'); self.assertEqual(m['type'], 'stdio')
        self.assertTrue(pathlib.Path(m['path']).is_absolute()); self.assertEqual(pathlib.Path(m['path']).parent, ROOT)
        self.assertTrue(pathlib.Path(m['path']).is_file())
        self.assertEqual(m['allowed_origins'], [f'chrome-extension://{native_setup.EXTENSION_ID}/'])

    def test_unix_targets_only_existing_browsers(self):
        with tempfile.TemporaryDirectory() as home:
            h = pathlib.Path(home); (h / '.config' / 'google-chrome').mkdir(parents=True)
            t = native_setup.unix_targets(h, 'linux', {})
            self.assertEqual(t, [h / '.config/google-chrome/NativeMessagingHosts/com.fruchtdrama.studio.json'])
            (h / 'profil').mkdir()
            t = native_setup.unix_targets(h, 'linux', {'FRUCHT_CHROME_PROFILE': str(h / 'profil')})
            self.assertIn(h / 'profil/NativeMessagingHosts/com.fruchtdrama.studio.json', t, 'dedicated --user-data-dir profile')
            (h / 'Library/Application Support/Google/Chrome').mkdir(parents=True)
            self.assertEqual(native_setup.unix_targets(h, 'darwin', {}), [h / 'Library/Application Support/Google/Chrome/NativeMessagingHosts/com.fruchtdrama.studio.json'])

    @unittest.skipIf(os.name == 'nt', 'Unix registration')
    def test_register_writes_manifest(self):
        with tempfile.TemporaryDirectory() as home:
            target = pathlib.Path(home) / 'NativeMessagingHosts' / 'com.fruchtdrama.studio.json'
            with mock.patch.object(native_setup, 'unix_targets', return_value=[target]):
                self.assertEqual(native_setup.register(), [target])
            self.assertEqual(json.loads(target.read_text('utf-8'))['path'], str(ROOT / 'native-host.sh'))
            self.assertTrue(os.access(ROOT / 'native-host.sh', os.X_OK))

    def test_windows_wrapper_uses_this_copy(self):
        cmd = (ROOT / 'native-host.cmd').read_bytes()
        self.assertIn(b'"%~dp0.venv\\Scripts\\python.exe" "%~dp0native_host.py"', cmd); self.assertIn(b'\r\n', cmd)


if __name__ == '__main__':
    unittest.main()
