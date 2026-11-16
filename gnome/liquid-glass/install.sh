#!/usr/bin/env bash
# Installs the tuned Liquid Glass look: patched shader, schema and settings.
set -euo pipefail

UUID="liquid-glass@thinkingcoding1231.gmail.com"
SCHEMA="org.gnome.shell.extensions.$UUID"
# Il path dconf non contiene l'UUID: e' quello dichiarato dallo schema, e un
# dconf load sul path sbagliato non fa niente e non avvisa.
DCONF_PATH="/org/gnome/shell/extensions/liquid-glass/"
EXT="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$UUID"
HERE="$(cd "$(dirname "$0")" && pwd)"

[ -d "$EXT/shaders" ] || { echo "estensione non trovata in $EXT"; exit 1; }

cp "$HERE/glass.frag" "$EXT/shaders/glass.frag"
# Il modulo del puntatore va bene anche se nessuno lo importa: senza le cinque
# modifiche in dist/ il cancello resta a 1.0 e lo shader disegna come prima.
if [ -f "$HERE/cursorLight.js" ]; then
    cp "$HERE/cursorLight.js" "$EXT/dist/rendering/cursorLight.js"
fi

schema_src="$HERE/$SCHEMA.gschema.xml"
if [ -f "$schema_src" ]; then
    cp "$schema_src" "$EXT/schemas/"
    glib-compile-schemas "$EXT/schemas/"
fi

dconf load "$DCONF_PATH" < "$HERE/settings.dconf"

gnome-extensions disable "$UUID" || true
sleep 1
gnome-extensions enable "$UUID"
echo "Fatto. Se qualcosa non si aggiorna, esci e rientra dalla sessione."
