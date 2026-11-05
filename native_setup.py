"""Register this copy as the Chrome native host that lets the extension start the studio.

Works wherever the folder is unzipped: the paths are written at install (and at each launch, so a moved
folder heals itself). Only the current user's settings are touched: no administrator rights, no network.
"""
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
HOST = 'com.fruchtdrama.studio'
# Fixed by the "key" in extension/manifest.json: the same ID on every computer, wherever the folder is.
EXTENSION_ID = 'bhdmibhibonmaamgcbpmbhedhohfongj'
# Chromium browsers that load the extension (Chrome first). Windows registry keys under HKCU\Software.
WINDOWS_KEYS = ('Google\\Chrome', 'Chromium', 'Microsoft\\Edge', 'BraveSoftware\\Brave-Browser')
UNIX_DIRS = {
    'linux': ('google-chrome', 'google-chrome-beta', 'chromium', 'microsoft-edge', 'BraveSoftware/Brave-Browser'),
    'darwin': ('Google/Chrome', 'Chromium', 'Microsoft Edge', 'BraveSoftware/Brave-Browser'),
}


def manifest():
    program = ROOT / ('native-host.cmd' if os.name == 'nt' else 'native-host.sh')
    return {'name': HOST, 'description': 'FruchtDrama : démarre le studio local', 'path': str(program),
            'type': 'stdio', 'allowed_origins': [f'chrome-extension://{EXTENSION_ID}/']}


def unix_targets(home=None, platform=None, env=None):
    home = pathlib.Path(home or pathlib.Path.home()); platform = platform or sys.platform; env = os.environ if env is None else env
    base = home / ('Library/Application Support' if platform == 'darwin' else '.config')
    found = [base / d for d in UNIX_DIRS['darwin' if platform == 'darwin' else 'linux'] if (base / d).is_dir()]
    # A Chrome started with --user-data-dir reads hosts from that folder (lancer-chrome.sh).
    dedicated = pathlib.Path(env.get('FRUCHT_CHROME_PROFILE') or home / '.config' / 'fruchtdrama-chrome-debug')
    if dedicated.is_dir():
        found.append(dedicated)
    return [d / 'NativeMessagingHosts' / f'{HOST}.json' for d in found]


def register():
    """Write the host manifest where the browsers look for it. Returns the places written."""
    data = json.dumps(manifest(), ensure_ascii=False, indent=2)
    if os.name == 'nt':
        import winreg
        target = ROOT / 'data' / f'{HOST}.json'
        target.parent.mkdir(exist_ok=True)
        target.write_text(data, 'utf-8')
        for key in WINDOWS_KEYS:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f'Software\\{key}\\NativeMessagingHosts\\{HOST}') as k:
                winreg.SetValueEx(k, '', 0, winreg.REG_SZ, str(target))
        return [target]
    script = ROOT / 'native-host.sh'
    script.chmod(script.stat().st_mode | 0o111)  # a zip may lose the executable bit
    written = []
    for target in unix_targets():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, 'utf-8')
        written.append(target)
    return written


if __name__ == '__main__':
    places = register()
    print('Démarrage par l’extension activé.' if places else 'Aucun navigateur Chrome trouvé pour cet utilisateur.')
