#!/usr/bin/env python3
"""Headless preview harness for the Sayri Liquid Glass Cajita.

Renders the real ``SayriCajita`` widget inside a throw-away GTK window with a
fake desktop wallpaper, then saves a PNG.  It never talks to the running Sayri
instance, never loads WebKit and never touches the user's live session, so it
is safe to use while iterating on the design.

Run it through ``run-preview-safe.sh`` (nested Mutter) on GNOME Wayland:

    ./run-preview-safe.sh --shot /tmp/opencode/sayri-pill.png
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import tempfile
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "lib"))

from sayri.cajita import (  # noqa: E402
    BAR_HEIGHT, BAR_WIDTH, SayriCajita, _cover_pixbuf, _wallpaper_path,
    markdown_to_pango,
)


class StubOverlay:
    def hide(self) -> None:
        pass


class StubApp:
    """Minimal stand-in for ``sayri.app.SayriApp``."""

    def __init__(self) -> None:
        self.cfg = {}
        self.overlay = StubOverlay()
        self.storage = None
        self.active_agent = None
        self._mode = "idle"

    def listening_now(self) -> bool:
        return self._mode in ("listening", "active")

    def toggle_listening(self) -> None:
        pass

    def send_text(self, text: str) -> None:
        pass

    def new_conversation(self) -> None:
        pass

    def _apply_mode(self, mode: str) -> None:
        self._mode = mode

    def switch_session(self, *args, **kwargs) -> None:
        pass


def draw_wallpaper(area: Gtk.DrawingArea, cr: cairo.Context, w: int, h: int) -> None:
    """A near-black abstract wallpaper with soft colour blooms."""
    bg = cairo.LinearGradient(0, 0, w * 0.35, h)
    bg.add_color_stop_rgb(0.0, 0.055, 0.050, 0.085)
    bg.add_color_stop_rgb(0.55, 0.020, 0.022, 0.040)
    bg.add_color_stop_rgb(1.0, 0.008, 0.008, 0.014)
    cr.set_source(bg)
    cr.paint()

    blooms = (
        (0.18, 0.16, 0.55, (1.00, 0.35, 0.62), 0.16),
        (0.86, 0.30, 0.60, (0.55, 0.40, 1.00), 0.17),
        (0.62, 0.90, 0.65, (0.25, 0.50, 1.00), 0.13),
        (0.94, 0.78, 0.45, (1.00, 0.60, 0.30), 0.10),
    )
    for cx, cy, rad, col, alpha in blooms:
        x, y = cx * w, cy * h
        r = rad * max(w, h)
        g = cairo.RadialGradient(x, y, 0, x, y, r)
        g.add_color_stop_rgba(0.0, *col, alpha)
        g.add_color_stop_rgba(0.55, *col, alpha * 0.35)
        g.add_color_stop_rgba(1.0, *col, 0.0)
        cr.set_source(g)
        cr.paint()

    # Faint diagonal streak so the glass has something to refract.
    cr.save()
    cr.translate(w * 0.5, h * 0.5)
    cr.rotate(-0.35)
    streak = cairo.LinearGradient(-w, 0, w, 0)
    streak.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.0)
    streak.add_color_stop_rgba(0.47, 1.0, 1.0, 1.0, 0.0)
    streak.add_color_stop_rgba(0.50, 1.0, 1.0, 1.0, 0.035)
    streak.add_color_stop_rgba(0.53, 1.0, 1.0, 1.0, 0.0)
    streak.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
    cr.set_source(streak)
    cr.rectangle(-w * 1.5, -h * 1.5, w * 3, h * 3)
    cr.fill()
    cr.restore()


def draw_real_wallpaper(area: Gtk.DrawingArea, cr: cairo.Context, w: int, h: int) -> None:
    """The actual desktop wallpaper, so the sampled glass matches the backdrop."""
    path = _wallpaper_path()
    if not path:
        draw_wallpaper(area, cr, w, h)
        return
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file(path)
        pb = _cover_pixbuf(pb, w, h)
        # Pass through a PNG: cairo loads it without needing a Gdk display,
        # which is not always available inside the nested compositor.
        tmp = Path(tempfile.gettempdir()) / "sayri-preview-wallpaper.png"
        pb.savev(str(tmp), "png", [], [])
        cr.set_source_surface(cairo.ImageSurface.create_from_png(str(tmp)), 0, 0)
        cr.paint()
    except Exception as exc:
        print(f"[preview] wallpaper finto: {exc}", file=sys.stderr)
        draw_wallpaper(area, cr, w, h)


def build(args: argparse.Namespace) -> tuple[Gtk.Window, Gtk.Widget, SayriCajita]:
    app = StubApp()
    cajita = SayriCajita(app)
    cajita.set_size_request(BAR_WIDTH, -1)

    if args.text:
        cajita.entry.set_text(args.text)
        # Move the caret to the end only after the entry has been allocated,
        # otherwise GTK scrolls the text with a zero-width entry and the first
        # characters get clipped in the screenshot.
        GLib.timeout_add(120, lambda: (cajita.entry.set_position(-1), False)[1])

    if args.card != "none":
        if args.card_delay <= 0:
            cajita.show_card()
        cajita.card_stack.set_visible_child_name("chat")
        for tid, btn in cajita._tab_btns.items():
            if tid == "chat":
                btn.add_css_class("active")
            else:
                btn.remove_css_class("active")
        if args.card_text:
            cajita.response_label.set_markup(markdown_to_pango(args.card_text))
        if args.card in ("active", "thinking", "speaking"):
            cajita.card_bg.mode = args.card
            cajita.card_bg.angle = args.angle

    if args.state:
        cajita.pill_bg.mode = args.state
        cajita.pill_bg.angle = args.angle

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    content.set_halign(Gtk.Align.CENTER)
    content.set_valign(Gtk.Align.START)
    content.set_size_request(BAR_WIDTH, -1)
    content.set_hexpand(False)
    content.set_margin_top(args.top)
    content.append(cajita)

    root = Gtk.Overlay()
    root.set_size_request(args.width, args.height)
    backdrop = Gtk.DrawingArea()
    backdrop.set_draw_func(draw_real_wallpaper if args.wallpaper == "real" else draw_wallpaper)
    backdrop.set_hexpand(True)
    backdrop.set_vexpand(True)
    root.set_child(backdrop)
    root.add_overlay(content)

    # The real screen position of the pill, for the wallpaper sampling.
    if args.wallpaper == "real":
        origin_x = (args.width - BAR_WIDTH) // 2
        cajita.pill_bg.set_screen_origin(origin_x, args.top)
        cajita.card_bg.set_screen_origin(origin_x, args.top + BAR_HEIGHT + 4)

    window = Gtk.Window()
    window.set_default_size(args.width, args.height)
    window.set_decorated(False)
    window.set_child(root)
    return window, root, cajita


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shot", default="/tmp/opencode/sayri-preview.png")
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--height", type=int, default=760)
    parser.add_argument("--top", type=int, default=200)
    parser.add_argument("--state", choices=["idle", "active", "thinking", "speaking"], default="idle")
    parser.add_argument("--card", choices=["none", "chat", "active", "thinking", "speaking"], default="none")
    parser.add_argument("--card-text", default="")
    parser.add_argument("--text", default="")
    parser.add_argument("--angle", type=float, default=1.15)
    parser.add_argument("--drop", type=float, default=None,
                        help="freeze the opening drop at this progress (0..1)")
    parser.add_argument("--delay", type=int, default=700)
    parser.add_argument("--card-delay", type=int, default=0)
    parser.add_argument("--list", action="store_true", help="print widget tree and exit")
    parser.add_argument("--wallpaper", choices=["fake", "real"], default="fake")
    args = parser.parse_args()

    app = Gtk.Application(application_id="dev.sayri.preview")
    status = {"code": 0}

    def on_activate(gtk_app: Gtk.Application) -> None:
        window, root, cajita = build(args)
        gtk_app.add_window(window)
        window.present()
        if args.drop is None:
            cajita.animate_in()
        else:
            # Freeze the opening drop: no animation tag to fight with, the
            # capture renders exactly the requested moment.
            cajita.pill_bg._appear = 1.0
            cajita.pill_bg._drop = max(0.0, min(1.0, args.drop))
            cajita.pill_row.set_opacity(
                max(0.0, min(1.0, (cajita.pill_bg._drop - 0.35) / 0.45)))
        if args.card != "none" and args.card_delay > 0:
            GLib.timeout_add(
                args.card_delay,
                lambda: (cajita.show_card(), False)[1],
            )

        attempts = {"n": 0}

        def capture() -> bool:
            attempts["n"] += 1
            if args.list:
                def walk(widget: Gtk.Widget, depth: int = 0) -> None:
                    name = type(widget).__name__
                    print("  " * depth + name)
                    child = widget.get_first_child()
                    while child is not None:
                        walk(child, depth + 1)
                        child = child.get_next_sibling()
                walk(cajita)
                gtk_app.quit()
                return False

            try:
                width = root.get_width() or args.width
                height = root.get_height() or args.height
                paintable = Gtk.WidgetPaintable.new(root)
                snapshot = Gtk.Snapshot()
                paintable.snapshot(snapshot, width, height)
                node = snapshot.to_node()
                if node is None:
                    if attempts["n"] < 10:
                        # A freshly mapped overlay can yield an empty node
                        # before its first frame; try again shortly.
                        root.queue_draw()
                        GLib.timeout_add(120, capture)
                        return False
                    raise RuntimeError("empty render node")

                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
                cr = cairo.Context(surface)
                cr.set_source_rgba(0, 0, 0, 1)
                cr.paint()
                node.draw(cr)
                surface.flush()

                out = Path(args.shot)
                out.parent.mkdir(parents=True, exist_ok=True)
                surface.write_to_png(str(out))
                print(f"saved {out} ({width}x{height})")
            except Exception:  # pragma: no cover - preview diagnostics
                import traceback
                traceback.print_exc()
                status["code"] = 1
            gtk_app.quit()
            return False

        GLib.timeout_add(args.delay, capture)

    app.connect("activate", on_activate)
    code = app.run([])
    return status["code"] or code


if __name__ == "__main__":
    raise SystemExit(main())
