# Sayri · Liquid Glass (iOS 27 Siri style)

Restyle della UI di Sayri ispirato alla nuova Siri AI di macOS/iOS 27: una
**barra "Search or Ask" centrata** orizzontalmente a circa un quarto
dell'altezza dello schermo (più in alto), in vetro fumé quasi nero. Il corpo è opaco in alto
e sempre più trasparente verso il basso, così la luce dello sfondo attraversa
il vetro; il bordo è neutro e sottile, con una **rifrazione iridescente rimossa dal bordo (ora solo sul cursore)** (ciano → blu → viola → rosa → arancio).
Niente grande aurora colorata: il colore vive nel vetro, non nel corpo.

Il design segue i riferimenti `siriai1–5` forniti dall'utente
(`~/Archivio/Downloads`): `siriai2.mp4` per la barra "Search or Ask" e la
card che si apre sotto, `siriai3.mp4` per il pannello Siri laterale,
`siriai1/4/5` per il pannello e le pill di suggerimento.

Tutto è stato sviluppato in una copia isolata:

```
/home/agnell0/Projects/sayri-liquid-glass
```

L'installazione di sistema (`/usr/share/sayri`) non è stata toccata.

## Dimensioni, posizione e animazioni

| Elemento | Valore |
| --- | --- |
| Barra | `540 × 84` px, pillola piena (`raggio = altezza / 2`) |
| Finestra overlay | `564` px senza orb, `726` px con orb WebKit |
| Posizione | centrata orizzontalmente sul monitor primario |
| Altezza | `top = int(1080 × 0.16) = 172` (`TOP_RATIO = 0.16`) |
| Card | larghezza `540`, raggio `26`, altezza max contenuto `470` |
| Entrata vetro | scala `0.94 → 1.0` + fade, 340 ms, ease-out cubic |
| Entrata testo | opacity `0 → 1` in parallelo al vetro |
| Apertura card | fade + scivolata 10 px, ease-out cubic, 340 ms; chiusura 200 ms |
| Caret | prismatico con glow quando il campo è vuoto; rosa nativo con testo |
| Bordo | neutro: solo riflesso bianco, nessun colore |
| Testi | barra `22 px`, risposta card `26 px`, font di sistema |
| Hint | `— Ask Sayri` in grigio quando c'è del testo |

La posizione è gestita in `overlay.py` (`_overlay_metrics`) e passata come
`left_margin` a `pin_window` in `webkit.py`, sia per layer-shell (Wayland) sia
per X11/XWayland.

## Compatibilità con l'estensione Liquid Glass

`application-window-whitelist` dell'estensione contiene ora `sayri`,
`es.inled.sayri` e `Sayri`, con `enable-application-glass` attivo: se la
finestra gira come toplevel normale (X11/XWayland), il vetro dell'estensione
viene applicato anche a Sayri.

Su Wayland la barra è un surface **layer-shell OVERLAY**, ma la finestra resta
visibile a Meta: l'estensione la elenca (`wmClass: es.inled.sayri`) e, con
`application-glass-all-windows` attivo, le applica il vetro. Il corpo della
pillola è quindi un velo nero (alpha `1.00 → 0.03` dall'alto in basso): nero
pieno solo in cima (alpha `1.00`), poi una rampa lunga e chiara che copre
tutta l'altezza (`0.96 @0.10`, `0.85 @0.24`, `0.74 @0.38`, `0.62 @0.52`,
`0.49 @0.66`, `0.34 @0.80`, `0.17 @0.92`, `0.03 @1.00`) e lascia passare lo sfondo. Anche il backdrop sfocato (`WallpaperGlass`) sfuma con la stessa
curva (`1.00 → 0.04`), altrimenti sotto resterebbe una lastra di vetro opaca;
la card usa la stessa rampa lunga e chiara ma con un fondo `0.18` invece di
`0.03`, perché il testo arriva fino al bordo inferiore; anche la finestra di
Impostazioni (`settings_cajita.SETTINGS_CSS`) usa la stessa curva come
`linear-gradient` sul fondo della finestra, che è diventata trasparente, così
la parte bassa lascia vedere il desktop Il taglio non è orizzontale: una fascia scura è tracciata **lungo il
contorno** della pillola con molti stroke concentrici sottili (larghezza 4→100 px a passi di 3,
alpha 0,032 ciascuno: si sommano verso il bordo senza leggersi come fasce),
mascherati da una
rampa verticale che resta piena fino a `0.42` e si chiude più in alto, prima
del fondo delle calotte (`0.58 @0.54`, `0.16 @0.64`, `0` a `0.72`).
Così il nero scende sui lati mantenendo l'angolazione del bordo e si ferma
lì, invece di chiudere con una linea dritta. Nel
preview headless (`SAYRI_DEV_NO_ORB=1`) non c'è compositore dietro, quindi la
sfocatura non si vede: il giudizio sul vetro va fatto sulla sessione reale.


## Cosa è cambiato

| File | Modifica |
| --- | --- |
| `lib/sayri/cajita.py` | Nuovo renderer `ChromaBackground._draw`: barra `540×84` in vetro fumé, velo scuro quasi invisibile (alpha `0.34 → 0.14`), bordo solo bianco neutro, lente speculare e riflesso diagonale morbido. Rimossi i CSS `box-shadow` (disegnavano un rettangolo visibile) e l'ombra ora è disegnata in Cairo. Aggiunti: animazione di entrata scala+fade, caret prismatico lampeggiante con glow (unico elemento colorato), hint `— Ask Sayri`, revealer della card (`SLIDE_DOWN`, 280 ms) e clamp di larghezza con `Gtk.ScrolledWindow` (`propagate_natural_width=False`, max `470`). Testo barra 22 px, Risposta 26 px, icone 22 px, placeholder "Search or Ask…". Logo colorato sostituito da una scintilla bianca monocromatica (stile Apple Intelligence); per riavere il logo originale: `SAYRI_LOGO_STYLE=color`. |
| `lib/sayri/overlay.py` | Barra centrata a `TOP_RATIO = 0.33` tramite `_overlay_metrics()`; `BUBBLE_WIDTH = 760`, `BUBBLE_HEIGHT = 620`. La finestra viene posizionata con `left_margin` invece del vecchio ancoraggio a destra. Aggiunto `SAYRI_DEV_NO_ORB=1` per provare la UI senza WebKit; `apply_config` non fallisce in quella modalità. `show()` avvia l'animazione di entrata e `hide_card()` chiude la card con il revealer. |
| `lib/sayri/webkit.py` | `pin_window`, `pin_layer_shell` e `pin_x11_window` accettano `left_margin` e centrano la finestra sul monitor primario; compatibilità mantenuta con `right_margin`. |
| `lib/sayri/indicator.py` | Aggiunto `sysinfo` all'import: corregge il `NameError` in `_on_kill_all`. |
| `preview.py` | Harness headless aggiornato a `760` px, `--top`, `--delay` e `--card-delay` per catturare le animazioni; il caret viene spostato a fine testo dopo il layout. |

## Provare la UI senza aprire Sayri

Render headless dentro un Mutter annidato: nessun contatto con la sessione
GNOME reale, nessun WebKit, nessun processo Sayri.

```bash
cd ~/Projects/sayri-liquid-glass

# barra a riposo
./run-preview-safe.sh --shot /tmp/opencode/pill.png

# barra attiva + card con risposta
./run-preview-safe.sh --width 1000 --height 760 --top 250 \
  --state active --card chat \
  --text "Che tempo fa a Roma?" \
  --card-text "Roma oggi è soleggiata, **21°C**." \
  --shot /tmp/opencode/card.png

# fotogramma dell'animazione di entrata (100 ms)
./run-preview-safe.sh --state idle --delay 100 \
  --shot /tmp/opencode/entrance.png

# card che si apre 500 ms dopo la barra
./run-preview-safe.sh --width 1000 --height 760 --top 250 \
  --state active --card chat --card-delay 500 --delay 640 \
  --text "Che tempo fa a Roma?" \
  --card-text "Roma oggi è soleggiata, **21°C**." \
  --shot /tmp/opencode/card-opening.png
```

Le immagini vengono salvate dove indicate da `--shot`.

Anteprime già pronte:

- `screenshots/pill-idle.png` — barra a riposo con caret prismatico
- `screenshots/pill-active.png` — barra in ascolto/elaborazione
- `screenshots/card-chat.png` — barra con testo, hint `— Ask Sayri` e card aperta
- `screenshots/entrance.png` — fotogramma dell'animazione di entrata

Riferimenti usati per il design (in `~/Archivio/Downloads`):

- `siriai2.mp4` — barra "Search or Ask", testo grande, caret prismatico,
  hint `— Ask Siri` e pill "Show Results"
- `siriai3.mp4` — pannello Siri che entra da destra
- `siriai1.jpg` / `siriai4.jpg` — pannello Siri scuro
- `siriai5.jpg` — pill di suggerimento impilate

Il layout attuale segue la barra "Search or Ask": una sola barra larga con
scintilla, testo, cronologia e microfono, e la card che si apre sotto. La
variante `[allega] [Ask Siri] [microfono]` e il pannello laterale destro della
app Siri restano possibili passi successivi.


## Provare la copia di sviluppo

```bash
cd ~/Projects/sayri-liquid-glass

# UI vera, senza WebKit, chiusura automatica dopo 20 secondi
./run-sayri-safe.sh --timeout 20

# con anche l'orb WebKit
./run-sayri-safe.sh --timeout 20 --with-orb
```

La copia di sviluppo usa:

- `~/.config/sayri-dev` (copia della configurazione, la tua non viene scritta)
- `~/.local/state/sayri-dev` (socket IPC separato, quindi nessun comando
  viene inoltrato all'istanza reale)
- API su `127.0.0.1:18765` invece di `8765`
- backend Wayland, renderer Cairo, GL software
- niente aggiornamento dell'autostart né della blacklist di blur-my-shell

## Installare davvero

```bash
cd ~/Projects/sayri-liquid-glass
sudo ./install-ui.sh
```

Lo script salva un backup di ogni file sostituito con suffisso
`.bak-AAAAMMGG-HHMMSS`. Poi:

```bash
sayri --quit
sayri --launch-ui
```

Se vuoi prima vedere l'effetto senza riavviare Sayri, usa il preview o
`run-sayri-safe.sh`.

## Nota sull'instabilità segnalata

I coredump di GNOME Shell presenti sul sistema (5 nov, 17:05 e 19:38) mostrano
entrambi lo stesso stack:

```
clutter_actor_queue_relayout
g_object_run_dispose
meta_display_close
meta_context_destroy
```

Cioè il crash avviene nella fase di **chiusura del display / logout**, non
all'apertura di Sayri. Nello stesso intervallo sono presenti crash di Discord,
Sidra e freebuff. Non ci sono tracce di GPU hang (i915) né OOM nei log del
kernel.

Questo non esclude che l'estensione Liquid Glass di GNOME Shell possa reagire
male alla finestra di Sayri, ma i dump disponibili non la coinvolgono. Per
questo il percorso consigliato è:

1. provare prima `run-preview-safe.sh` (nessun rischio);
2. poi `run-sayri-safe.sh --timeout 20` (WebKit disattivato);
3. solo dopo installare e riavviare Sayri.

Se GNOME Shell dovesse ancora riavviarsi, disabilita temporaneamente
l'estensione Liquid Glass e ripeti il test:

```bash
gnome-extensions disable liquid-glass@thinkingcoding1231.gmail.com
```

## Prestazioni

La fascia scura sul bordo costa 33 tratti larghi fino a 102 px, un gruppo e una maschera: troppo per un fotogramma. Viene disegnata una volta in una `cairo.ImageSurface` per ogni misura (pillola o card) e poi incollata; la cache è in `ChromaBackground._fall_band`, chiave = larghezza, altezza, raggio e scale factor, al massimo 8 voci.

## Entrata a goccia

All'apertura la barra non scivola più da sotto: nasce come una **goccia** 22 px sopra la
posizione finale, larga il 14% e alta il 58%, e si apre scendendo in **0,46 s** (ease-out
cubica) fino alla pillola piena, con il raggio che passa da `h/2` al raggio della forma.

- stato: `ChromaBackground._drop` (0 = goccia chiusa, 1 = aperta), animato in `animate_in`;
- geometria: blocco `drop` in `_draw`, prima del disegno, così tutti i livelli del vetro
  (sfondo sfocato, riflessi, bordo) seguono la stessa forma;
- contenuto: `SayriCajita.animate_in` porta l'opacità della riga da 0 a 1 sulla stessa
  durata, così il testo entra mentre la goccia si apre e non resta mai fuori dal vetro;
- la fascia scura sul bordo si disegna solo a goccia aperta (`drop >= 0.995`), per non
  ricostruire la cache a ogni fotogramma;
- `preview.py --drop 0.45` congela un istante dell'apertura per confronti e screenshot.
