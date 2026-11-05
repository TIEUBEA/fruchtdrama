"""Install dependencies in this copy only; never copies browser data."""
import os
import pathlib
import shutil
import subprocess
import sys
from distribution import accept_terms
import native_setup

ROOT = pathlib.Path(__file__).resolve().parent


def main():
    if sys.version_info < (3, 10) or sys.version_info >= (3, 14):
        raise RuntimeError('Installez Python 3.11 ou 3.12 64 bits, puis relancez Installer.cmd.')
    venv = ROOT / '.venv' / ('Scripts' if os.name == 'nt' else 'bin')
    if pathlib.Path(sys.executable).parent.resolve() != venv.resolve():
        raise RuntimeError('Utilisez Installer.cmd (Windows) ou installer.sh (Linux) pour installer dans l environnement separe de cette copie.')
    accept_terms()
    missing = [name for name in ('ffmpeg', 'ffprobe') if not shutil.which(name)]
    if missing:
        print('\nFFmpeg / ffprobe manquant. Installez FFmpeg, puis fermez cette fenetre et relancez Installer.cmd.')
        print('Commande Windows proposee (a executer vous-meme) : winget install --id Gyan.FFmpeg --exact')
        raise SystemExit(1)
    for requirements in ('requirements.txt', 'requirements-quality.txt'):
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(ROOT / requirements)], check=True)
    subprocess.run([sys.executable, str(ROOT / 'quality_setup.py')], check=True, cwd=ROOT)
    (ROOT / '.installation-complete').write_text('0.1.85\n', 'utf-8')
    # The extension starts the studio by itself from now on (no window to keep open, survives a restart).
    places = native_setup.register()
    print('\nInstallation terminee. Chargez le dossier extension dans Chrome (chrome://extensions > Mode developpeur > Charger l extension non empaquetee),')
    print('puis cliquez l icone FruchtDrama : le studio demarre tout seul.' if places or os.name == 'nt' else 'puis lancez lancer-studio.sh (aucun Chrome trouve pour le demarrage automatique).')


if __name__ == '__main__':
    main()
