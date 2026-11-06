"""Access key: signed verdicts verified offline, 3-day grace, consultation only after the end."""
import base64, datetime as dt, json, pathlib, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
import licence

NOW = dt.datetime(2026, 11, 4, 10, tzinfo=dt.timezone.utc)
MACHINE = 'a' * 64
KEY = 'FD-7K2M-Q9XA-4TPE-H3WZ'


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


@unittest.skipUnless(shutil.which('openssl'), 'openssl absent')
class LicenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pem = pathlib.Path(cls.tmp.name) / 'k.pem'
        subprocess.run(['openssl', 'genrsa', '-out', str(cls.pem), '2048'], check=True, capture_output=True)
        out = subprocess.run(['openssl', 'rsa', '-in', str(cls.pem), '-noout', '-modulus'], check=True, capture_output=True, text=True).stdout
        cls.modulus = out.strip().split('=')[1]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def token(self, status='active', expires=NOW + dt.timedelta(days=90), checked=NOW, machine=MACHINE):
        body = b64(json.dumps({'v': 1, 'licence': 'L1', 'machine': machine, 'holder': 'Awa', 'status': status,
                               'expiresAt': expires.isoformat().replace('+00:00', 'Z'), 'checkedAt': checked.isoformat().replace('+00:00', 'Z')}).encode())
        sig = subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(self.pem)], input=body.encode(), check=True, capture_output=True).stdout
        return body + '.' + b64(sig)

    def make(self, replies=None, now=NOW):
        self.data = tempfile.TemporaryDirectory(); self.addCleanup(self.data.cleanup)
        self.sent = []; self.replies = list(replies or [])
        def post(url, body):
            self.sent.append(body)
            reply = self.replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply
        self.clock = [now]
        return licence.Licence(pathlib.Path(self.data.name), '0.1.70', post=post, clock=lambda: self.clock[0], machine=MACHINE, modulus_hex=self.modulus)

    def test_signature_is_checked(self):
        t = self.token()
        self.assertEqual(licence.verify(t, self.modulus)['holder'], 'Awa')
        body, sig = t.split('.')
        forged = b64(json.dumps({**licence.verify(t, self.modulus), 'expiresAt': '2099-01-01T00:00:00Z'}).encode())
        self.assertIsNone(licence.verify(forged + '.' + sig, self.modulus), 'an edited date breaks the signature')
        self.assertIsNone(licence.verify('nope', self.modulus))
        other = self.modulus[:-1] + ('1' if self.modulus[-1] != '1' else '3')
        self.assertIsNone(licence.verify(t, other), 'another server key is refused')

    def test_free_edition_never_asks(self):
        self.assertEqual(self.make().view(required=False), {'mode': 'free', 'allowed': True})

    def test_activation_then_active(self):
        lic = self.make([(200, {'ok': True, 'token': self.token()})])
        self.assertEqual(lic.view(required=True)['mode'], 'needs_key')
        v = lic.activate(' fd 7k2m q9xa 4tpe h3wz ')
        self.assertEqual(self.sent[0]['key'], KEY); self.assertEqual(self.sent[0]['machine'], MACHINE)
        self.assertEqual((v['mode'], v['allowed'], v['days_left'], v['warn']), ('active', True, 90, False))
        self.assertNotIn(KEY, json.dumps(v), 'the key is never shown back, only its last 4 symbols')
        self.assertEqual(v['key_hint'], 'H3WZ')

    def test_refusals_are_explained(self):
        lic = self.make([(403, {'ok': False, 'message': 'Cette clé est déjà utilisée sur 2 ordinateurs.'}), ValueError('Pas de connexion')])
        with self.assertRaisesRegex(ValueError, '2 ordinateurs'):
            lic.activate(KEY)
        with self.assertRaisesRegex(ValueError, 'connexion'):
            lic.activate(KEY)
        with self.assertRaisesRegex(ValueError, 'mal saisie'):
            lic.activate('FD-1234')
        self.assertEqual(self.sent.__len__(), 2)

    def test_token_for_another_computer_is_refused(self):
        lic = self.make([(200, {'ok': True, 'token': self.token(machine='b' * 64)})])
        with self.assertRaisesRegex(ValueError, 'non reconnue'):
            lic.activate(KEY)

    def test_end_of_access_is_consultation_only(self):
        lic = self.make([(200, {'ok': True, 'token': self.token(expires=NOW + dt.timedelta(days=5))})])
        lic.activate(KEY)
        self.assertTrue(lic.view(required=True)['warn'], 'banner a few days before the end')
        self.clock[0] = NOW + dt.timedelta(days=5)
        v = lic.view(required=True)
        self.assertEqual((v['mode'], v['allowed']), ('expired', False))
        self.assertIn('consultables', v['message'])

    def test_grace_without_internet_then_offline(self):
        lic = self.make([(200, {'ok': True, 'token': self.token()}), ValueError('réseau'), (200, {'ok': True, 'token': self.token(checked=NOW + dt.timedelta(days=4))})])
        lic.activate(KEY)
        self.clock[0] = NOW + dt.timedelta(days=2)
        self.assertTrue(lic.due()); self.assertFalse(lic.refresh(), 'network trouble keeps the verdict')
        self.assertEqual(lic.view(required=True)['mode'], 'active')
        self.clock[0] = NOW + dt.timedelta(days=4)
        self.assertEqual(lic.view(required=True)['mode'], 'offline')
        self.assertTrue(lic.refresh()); self.assertEqual(lic.view(required=True)['mode'], 'active')

    def test_revoked_or_seat_freed(self):
        lic = self.make([(200, {'ok': True, 'token': self.token()}), (200, {'ok': True, 'token': self.token(status='revoked')}),
                         (403, {'ok': False, 'message': 'Cette clé est déjà utilisée sur 2 ordinateurs.'})])
        lic.activate(KEY)
        lic.refresh(); self.assertEqual(lic.view(required=True)['mode'], 'revoked')
        lic.refresh()
        v = lic.view(required=True)
        self.assertEqual(v['mode'], 'needs_key'); self.assertIn('2 ordinateurs', v['message'])

    def test_clock_set_back_is_caught(self):
        lic = self.make([(200, {'ok': True, 'token': self.token()})])
        lic.activate(KEY)
        self.clock[0] = NOW - dt.timedelta(days=30)
        self.assertEqual(lic.view(required=True)['mode'], 'clock')

    def test_machine_id_is_anonymous(self):
        m = licence.machine_id()
        self.assertRegex(m, r'^[0-9a-f]{64}$'); self.assertEqual(m, licence.machine_id())


if __name__ == '__main__':
    unittest.main()
