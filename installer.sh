#!/usr/bin/env bash
# Linux installation (equivalent of Installer.cmd).
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"
[[ -x .venv/bin/python ]] || python3 -m venv .venv
exec .venv/bin/python installer.py
