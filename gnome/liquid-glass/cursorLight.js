// Keeps the glass edge light following the pointer. The pointer is polled at
// ~30 Hz instead of listened to: while a menu is open GNOME grabs the pointer,
// the events stop reaching the stage, and the glass froze on the position it
// had when the menu was clicked. A query works during a grab.
//
// Editing this file needs a session restart, not just disable/enable: the shell
// keeps the extension's module graph in memory.
import GLib from 'gi://GLib';
import { forEachGlass } from '../diagnostics/glass.js';

// ~30 Hz. Twice that would look no smoother on a rim and cost twice the paints.
const INTERVAL_MS = 33;
// Reach of the highlight, in shader pixels.
const RADIUS_PX = 170.0;
// How far outside its own box a glass keeps receiving updates, in uv units.
const MARGIN = 0.15;

let _timerId = 0;
let _settingsId = 0;
let _settings = null;
let _enabled = true;
let _announced = false;
let _lastPx = Number.NEGATIVE_INFINITY;
let _lastPy = Number.NEGATIVE_INFINITY;
let _lastCount = -1;

function _apply(px, py) {
    let touched = 0;
    let sample = null;
    const total = forEachGlass(glass => {
        if (!glass.mapped || !glass.has_allocation())
            return;
        // Quick Settings toggles use a class without this setter.
        if (typeof glass.setCursorLight !== 'function')
            return;
        // Transformed box, not the actor's own size: the menu, Control Center
        // and notification-centre glasses are a 1x1 actor whose real rect lives
        // in the dock_* uniforms, so get_size() said 1 and the uv was junk.
        const [gx, gy] = glass.get_transformed_position();
        const [gw, gh] = glass.get_transformed_size();
        if (!(gw >= 1) || !(gh >= 1))
            return;
        const ux = (px - gx) / gw;
        const uy = (py - gy) / gh;
        if (sample === null)
            sample = `${ux.toFixed(2)},${uy.toFixed(2)}`;
        const near = ux > -MARGIN && ux < 1 + MARGIN &&
            uy > -MARGIN && uy < 1 + MARGIN;
        const wasNear = glass._cursorNear === true;
        glass._cursorNear = near;
        // Far away and already faded out: there is nothing to redraw there.
        if (!near && !wasNear)
            return;
        glass.setCursorLight(ux, uy, RADIUS_PX);
        touched++;
    });
    // One line per session, and only from a pass that resolved a position.
    if (!_announced && sample !== null) {
        _announced = true;
        const line = `cursor light: ${touched}/${total} surface(s) updated, ` +
            `pointer at uv ${sample}`;
        try {
            GLib.file_set_contents('/tmp/liquid-glass-cursor-light', line + '\n');
        }
        catch (e) {
        }
        console.warn(`[Liquid Glass] ${line}`);
    }
}

function _tick() {
    if (!_enabled)
        return GLib.SOURCE_CONTINUE;
    const [px, py] = global.get_pointer();
    // A popup opening under a still pointer has a new surface to place, so a
    // change in the number of live glasses counts as movement too.
    let count = 0;
    forEachGlass(() => { count++; });
    if (px === _lastPx && py === _lastPy && count === _lastCount)
        return GLib.SOURCE_CONTINUE;
    _lastPx = px;
    _lastPy = py;
    _lastCount = count;
    _apply(px, py);
    return GLib.SOURCE_CONTINUE;
}

function _readSetting() {
    // If the key cannot be read, stay enabled: the shader's gate is harmless
    // when the uniforms are never written.
    try {
        _enabled = _settings ? _settings.get_boolean('glass-cursor-light') : true;
    }
    catch (e) {
        _enabled = true;
    }
    if (!_enabled) {
        // Park the pointer far away on every surface, so a surface that was
        // lit goes back to its plain edge light even if it never repaints.
        forEachGlass(glass => {
            glass._cursorNear = false;
            if (typeof glass.setCursorLight === 'function')
                glass.setCursorLight(-10.0, -10.0, RADIUS_PX);
        });
    }
}

export function startCursorLight(settings) {
    stopCursorLight();
    _settings = settings ?? null;
    _readSetting();
    if (_settings) {
        _settingsId = _settings.connect('changed::glass-cursor-light', _readSetting);
    }
    _lastPx = Number.NEGATIVE_INFINITY;
    _lastPy = Number.NEGATIVE_INFINITY;
    _lastCount = -1;
    _timerId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, INTERVAL_MS, _tick);
}

export function stopCursorLight() {
    if (_timerId) {
        GLib.Source.remove(_timerId);
        _timerId = 0;
    }
    if (_settingsId) {
        _settings?.disconnect(_settingsId);
        _settingsId = 0;
    }
    _settings = null;
    _enabled = true;
    _announced = false;
    _lastCount = -1;
}
