# Sayri Liquid Glass

A Liquid Glass skin for the [Sayri](https://github.com/Inled-Pulsar-OS/sayri) assistant bar:
a black-to-transparent ramp on the input bar and the answer card, a dark shade that cascades
along the rounded border following its angle, and an entrance where the bar opens out of a
droplet coming from the top edge.

## What it changes

- **Ramp** — nine-stop black-to-transparent gradient, long and gentle, on the input bar
  and (with a lighter floor) on the answer card, so the text stays readable.
- **Cascading shade** — the dark does not cut across the pill: it is traced *along* the
  rounded outline as many thin concentric strokes, then masked vertically, so it falls on
  the caps keeping the angle of the border. No visible banding.
- **Cached band** — that band costs 33 wide strokes, a group and a mask; it is drawn once
  into a `cairo.ImageSurface` per size and reused, which took the per-frame cost from
  4.91 ms to 0.025 ms.
- **Droplet entrance** — the bar starts as a small drop 22 px above its final place
  (14% wide, 58% tall), then opens down into the full pill in 0.46 s; the content fades in
  while it opens, so the text is never outside the glass.
- **Settings window** — same ramp as a `linear-gradient` on a transparent background.
- **Smaller response text** — 24 px instead of 26 px.

## The orb is off by default

The floating WebKit orb next to the bar is gone. It was a second WebKit process tree for a
decoration: the bar already has its own mic button, and the hotkey still works. The window
is narrower by the orb slot, and nothing else changes.

To bring it back, start Sayri with `SAYRI_SHOW_ORB=1`. `SAYRI_DEV_NO_ORB=1` still forces it
off, as used by the headless preview.

## Install

The theme lives in the Sayri Python package, so it is installed by copying the files over
an existing Sayri install (back up first):

```bash
ts=$(date +%Y%m%d-%H%M%S)
for f in cajita.py settings_cajita.py overlay.py app.py api_server.py domain/agent_engine.py; do
  cp -a "/usr/share/sayri/lib/sayri/$f" "/usr/share/sayri/lib/sayri/$f.bak-$ts"
done
cp lib/sayri/cajita.py lib/sayri/settings_cajita.py lib/sayri/overlay.py \
   lib/sayri/app.py lib/sayri/api_server.py /usr/share/sayri/lib/sayri/
cp lib/sayri/domain/agent_engine.py /usr/share/sayri/lib/sayri/domain/
```

For development without touching the system copy, run the app with the local package:

```bash
SAYRI_PYTHONPATH="$PWD/lib" python3 -m sayri --show
```

## Preview without a desktop

`preview.py` renders the widget headlessly, which is how the pixels in this repo were
checked:

```bash
./run-preview-safe.sh --width 1920 --height 1080 --top 172 --wallpaper fake --shot out.png
./run-preview-safe.sh --width 1920 --height 1080 --top 172 --drop 0.45 --shot drop.png
```

`--drop` freezes the entrance at a given progress (0 = drop closed, 1 = fully open).

## Notes

- `README-liquid-glass.md` is the Italian working log with every step, measurement and
  the reasons behind the parameters.
- The repo carries the Sayri sources needed to run the skin, so it is a working copy of the
  project rather than a patch.

## Credits and licence

Derived from [Sayri](https://github.com/Inled-Pulsar-OS/sayri) by Inled Group, released
under the MIT-INLED licence. The glass, the cascading shade and the droplet entrance are
the changes documented here.
