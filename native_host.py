"""Chrome native messaging host: the FruchtDrama extension asks it to start the local studio.

Protocol (Chrome): one message = 4-byte little-endian length + UTF-8 JSON, on stdin/stdout.
Commands: {"cmd": "ping"} and {"cmd": "start"}. Nothing else is ever printed on stdout.
"""
import json
import pathlib
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parent


def read(stream):
    head = stream.read(4)
    if len(head) < 4:
        return None
    size = struct.unpack('<I', head)[0]
    if size > 1024 * 1024:
        raise ValueError('Message trop long')
    return json.loads(stream.read(size).decode('utf-8'))


def write(stream, message):
    body = json.dumps(message, ensure_ascii=False).encode('utf-8')
    stream.write(struct.pack('<I', len(body)) + body)
    stream.flush()


def handle(message, start=None, accepted=None, installed=None):
    import distribution
    import launcher
    start = start or (lambda: launcher.start_server(detached=True))
    accepted = accepted if accepted is not None else distribution.terms_accepted()
    installed = installed if installed is not None else (ROOT / '.installation-complete').is_file()
    cmd = (message or {}).get('cmd')
    if cmd == 'ping':
        return {'ok': True, 'installed': installed and accepted}
    if cmd != 'start':
        return {'ok': False, 'error': 'Commande inconnue'}
    if not installed or not accepted:
        return {'ok': False, 'error': 'Installation à terminer : lancez une fois Installer.cmd (Windows) ou installer.sh (Linux) dans le dossier FruchtDrama.'}
    try:
        start()
    except (RuntimeError, OSError) as e:
        return {'ok': False, 'error': str(e)}
    return {'ok': True}


def main():
    stdin, stdout = sys.stdin.buffer, sys.stdout.buffer
    sys.stdout = sys.stderr  # any stray print would corrupt the Chrome channel
    try:
        reply = handle(read(stdin))
    except Exception as e:  # the extension must always get an answer
        reply = {'ok': False, 'error': f'Hôte FruchtDrama : {e}'}
    write(stdout, reply)


if __name__ == '__main__':
    main()
