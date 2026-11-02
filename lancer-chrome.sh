#!/usr/bin/env bash
# Dedicated Chrome profile with this copy's extension. Your accounts stay in this profile.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
profile="${FRUCHT_CHROME_PROFILE:-$HOME/.config/fruchtdrama-chrome-debug}"
args=(--user-data-dir="$profile" --load-extension="$root/extension" --no-first-run --no-default-browser-check)
[[ "${FRUCHT_CHROME_DEBUG:-0}" == 1 ]] && args+=(--remote-debugging-port=9222)  # diagnostics only, local
nohup google-chrome "${args[@]}" "$@" >/dev/null 2>&1 &
