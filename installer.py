"""Install dependencies in this copy only; never copies browser data."""
import pathlib
import shutil
import subprocess
import sys
from distribution import accept_terms

ROOT = pathlib.Path(__file__).resolve().parent


def main():
    if sys.version_info < (3, 10) or sys.version_info >= (3, 14):
        raise RuntimeError('Installez Python 3.11 ou 3.12 64 bits, puis relancez Installer.cmd.')
    if pathlib.Path(sys.executable).resolve().parent != (ROOT / '.venv' / 'Scripts').resolve():
        raise RuntimeError('Utilisez Installer.cmd pour installer dans l environnement separe de cette copie.')
    accept_terms()
    missing = [name for name in ('ffmpeg', 'ffprobe') if not shutil.which(name)]
    if missing:
        print('\nFFmpeg / ffprobe manquant. Installez FFmpeg, puis fermez cette fenetre et relancez Installer.cmd.')
        print('Commande Windows proposee (a executer vous-meme) : winget install --id Gyan.FFmpeg --exact')
        raise SystemExit(1)
    for requirements in ('requirements.txt', 'requirements-quality.txt'):
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(ROOT / requirements)], check=True)
    subprocess.run([sys.executable, str(ROOT / 'quality_setup.py')], check=True, cwd=ROOT)
    (ROOT / '.installation-complete').write_text('0.1.58\n', 'utf-8')
    print('\nInstallation terminee. Lancez Lancer-Studio.cmd, puis configurez VOS comptes dans Connexions.')


if __name__ == '__main__':
    main()
