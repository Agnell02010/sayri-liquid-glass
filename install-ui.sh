#!/usr/bin/env bash
# Install the Liquid Glass UI into the system Sayri package.
#
# This writes to /usr/share/sayri, so it must be run with sudo. It backs up
# every file it replaces. Only the files that contain the restyle and the
# tray bugfix are copied (cajita, indicator, overlay, webkit).
#
# Usage:
#   sudo ./install-ui.sh
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "This script must run as root:  sudo $0" >&2
  exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/lib/sayri"
DEST="/usr/share/sayri/lib/sayri"

if [[ ! -d "$DEST" ]]; then
  echo "Sayri does not look installed at $DEST" >&2
  exit 1
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
for f in cajita.py indicator.py overlay.py webkit.py; do
  if [[ ! -f "$SRC/$f" ]]; then
    echo "missing $SRC/$f" >&2
    exit 1
  fi
  if [[ -f "$DEST/$f" ]]; then
    cp -a "$DEST/$f" "$DEST/$f.bak-$STAMP"
    echo "backup: $DEST/$f.bak-$STAMP"
  fi
  install -m 0644 "$SRC/$f" "$DEST/$f"
  echo "installed: $DEST/$f"
done

rm -rf "$DEST/__pycache__"
echo
echo "Done. To use the new UI, quit the running instance and start it again:"
echo "  sayri --quit"
echo "  sayri --launch-ui"
echo
echo "If you want to try it without touching the live session first:"
echo "  ./run-sayri-safe.sh --timeout 20"
