"""The zip sent to trainees: everything needed to run, nothing private."""
import pathlib, re, shutil, subprocess, sys, tempfile, unittest, zipfile

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
import package


class PackageTests(unittest.TestCase):
    def test_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / 'f.zip'; package.build(out)
            names = zipfile.ZipFile(out).namelist()
        self.assertTrue(all(n.startswith('FruchtDrama/') for n in names), 'one top folder')
        for needed in ('Installer.cmd', 'installer.sh', 'server.py', 'launcher.py', 'native_host.py', 'native_setup.py', 'native-host.cmd',
                       'native-host.sh', 'extension/manifest.json', 'extension/studio-start.js', 'web/index.html', 'GUIDE-UTILISATEUR.pdf',
                       'INSTALLATION.md', 'CONDITIONS-UTILISATION.txt', 'requirements.txt'):
            self.assertIn('FruchtDrama/' + needed, names)
        for n in names:
            self.assertNotRegex(n, r'/(data|tests|sudf|guide)/|\.env|state\.json|ESSAI-REEL|package\.py$')

    def test_no_real_address(self):
        self.assertEqual(package.private_addresses(package.files()), {})
        leak = ROOT / 'zz_leak_probe.py'; leak.write_text("a='quelqu.un@gmail.com'; b='moi@gmail.com'")
        try:
            self.assertEqual(package.private_addresses(['zz_leak_probe.py']), {'zz_leak_probe.py': {'quelqu.un@gmail.com'}})
        finally:
            leak.unlink()

    @unittest.skipUnless(shutil.which('pdftotext'), 'pdftotext absent')
    def test_guide_pdf_has_no_account_name(self):
        text = subprocess.run(['pdftotext', str(ROOT / 'docs/GUIDE-UTILISATEUR.pdf'), '-'], capture_output=True, text=True).stdout
        self.assertNotRegex(text.lower(), r'arnaud|pkf|djoum|chewa')
        self.assertIn('0.1.85', text)


if __name__ == '__main__':
    unittest.main()
