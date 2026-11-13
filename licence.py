"""FruchtDrama access key (paid course): 3 months from the first activation, 2 computers per key.

The key server (project fruchtdrama-licences) answers with a token signed by its RSA private key; this
module only holds the public key and checks the signature with the standard library (no dependency).
After the end, a revocation or 3 days without reaching the server, the studio is in "consultation
only": every production can still be opened and downloaded, nothing new is made, nothing is deleted.
Sent to the key server: the key, an anonymous fingerprint of this computer, its name and the version.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import uuid

# Off in the testers' zip; switched on in the trainees' edition once the key server is online.
REQUIRED = False
URL = os.environ.get('FRUCHT_LICENCE_URL', 'https://fruchtdrama-licences.vercel.app/api/v1/licence')
# Public half of the key server's signing key (hex modulus, exponent 65537). Set at deployment.
PUBLIC_MODULUS_HEX = ''
PUBLIC_EXPONENT = 65537
GRACE_DAYS = 3        # without internet, the studio keeps working this long after the last check
WARN_DAYS = 7         # banner before the end
CHECK_HOURS = 24      # a fresh verdict is asked once a day
ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
# DER prefix of a SHA-256 DigestInfo (PKCS#1 v1.5 signatures).
_DIGEST_INFO = bytes.fromhex('3031300d060960864801650304020105000420')
_LOCK = threading.Lock()

MESSAGES = {
    'needs_key': 'Entre ta clé FruchtDrama pour commencer.',
    'expired': 'Ton accès de 3 mois est terminé : tes vidéos restent consultables et téléchargeables. Contacte ton formateur pour le prolonger.',
    'revoked': 'Cette clé a été désactivée par ton formateur : tes vidéos restent consultables. Contacte-le.',
    'offline': 'Le studio n’a pas pu vérifier ta clé depuis plus de 3 jours : connecte-toi à internet, puis clique « Vérifier maintenant ».',
    'clock': 'La date de ton ordinateur semble fausse : corrige-la (réglage automatique), puis clique « Vérifier maintenant ».',
}


def _b64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))


def normalize_key(text: str) -> str | None:
    raw = re.sub(r'[^0-9A-Z]', '', str(text).upper())
    body = raw[2:] if raw.startswith('FD') else raw
    if len(body) != 16 or any(c not in ALPHABET for c in body):
        return None
    return 'FD-' + '-'.join(body[i:i + 4] for i in range(0, 16, 4))


def machine_id() -> str:
    """Anonymous, stable fingerprint of this computer (never the raw identifier)."""
    raw = ''
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography', 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                raw = str(winreg.QueryValueEx(k, 'MachineGuid')[0])
        except OSError:
            raw = ''
    elif sys.platform == 'darwin':
        # Mac (owner 11/11/2026, migration): the hardware UUID never changes, unlike the network card fallback.
        try:
            out = subprocess.run(['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'], capture_output=True, text=True, timeout=10).stdout
            found = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', out)
            raw = found[1] if found else ''
        except (OSError, subprocess.SubprocessError):
            raw = ''
    else:
        for path in ('/etc/machine-id', '/var/lib/dbus/machine-id'):
            try:
                raw = pathlib.Path(path).read_text().strip()
                break
            except OSError:
                continue
    raw = raw or str(uuid.getnode())
    return hashlib.sha256(('fruchtdrama:' + raw).encode()).hexdigest()


def verify(token: str, modulus_hex: str | None = None) -> dict | None:
    """Payload of a token signed by the key server, or None if the signature does not match."""
    modulus_hex = PUBLIC_MODULUS_HEX if modulus_hex is None else modulus_hex
    try:
        body, sig = token.split('.')
        n = int(modulus_hex, 16)
        size = (n.bit_length() + 7) // 8
        signature = _b64(sig)
        if len(signature) != size:
            return None
        em = pow(int.from_bytes(signature, 'big'), PUBLIC_EXPONENT, n).to_bytes(size, 'big')
        digest = hashlib.sha256(body.encode()).digest()
        expected = b'\x00\x01' + b'\xff' * (size - 3 - len(_DIGEST_INFO) - len(digest)) + b'\x00' + _DIGEST_INFO + digest
        if not hmac.compare_digest(em, expected):
            return None
        payload = json.loads(_b64(body))
        return payload if isinstance(payload, dict) and payload.get('v') == 1 else None
    except (ValueError, TypeError, AttributeError):
        return None


class Licence:
    def __init__(self, data_dir: pathlib.Path, version: str, post=None, clock=None, machine=None, modulus_hex=None):
        self.file = pathlib.Path(data_dir) / 'licence.json'
        self.version = version
        self._post = post or _post
        self._clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self._machine = machine or machine_id()
        self._modulus = modulus_hex

    # --- stored state (data/licence.json, never shared) ---
    def _load(self) -> dict:
        try:
            data = json.loads(self.file.read_text('utf-8'))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self, data: dict) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
        os.replace(tmp, self.file)

    # --- what the studio may do ---
    def view(self, required: bool | None = None) -> dict:
        if not (REQUIRED if required is None else required):
            return {'mode': 'free', 'allowed': True}
        data = self._load()
        hint = data.get('key', '')[-4:]
        payload = verify(data.get('token', ''), self._modulus) if data.get('token') else None
        if not payload or payload.get('machine') != self._machine:
            return {'mode': 'needs_key', 'allowed': False, 'message': data.get('error') or MESSAGES['needs_key'], 'key_hint': hint}
        now = self._clock()
        expires = dt.datetime.fromisoformat(payload['expiresAt'].replace('Z', '+00:00'))
        checked = dt.datetime.fromisoformat(payload['checkedAt'].replace('Z', '+00:00'))
        base = {'holder': payload.get('holder', ''), 'expires_at': payload['expiresAt'], 'checked_at': payload['checkedAt'], 'key_hint': hint}
        if payload.get('status') == 'revoked':
            return {**base, 'mode': 'revoked', 'allowed': False, 'message': MESSAGES['revoked']}
        if payload.get('status') == 'expired' or now >= expires:
            return {**base, 'mode': 'expired', 'allowed': False, 'message': MESSAGES['expired']}
        if checked - now > dt.timedelta(days=1):
            return {**base, 'mode': 'clock', 'allowed': False, 'message': MESSAGES['clock']}
        if now - checked > dt.timedelta(days=GRACE_DAYS):
            return {**base, 'mode': 'offline', 'allowed': False, 'message': MESSAGES['offline']}
        days_left = max(0, -(-int((expires - now).total_seconds()) // 86400))  # rounded up: 89.9 days shows 90
        return {**base, 'mode': 'active', 'allowed': True, 'days_left': days_left, 'warn': days_left < WARN_DAYS}

    def allowed(self) -> bool:
        return self.view()['allowed']

    def require(self) -> None:
        """Raise before making anything new when the studio is in consultation only."""
        v = self.view()
        if not v['allowed']:
            raise ValueError('Consultation seule : ' + v['message'])

    # --- talking to the key server ---
    def _ask(self, key: str) -> tuple[int, dict]:
        return self._post(URL, {'key': key, 'machine': self._machine, 'label': platform.node()[:60] or 'Ordinateur', 'version': self.version})

    def activate(self, text: str) -> dict:
        key = normalize_key(text)
        if not key:
            raise ValueError('Clé mal saisie : elle ressemble à FD-XXXX-XXXX-XXXX-XXXX.')
        with _LOCK:
            status, body = self._ask(key)
            if status != 200 or not body.get('ok'):
                raise ValueError(body.get('message') or 'Clé refusée par le service des clés.')
            payload = verify(body.get('token', ''), self._modulus)
            if not payload or payload.get('machine') != self._machine:
                raise ValueError('Réponse du service des clés non reconnue : mettez FruchtDrama à jour.')
            self._save({'key': key, 'token': body['token']})
        return self.view(required=True)

    def refresh(self) -> bool:
        """Ask a fresh verdict. Network trouble keeps the current one (grace period); a refusal ends it."""
        with _LOCK:
            data = self._load()
            if not data.get('key'):
                return False
            try:
                status, body = self._ask(data['key'])
            except ValueError:
                return False
            if status == 200 and body.get('ok') and verify(body.get('token', ''), self._modulus):
                self._save({'key': data['key'], 'token': body['token']})
                return True
            if status in (403, 404):
                # Key unknown or its computer seat was freed by the trainer: enter a key again.
                self._save({'key': data['key'], 'error': body.get('message') or MESSAGES['needs_key']})
            return False

    def due(self) -> bool:
        payload = verify(self._load().get('token', ''), self._modulus) if self._load().get('token') else None
        if not payload:
            return bool(self._load().get('key'))
        checked = dt.datetime.fromisoformat(payload['checkedAt'].replace('Z', '+00:00'))
        return self._clock() - checked > dt.timedelta(hours=CHECK_HOURS)


def _post(url: str, body: dict) -> tuple[int, dict]:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=15) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except ValueError:
            return e.code, {}
    except (OSError, ValueError) as e:
        raise ValueError('Pas de connexion au service des clés : vérifie internet, puis réessaie.') from e
