#!/bin/bash
# Mac : démarre le studio local puis ouvre Chrome sur le studio (double-clic).
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if [ ! -x .venv/bin/python ]; then echo "Lancez d'abord Installer-Mac.command."; read -r -p "Entrée pour fermer." _; exit 1; fi
FRUCHT_NO_BROWSER=1 .venv/bin/python launcher.py || { read -r -p "Entrée pour fermer." _; exit 1; }
open -a "Google Chrome" "http://127.0.0.1:8840" 2>/dev/null || open "http://127.0.0.1:8840"
