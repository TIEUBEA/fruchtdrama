#!/bin/bash
# Mac : installation de FruchtDrama Studio (double-clic). Nécessite Python 3.11 à 3.13 et FFmpeg (Homebrew).
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
# Fichiers copiés depuis un autre ordinateur : macOS les met en quarantaine (les scripts et l'extension refuseraient de s'ouvrir).
xattr -dr com.apple.quarantine . 2>/dev/null
chmod +x ./*.command ./*.sh 2>/dev/null
PY=""
for c in python3.13 python3.12 python3.11 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  if command -v "$c" >/dev/null 2>&1 && [ "$("$c" -c 'import sys;print((3,11)<=sys.version_info[:2]<(3,14))' 2>/dev/null)" = "True" ]; then
    PY="$(command -v "$c")"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.11, 3.12 ou 3.13 est introuvable."
  echo "Installez-le vous-même (Homebrew) :  brew install python@3.12   puis relancez Installer-Mac.command."
  read -r -p "Appuyez sur Entrée pour fermer." _; exit 1
fi
echo "Python utilisé : $PY ($("$PY" --version))"
[ -x .venv/bin/python ] || "$PY" -m venv .venv || { echo "Création de l'environnement impossible."; read -r -p "Entrée pour fermer." _; exit 1; }
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python installer.py
status=$?
[ $status -eq 0 ] && echo "Installation terminée. Lancez ensuite Lancer-Studio-Mac.command."
read -r -p "Appuyez sur Entrée pour fermer." _
exit $status
