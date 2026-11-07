#!/usr/bin/env bash
# Launch the DEVELOPMENT copy of Sayri with the new Liquid Glass UI.
#
# Safety measures (the goal is to never touch the live session):
#   * runs from ~/Projects/sayri-liquid-glass, not /usr/share/sayri
#   * isolated config + state dirs, so no IPC with the running Sayri instance
#   * Wayland backend + Cairo renderer + software GL
#   * WebKit orb disabled by default (use --with-orb to enable it)
#   * optional auto-quit so a test cannot leave a stuck overlay behind
#
# Usage:
#   ./run-sayri-safe.sh                 # show the glass pill without WebKit
#   ./run-sayri-safe.sh --timeout 20    # auto-close after 20 seconds
#   ./run-sayri-safe.sh --with-orb      # also render the WebKit orb
#   ./run-sayri-safe.sh --logs          # keep the log in /tmp/opencode
set -euo pipefail

cd "$(dirname "$0")"

WITH_ORB=0
TIMEOUT_MS=""
SHOW_LOGS=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-orb) WITH_ORB=1; shift ;;
    --timeout)
      [[ $# -ge 2 ]] || { echo "--timeout needs a number of seconds" >&2; exit 2; }
      TIMEOUT_MS=$(( $2 * 1000 )); shift 2 ;;
    --logs) SHOW_LOGS=1; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

DEV_ROOT="$(pwd)"
DEV_CONFIG="${SAYRI_DEV_CONFIG_DIR:-$HOME/.config/sayri-dev}"
DEV_STATE="${SAYRI_DEV_STATE_DIR:-$HOME/.local/state/sayri-dev}"
mkdir -p "$DEV_CONFIG" "$DEV_STATE"
chmod 700 "$DEV_CONFIG" "$DEV_STATE"

# Reuse the user's settings (read-only copy) but never write the live config.
if [[ ! -f "$DEV_CONFIG/sayri.conf" && -f "$HOME/.config/sayri/sayri.conf" ]]; then
  cp "$HOME/.config/sayri/sayri.conf" "$DEV_CONFIG/sayri.conf"
  # Never race the live instance for the API port.
  if ! grep -q '^\[api\]' "$DEV_CONFIG/sayri.conf"; then
    printf '\n[api]\nport=18765\n' >>"$DEV_CONFIG/sayri.conf"
  fi
  chmod 600 "$DEV_CONFIG/sayri.conf"
  echo "==> copied sayri.conf to $DEV_CONFIG (live config untouched)" >&2
fi

# Reuse downloaded models/voices without duplicating gigabytes.
for sub in models voices bin; do
  src="$HOME/.local/state/sayri/$sub"
  dst="$DEV_STATE/$sub"
  if [[ -d "$src" && ! -e "$dst" ]]; then
    ln -s "$src" "$dst"
  fi
done

LOG="${TMPDIR:-/tmp/opencode}/sayri-dev.log"
mkdir -p "$(dirname "$LOG")"
: >"$LOG"

echo "==> dev copy: $DEV_ROOT" >&2
echo "==> config:   $DEV_CONFIG" >&2
echo "==> state:    $DEV_STATE" >&2
echo "==> WebKit orb: $([[ $WITH_ORB -eq 1 ]] && echo enabled || echo disabled)" >&2
echo "==> log:      $LOG" >&2
echo "==> press Ctrl+C (or wait for the timeout) to close it" >&2

export PYTHONPATH="$DEV_ROOT/lib${PYTHONPATH:+:$PYTHONPATH}"
export SAYRI_CONFIG_DIR="$DEV_CONFIG"
export SAYRI_STATE_DIR="$DEV_STATE"
export SAYRI_DATA_DIR="$DEV_ROOT/web"
export SAYRI_API_HOST=127.0.0.1
export SAYRI_API_PORT=18765
export SAYRI_SKIP_PRELOAD=1
export SAYRI_SKIP_BLUR_LIST=1
export SAYRI_SKIP_AUTOSTART=1
export SAYRI_FORCE_WAYLAND=1
export GDK_BACKEND=wayland
export GSK_RENDERER=cairo
export LIBGL_ALWAYS_SOFTWARE=1
export WEBKIT_DISABLE_DMABUF_RENDERER=1
export WEBKIT_DISABLE_COMPOSITING_MODE=1
export GST_DEBUG=0
if [[ "$WITH_ORB" -eq 0 ]]; then
  export SAYRI_DEV_NO_ORB=1
fi
if [[ -n "$TIMEOUT_MS" ]]; then
  export SAYRI_AUTOQUIT_MS="$TIMEOUT_MS"
fi

set +e
python3 -m sayri --show 2>&1 | tee -a "$LOG"
code=${PIPESTATUS[0]}
set -e

if [[ $SHOW_LOGS -eq 0 && -s "$LOG" ]]; then
  echo "==> log saved to $LOG" >&2
fi
exit "$code"
