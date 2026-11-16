#!/usr/bin/env bash
# Installs the tuned Liquid Glass look: patched shader, schema and settings.
set -euo pipefail

UUID="liquid-glass@thinkingcoding1231.gmail.com"
EXT="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$UUID"
HERE="$(cd "$(dirname "$0")" && pwd)"

[ -d "$EXT/shaders" ] || { echo "estensione non trovata in $EXT"; exit 1; }

cp "$HERE/glass.frag"                    "$EXT/shaders/glass.frag"
cp "$HERE/$UUID.gschema.xml"             "$EXT/schemas/$UUID.gschema.xml"
glib-compile-schemas "$EXT/schemas/"

dconf load "/org/gnome/shell/extensions/$UUID/" < "$HERE/settings.dconf"

gnome-extensions disable "$UUID" || true
sleep 1
gnome-extensions enable "$UUID"
echo "Fatto. Se qualcosa non si aggiorna, esci e rientra dalla sessione."
