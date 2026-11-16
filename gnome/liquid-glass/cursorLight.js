// Keeps the glass edge light following the pointer. A motion listener stores
// the position and, at most every INTERVAL_MS, hands it to every live glass;
// the shader does the rest (see CURSOR_MIN_LIGHT in shaders/glass.frag).
//
// Cost: one signal callback that does nothing but schedule a timeout, then one
// loop per tick over the live glasses. Only surfaces near the pointer are
// repainted, and only while it moves.
import GLib from 'gi://GLib';
import { forEachGlass } from '../diagnostics/glass.js';

// ~30 Hz. A 60 Hz update would make the highlight smoother at the price of
// twice the paint passes, and the eye does not tell them apart on a rim.
const INTERVAL_MS = 33;
// Reach of the highlight, in shader pixels.
const RADIUS_PX = 170.0;
// How far outside its own box a glass keeps receiving updates, in uv units.
const MARGIN = 0.15;

let _motionId = 0;
let _tickId = 0;
let _settingsId = 0;
let _settings = null;
let _enabled = false;

function _apply() {
    const [px, py] = global.get_pointer();
    forEachGlass(glass => {
        if (!glass.mapped || !glass.has_allocation())
            return;
        const [ok, lx, ly] = glass.transform_stage_point(px, py);
        if (!ok)
            return;
        const [w, h] = glass.get_size();
        if (!(w >= 1) || !(h >= 1))
            return;
        const ux = lx / w;
        const uy = ly / h;
        const near = ux > -MARGIN && ux < 1 + MARGIN &&
            uy > -MARGIN && uy < 1 + MARGIN;
        const wasNear = glass._cursorNear === true;
        glass._cursorNear = near;
        // Far away and already faded out: there is nothing to redraw there.
        if (!near && !wasNear)
            return;
        // Quick Settings toggles use a different class without this setter.
        if (typeof glass.setCursorLight !== 'function')
            return;
        glass.setCursorLight(ux, uy, RADIUS_PX);
    });
}

function _schedule() {
    if (!_enabled || _tickId)
        return;
    _tickId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, INTERVAL_MS, () => {
        _tickId = 0;
        _apply();
        return GLib.SOURCE_REMOVE;
    });
}

function _readSetting() {
    _enabled = _settings ? _settings.get_boolean('glass-cursor-light') : false;
    if (!_enabled) {
        // The uniform itself is cleared by MaterialSettings; this only keeps the
        // next enable from repainting surfaces the pointer never visited.
        forEachGlass(glass => { glass._cursorNear = false; });
    }
}

function _onMotion() {
    _schedule();
    // Not handled: the event must keep travelling to whatever is under it.
    return false;
}

export function startCursorLight(settings) {
    stopCursorLight();
    _settings = settings ?? null;
    _readSetting();
    if (_settings) {
        _settingsId = _settings.connect('changed::glass-cursor-light', () => {
            _readSetting();
        });
    }
    _motionId = global.stage.connect('motion-event', _onMotion);
}

export function stopCursorLight() {
    if (_motionId) {
        global.stage.disconnect(_motionId);
        _motionId = 0;
    }
    if (_settingsId) {
        _settings?.disconnect(_settingsId);
        _settingsId = 0;
    }
    if (_tickId) {
        GLib.Source.remove(_tickId);
        _tickId = 0;
    }
    _settings = null;
    _enabled = false;
}
