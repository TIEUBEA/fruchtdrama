#!/usr/bin/env bash
# Chrome native host (Linux/macOS): the extension starts the studio through this script.
# Chrome starts this script with a minimal PATH: Homebrew's ffmpeg (Mac) must stay reachable for the studio.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
py="$root/.venv/bin/python"; [[ -x "$py" ]] || py=python3
exec "$py" "$root/native_host.py" "$@"
