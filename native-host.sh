#!/usr/bin/env bash
# Chrome native host (Linux/macOS): the extension starts the studio through this script.
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
py="$root/.venv/bin/python"; [[ -x "$py" ]] || py=python3
exec "$py" "$root/native_host.py" "$@"
