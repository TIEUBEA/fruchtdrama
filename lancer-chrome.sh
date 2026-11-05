#!/usr/bin/env bash
# Dedicated Chrome profile with this copy's extension. Your accounts stay in this profile.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
profile="${FRUCHT_CHROME_PROFILE:-$HOME/.config/fruchtdrama-chrome-debug}"
# The extension is installed once with chrome://extensions > "Load unpacked" (Chrome 137+ ignores --load-extension).
args=(--user-data-dir="$profile" --no-first-run --no-default-browser-check)
[[ "${FRUCHT_CHROME_DEBUG:-0}" == 1 ]] && args+=(--remote-debugging-port=9222)  # diagnostics only, local
nohup google-chrome "${args[@]}" "$@" >/dev/null 2>&1 &
