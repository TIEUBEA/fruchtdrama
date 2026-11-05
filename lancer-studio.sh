#!/usr/bin/env bash
# Linux: start the local studio, then the dedicated Chrome. Click the pinned FruchtDrama icon:
# the FruchtDrama window opens and everything happens inside it.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"
FRUCHT_NO_BROWSER=1 "$root/.venv/bin/python" "$root/launcher.py"
exec "$root/lancer-chrome.sh"
