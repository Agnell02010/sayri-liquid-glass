#!/usr/bin/env bash
# Render the Sayri Liquid Glass UI inside a throw-away nested Mutter session.
#
# Nothing here touches the real GNOME session, the real Sayri process or the
# user's config: it starts a headless compositor on its own Wayland socket,
# renders preview.py, saves a PNG and tears everything down again.
#
# Usage:
#   ./run-preview-safe.sh [preview.py args...]
#   ./run-preview-safe.sh --shot /tmp/opencode/pill.png --state active
set -euo pipefail

cd "$(dirname "$0")"

RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/opencode/runtime-$(id -u)}"
mkdir -p "$RUNTIME_DIR"
chmod 700 "$RUNTIME_DIR"

DISPLAY_NAME="sayri-preview-$$"
LOG="${TMPDIR:-/tmp/opencode}/sayri-preview-mutter-$$.log"
mkdir -p "$(dirname "$LOG")"

cleanup() {
  if [[ -n "${MUTTER_PID:-}" ]] && kill -0 "$MUTTER_PID" 2>/dev/null; then
    kill "$MUTTER_PID" 2>/dev/null || true
    wait "$MUTTER_PID" 2>/dev/null || true
  fi
  rm -f "$RUNTIME_DIR/$DISPLAY_NAME" "$RUNTIME_DIR/$DISPLAY_NAME.lock"
}
trap cleanup EXIT

echo "==> starting nested Mutter ($DISPLAY_NAME)" >&2
XDG_RUNTIME_DIR="$RUNTIME_DIR" \
  mutter --headless --wayland \
  --wayland-display="$DISPLAY_NAME" \
  --virtual-monitor=1280x900 \
  --no-x11 \
  >"$LOG" 2>&1 &
MUTTER_PID=$!

for _ in $(seq 1 100); do
  [[ -S "$RUNTIME_DIR/$DISPLAY_NAME" ]] && break
  if ! kill -0 "$MUTTER_PID" 2>/dev/null; then
    echo "Mutter exited early; log follows:" >&2
    cat "$LOG" >&2 || true
    exit 1
  fi
  sleep 0.1
done

if [[ ! -S "$RUNTIME_DIR/$DISPLAY_NAME" ]]; then
  echo "Timed out waiting for Wayland socket; log follows:" >&2
  cat "$LOG" >&2 || true
  exit 1
fi

echo "==> rendering preview" >&2
XDG_RUNTIME_DIR="$RUNTIME_DIR" \
WAYLAND_DISPLAY="$DISPLAY_NAME" \
GDK_BACKEND=wayland \
GSK_RENDERER=cairo \
LIBGL_ALWAYS_SOFTWARE=1 \
GST_DEBUG=0 \
python3 preview.py "$@"
