"""Sayri overlay: single transparent window containing the WebKit Siri Orb
and animated Chroma-Ring Cajita, pinned to the TOP-RIGHT corner of the monitor.
"""

import json
import os
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gdk, GLib, Gtk, WebKit  # noqa: E402

from .cajita import BAR_HEIGHT, BAR_WIDTH, SayriCajita
from .webkit import (
    get_primary_geometry_gnome,
    pin_window,
    webview_setup,
    SCHEME,
    ensure_scheme,
)

BUBBLE_WIDTH = BAR_WIDTH
BUBBLE_HEIGHT = 620
GAP = 22
TOP_RATIO = 0.16


def _monitor_geometry() -> tuple[int, int, int, int]:
    geo = get_primary_geometry_gnome()
    if geo:
        return geo
    try:
        monitor = Gdk.Display.get_default().get_monitors().get_item(0)
        geom = monitor.get_geometry()
        return (geom.x, geom.y, geom.width, geom.height)
    except Exception:  # noqa: BLE001
        return (0, 0, 1920, 1080)


def _overlay_metrics(width: int, height: int) -> tuple[int, int]:
    """Return (left_margin, top_margin) for a centred Siri-style bar."""
    _mx, _my, mon_w, mon_h = _monitor_geometry()
    left = max(0, (mon_w - BUBBLE_WIDTH) // 2)
    top = int(mon_h * TOP_RATIO)
    top = max(16, min(top, mon_h - height - 16))
    return left, top


class SayriOverlay:
    """Single transparent window with both the native orb and the animated chroma cajita."""

    def __init__(self, app) -> None:
        self.app = app
        self.cfg = app.cfg

        # The floating WebKit orb is off by default: the bar already carries its
        # own mic button, so the orb only added a second WebKit process tree for
        # a decoration. SAYRI_SHOW_ORB=1 brings it back; SAYRI_DEV_NO_ORB=1 keeps
        # it off explicitly (used by the headless preview).
        self._no_orb = os.environ.get("SAYRI_SHOW_ORB", "0") != "1"
        if os.environ.get("SAYRI_DEV_NO_ORB") == "1":
            self._no_orb = True

        orb_size = self.cfg.get_int("ui", "orb_size")
        if orb_size < 100 or orb_size > 300:
            orb_size = 140

        width = BUBBLE_WIDTH + 24 if self._no_orb else BUBBLE_WIDTH + GAP + orb_size + 24
        height = BUBBLE_HEIGHT
        self._left_margin, self._top_margin = _overlay_metrics(width, height)

        # ── window ──────────────────────────────────────────────────
        self.win = Gtk.ApplicationWindow(application=app)
        self.win.set_default_size(width, height)
        self.win.set_resizable(False)
        self.win.set_decorated(False)
        self.win.add_css_class("sayri-overlay")

        try:
            css = Gtk.CssProvider()
            css.load_from_data(
                b"window.sayri-overlay, "
                b"window.sayri-overlay.background, "
                b"window.sayri-overlay.csd, "
                b"window.sayri-overlay decoration, "
                b"window.sayri-overlay > contents, "
                b"window.sayri-overlay > box, "
                b".sayri-overlay, "
                b".sayri-overlay.background { "
                b"    background: none; "
                b"    background-color: transparent; "
                b"    background-image: none; "
                b"    border: none; "
                b"    box-shadow: none; "
                b"    outline: none; "
                b"}"
            )
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), css,
                Gtk.STYLE_PROVIDER_PRIORITY_USER)
        except Exception:  # noqa: BLE001
            pass

        self.win.connect("close-request", lambda *_: (self.win.set_visible(False), True)[-1])

        # ── pin to the top-centre of the primary monitor ──────────────
        pin_window(self.win, top_margin=self._top_margin,
                   left_margin=self._left_margin,
                   width=width, height=height)

        # ── layout: horizontal box [ cajita · orb ] ─────────────────
        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=GAP)
        self.hbox.set_halign(Gtk.Align.START)
        self.hbox.set_valign(Gtk.Align.START)
        self.hbox.set_hexpand(False)
        self.hbox.set_vexpand(False)

        # 1. Cajita with Chroma-Ring animated border
        self.cajita = SayriCajita(app)
        self.cajita.set_valign(Gtk.Align.START)
        self.cajita.set_hexpand(False)
        self.hbox.append(self.cajita)

        # 2. WebKit-based animated Siri Orb (React Native/Skia)
        self._orb_size = orb_size
        self._orb_ready = False
        self._orb_pending: list[tuple[str, dict]] = []
        self.web = None
        self._orb_box = None
        if not self._no_orb:
            self.web = WebKit.WebView.new()
            ensure_scheme(self.web.get_context())
            ucm = webview_setup(self.web, on_message=self._on_orb_message)
            # Wrap WebKit in a fixed-size container (WebKit ignores set_size_request)
            self._orb_box = Gtk.Box()
            self._orb_box.set_size_request(orb_size, orb_size)
            self._orb_box.set_halign(Gtk.Align.END)
            self._orb_box.set_valign(Gtk.Align.START)
            self._orb_box.set_hexpand(False)
            self._orb_box.set_vexpand(False)
            self._orb_box.append(self.web)
            self.web.set_hexpand(True)
            self.web.set_vexpand(True)
            self.web.load_uri(f"{SCHEME}://app/index.html?mode=orb")
            self.hbox.append(self._orb_box)

        self.win.set_child(self.hbox)

        # The glass samples the wallpaper under the pill, so it needs the
        # window's real position on the monitor.
        self._sync_glass_origin()

        # Auto-hide on unfocus / click outside
        self._was_active = False

        def _do_auto_hide() -> None:
            if hasattr(self.app, "_settings_proc") and self.app._settings_proc and self.app._settings_proc.poll() is None:
                return
            cfg = getattr(self.app, "cfg", None)
            if cfg is None or cfg.get_bool("ui", "close_on_click_outside"):
                self._was_active = False
                if hasattr(self, "cajita") and hasattr(self.cajita, "card_overlay"):
                    self.cajita.hide_card()
                self.hide()

        def _on_overlay_active_changed(win, _param):
            if win.is_active():
                self._was_active = True
                return
            if not getattr(self, "_was_active", False):
                if time.monotonic() - getattr(self, "_just_shown", 0.0) < 0.4:
                    return
            _do_auto_hide()

        self.win.connect("notify::is-active", _on_overlay_active_changed)

        focus_ctrl = Gtk.EventControllerFocus.new()
        def _on_focus_leave(_ctrl):
            if not getattr(self, "_was_active", False):
                if time.monotonic() - getattr(self, "_just_shown", 0.0) < 0.4:
                    return
            _do_auto_hide()
        focus_ctrl.connect("leave", _on_focus_leave)
        self.win.add_controller(focus_ctrl)

    def _sync_glass_origin(self) -> None:
        try:
            self.cajita.pill_bg.set_screen_origin(self._left_margin, self._top_margin)
            card_y = self._top_margin + BAR_HEIGHT + 4
            self.cajita.card_bg.set_screen_origin(self._left_margin, card_y)
        except Exception:
            pass

    def _on_orb_message(self, text: str) -> None:
        try:
            msg = json.loads(text)
        except Exception:  # noqa: BLE001
            return
        if msg.get("type") == "ready":
            self._orb_ready = True
            for s, o in self._orb_pending:
                self._orb_set_state(s, o)
            self._orb_pending = []
        elif msg.get("type") == "click":
            self.app.on_orb_click()

    def _orb_set_state(self, state: str, opts: dict | None = None) -> None:
        opts = opts or {}
        if self.web is None:  # orb removed: nothing to drive, nothing to queue
            return
        if not self._orb_ready:
            self._orb_pending.append((state, opts))
            return
        js = (f"window.sayriBridge && window.sayriBridge.setState("
              f"{json.dumps(state)}, {json.dumps(opts)})")
        self.web.evaluate_javascript(js, len(js), None, f"{SCHEME}://app", None, None, None)

    def set_state_sync(self, state: str, _opts: dict | None = None) -> None:
        self._orb_set_state(state, {"size": self._orb_size})
        if state == "speaking":
            self.cajita.set_speaking(True)
        else:
            self.cajita.set_speaking(False)
        if state in ("listening", "activated"):
            self.cajita.pill_bg.set_mode("active")
        elif state == "thinking":
            self.cajita.pill_bg.set_mode("rotating")
        elif state == "idle":
            if not self.cajita.entry.get_text().strip():
                self.cajita.pill_bg.set_mode("idle")

    def set_audio_level(self, level: float) -> None:
        if not self._orb_ready:
            return
        lvl = max(0.0, min(1.0, float(level)))
        js = f"window.sayriBridge && window.sayriBridge.setAudioLevel && window.sayriBridge.setAudioLevel({lvl:.3f})"
        self.web.evaluate_javascript(js, len(js), None, f"{SCHEME}://app", None, None, None)

    def set_content(self, kind: str, text: str) -> None:
        self.cajita.set_content(kind, text)

    def set_mic(self, active: bool) -> None:
        self.cajita.set_mic(active)

    def set_busy(self, busy: bool) -> None:
        self.cajita.set_busy(busy)

    def clear(self) -> None:
        self.cajita.clear()

    @property
    def is_visible(self) -> bool:
        return getattr(self, "_is_visible", False) or bool(self.win.get_visible())

    def reassert_position(self) -> bool:
        fn = getattr(self.win, "_reassert_x11_position", None)
        if fn:
            fn()
        return GLib.SOURCE_REMOVE

    def show(self) -> None:
        self._is_visible = True
        self._just_shown = time.monotonic()
        self._was_active = False
        self._orb_set_state("idle", {"size": self._orb_size})
        self.win.set_visible(True)
        try:
            self.win.present_with_time(0)
        except Exception:
            self.win.present()
        self._sync_glass_origin()
        self.cajita.animate_in()
        self.reassert_position()
        GLib.timeout_add(50, self.reassert_position)
        GLib.timeout_add(150, self.reassert_position)
        def _focus():
            self.cajita.entry.grab_focus()
            self.cajita.entry.set_position(-1)
        GLib.idle_add(_focus)
        if hasattr(self, "app") and self.app and hasattr(self.app, "on_shown"):
            self.app.on_shown()

    def hide(self) -> None:
        self._is_visible = False
        self._was_active = False
        self.win.set_visible(False)
        if hasattr(self, "app") and self.app and hasattr(self.app, "on_hidden"):
            self.app.on_hidden()

    def toggle(self) -> None:
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def apply_config(self) -> None:
        if self._no_orb:
            return
        orb_size = self.cfg.get_int("ui", "orb_size")
        if orb_size < 100 or orb_size > 300:
            orb_size = 140
        self._orb_size = orb_size
        width = BUBBLE_WIDTH + 24 if self._no_orb else BUBBLE_WIDTH + GAP + orb_size + 24
        height = max(BUBBLE_HEIGHT, orb_size)
        self._left_margin, self._top_margin = _overlay_metrics(width, height)
        if self._orb_box is not None:
            self._orb_box.set_size_request(orb_size, orb_size)
        self.win.set_default_size(width, height)
        pin_window(self.win, top_margin=self._top_margin,
                   left_margin=self._left_margin,
                   width=width, height=height)
        self._sync_glass_origin()
        self.reassert_position()
