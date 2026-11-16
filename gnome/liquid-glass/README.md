# Liquid Glass — look tarato

Patch dello shader di `liquid-glass` (ryohsuke) con la luce e la rifrazione dei
widget di `liquidglass-widgets`, più le impostazioni usate su questo sistema.

## Cosa cambia nello shader

Tutto è dietro `#define`, quindi tornare indietro è un flag:

| define | effetto |
|---|---|
| `LG_WIDGET_SURFACE_LIGHT 1` | sostituisce Fresnel + specular + sheen con lone d'angolo e lip light dei widget |
| `LG_WIDGET_REFRACTION 1` | sostituisce la rifrazione con quella dei widget (Snell, banda da 35 px) |
| `LG_WIDGET_REFRACTION 0` | rifrazione originale di ryohsuke |

Il dock fa eccezione: è largo e basso, quindi il suo vetro usa la ricetta
originale di ryohsuke appena rinforzata.

```glsl
#define DOCK_DISP_BOOST  1.25   // piega: +25% sull'originale
#define DOCK_LIGHT_BOOST 1.15   // luce: +15% sull'originale
```

## Attenzione: ci sono due schema con lo stesso id

- `/usr/share/glib-2.0/schemas/...gschema.xml` — di proprietà di root, versione
  vecchia. È quello che legge `gsettings` da terminale.
- `$EXT/schemas/...gschema.xml` — quello che legge GNOME Shell per
  l'estensione.

Condividono lo stesso path dconf, quindi i **valori** sono comuni, ma i
**default** no. Cambiare i default in una copia sola dà risultati incoerenti:
se si fa `gsettings reset`, il terminale e la shell leggono cose diverse.
Per questo il "default di sistema" vero richiede root.

## Installazione

```bash
./install.sh
```
