# Liquid Glass — look tarato

Patch dello shader di `liquid-glass` (ryohsuke) con la luce e la rifrazione dei
widget di `liquidglass-widgets`, più le impostazioni usate su questo sistema.

## Cosa cambia nello shader

Tutto è dietro `#define`, quindi tornare indietro è un flag:

| define | effetto |
|---|---|
| `LG_WIDGET_SURFACE_LIGHT 1` | sostituisce Fresnel + specular + sheen con l'alone d'angolo e il lip light dei widget |
| `LG_WIDGET_REFRACTION 1` | sostituisce la rifrazione con quella dei widget (Snell, banda da 35 px) |
| `LG_WIDGET_REFRACTION 0` | rifrazione originale di ryohsuke |

Le due patch lavorano sulla cattura viva dello schermo, non sul wallpaper:
`cogl_sampler0` è il desktop nitido sotto la superficie, `cogl_sampler1` la
stessa cattura sfocata.

Il dock fa eccezione: è largo e basso, quindi il suo vetro usa la ricetta
originale di ryohsuke appena rinforzata.

```glsl
#define DOCK_DISP_BOOST  1.25   // piega: +25% sull'originale
#define DOCK_LIGHT_BOOST 1.15   // luce: +15% sull'originale
```

## Luce dei bordi che segue il cursore

Rim, specular e alone d'angolo passano per un cancello che dipende dalla
distanza dal puntatore: il bordo si illumina dove sta il cursore, e lontano
resta a `CURSOR_MIN_LIGHT` (0.35) per non spegnersi del tutto.

Quattro uniform — `cursor_x`, `cursor_y` (uv 0..1 dello spazio della
superficie), `cursor_radius` (px), `cursor_light` (0..1) — alimentati da un
modulo che ascolta `captured-event` sullo stage, a ~30 Hz e solo mentre il mouse
si muove.

Il cancello da solo non basta: la luce dei widget e' debole (`lip light * 0.10`),
quindi modulare solo quella non si vede su niente tranne il dock, che usa la
luce originale di ryohsuke. Per questo c'e' anche un **riflesso additivo**:
un alone soffice appena dentro il bordo, solo dove sta il puntatore.

Le manopole stanno tutte nello shader, e si cambiano con un reload:

```glsl
#define CURSOR_MIN_LIGHT    0.35   // luce residua quando il cursore e' lontano
#define CURSOR_REACH_SCALE  1.6    // moltiplica il raggio arrivato dal JS
#define CURSOR_RIM_WIDTH    18.0   // spessore dell'alone, in px
#define CURSOR_GAIN         0.16   // intensita' dell'alone
```

Due dettagli che sono serviti a renderlo usabile:

- **il dock non riceve l'alone**: la sua luce originale risponde gia' bene al
  cancello, e sommare l'alone lo rendeva troppo luminoso;
- **il cancello e' neutro se il cursore e' fuori dalla superficie**
  (`cursorInBox` su uv, margine 0.05). Senza questo la posizione che il JS
  lascia quando il puntatore esce resta dentro la portata, e l'alone si
  **congela** sul bordo piu' vicino all'uscita, fermo.

Con `cursor_light = 0` il cancello vale esattamente 1.0, quindi **il solo
shader è retrocompatibile**: senza il lato JS disegna quello che disegnava
prima.

Il lato JS sono cinque modifiche:

| file | modifica |
|---|---|
| `dist/rendering/cursorLight.js` | modulo nuovo (in questo repo) |
| `dist/rendering/glassRenderer.js` | `setCursorLight(uvX, uvY, radiusPx)` |
| `dist/rendering/backdropGlass.js` | `setCursorLight(...)` che delega al renderer |
| `dist/rendering/material.js` | default degli uniform + binding del booleano |
| `dist/diagnostics/glass.js` | `forEachGlass(apply)` esportata |
| `extension.js` | `startCursorLight()` in enable, `stopCursorLight()` in disable |

L'opzione è la chiave GSettings `glass-cursor-light` (default `true`). Per
spegnerla senza root:

```bash
dconf write /org/gnome/shell/extensions/liquid-glass/glass-cursor-light false
```

Con `gsettings` serve indicare lo schema dell'estensione, perché quello di
sistema è una versione più vecchia che non ha la chiave:

```bash
GSETTINGS_SCHEMA_DIR=~/.local/share/gnome-shell/extensions/liquid-glass@thinkingcoding1231.gmail.com/schemas \
  gsettings set org.gnome.shell.extensions.liquid-glass@thinkingcoding1231.gmail.com glass-cursor-light false
```

## Serve un logout per il lato JS

Lo shader si aggiorna con `gnome-extensions disable/enable`: i `.frag` sono letti
da disco a ogni `initialize()`. **Il codice JS no**: GNOME Shell tiene in memoria
il grafo dei moduli dell'estensione, quindi disable/enable reinstanzia la classe
ma non rilegge `extension.js` ne' i file che importa.

Una modifica a `cursorLight.js`, `material.js`, `glassRenderer.js`,
`backdropGlass.js`, `diagnostics/glass.js` o `extension.js` richiede un
**logout** (o un riavvio della shell). Si riconosce perche' il comportamento non
cambia affatto, senza nessun errore nel journal.

## Due trappole da conoscere

**1. Il path dconf non contiene l'UUID.** Lo schema dichiara
`/org/gnome/shell/extensions/liquid-glass/`, quindi:

```bash
# giusto
dconf dump /org/gnome/shell/extensions/liquid-glass/
# sbagliato: non esiste, restituisce vuoto
dconf dump /org/gnome/shell/extensions/liquid-glass@thinkingcoding1231.gmail.com/
```

Un `dconf load` sul path sbagliato non fa niente e non avvisa.

**2. Ci sono due schema con lo stesso id.**

- `/usr/share/glib-2.0/schemas/...gschema.xml` — di proprietà di root, versione
  vecchia. È quello che legge `gsettings` da terminale.
- `$EXT/schemas/...gschema.xml` — quello che legge GNOME Shell.

I **valori** stanno in dconf e sono comuni, i **default** no. Un
`gsettings reset` riporta ai default dello schema di sistema, che qui sono di
un'altra versione (IOR 2.02 invece di 1.70, raggio menu 14 invece di 30): il
desktop si rompe. Per questo i default vanno messi in `system-db:local`, dove
hanno la precedenza.

## Contenuto

| file | cos'è |
|---|---|
| `glass.frag` | shader patchato |
| `cursorLight.js` | il modulo del puntatore, da copiare in `dist/rendering/` |
| `org.gnome.shell.extensions.liquid-glass@thinkingcoding1231.gmail.com.gschema.xml` | schema dell'estensione, con `glass-cursor-light` |
| `settings.dconf` | le chiavi del look, esportate dal path corretto |
| `dconf-system-default` | le stesse chiavi nel formato `local.d`, per il default di sistema |
| `install.sh` | copia shader + schema + modulo, ricompila, importa i valori, ricarica |

## Installazione del look

```bash
./install.sh
```

Per ripristinare a mano:

```bash
dconf load /org/gnome/shell/extensions/liquid-glass/ < settings.dconf
```

## Default di sistema (richiede root)

Il profilo dconf dell'utente include già `system-db:local`, quindi basta
mettere il file e ricompilare il database:

```bash
install -D -m 0644 dconf-system-default /etc/dconf/db/local.d/50-liquid-glass
dconf update
```

Da quel momento queste sono le impostazioni **predefinite**: un `gsettings
reset` torna a questo look invece che ai default di fabbrica, e un utente nuovo
le eredita. Verificato con `gsettings reset` su `menu-saturation`, `glass-ior` e
`menu-blur-radius`.

Per rimuoverle:

```bash
rm /etc/dconf/db/local.d/50-liquid-glass && dconf update
```

## Stato della verifica

- `glslangValidator`: 0 errori nelle quattro combinazioni dei due `#define` e
  con `LG_SHAPE_TEXTURE`.
- Estensione `ACTIVE` dopo il reload, nessun errore JS o di shader nel journal.
- `dconf write` della chiave di toggle verificato in entrambi i versi.
- Backup: `~/.config/liquid-glass-backup/liquid-glass-REAL-2026-11-16-2258.dconf`,
  `gschema-2026-11-16-2256.xml`, shader in questo repo.
