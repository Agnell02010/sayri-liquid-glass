// Keeps the glass edge light following the pointer. A captured-event listener
// does nothing but schedule a timeout; at most every INTERVAL_MS the last
// position is handed to the live glasses, and the shader does the rest (see
// CURSOR_MIN_LIGHT in shaders/glass.frag).
//
// captured-event rather than motion-event: motion-event only reaches the stage
// if no actor on the way stops its propagation, and plenty of them do.
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

let _eventId = 0;
let _tickId = 0;
let _settingsId = 0;
let _settings = null;
let _enabled = true;
let _announced = false;

function _apply() {
    const [px, py] = global.get_pointer();
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
        // in the dock_* uniforms, so get_size() returned 1 and the uv was junk.
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
    // One line per session, and only from a pass that actually resolved a
    // position: the first idle pass runs before the surfaces are mapped and
    // would report an empty run. console.debug never reaches the journal, so it
    // goes to a file too, which is how the plumbing was traced.
    if (!_announced && sample !== null) {
        _announced = true;
        const line = `cursor light: ${touched}/${total} surface(s) updated, ` +
            `pointer at uv ${sample ?? 'n/a'}`;
        try {
            GLib.file_set_contents('/tmp/liquid-glass-cursor-light', line + '\n');
        }
        catch (e) {
        }
        console.warn(`[Liquid Glass] ${line}`);
    }
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
    // If the key cannot be read, stay enabled: the shader's gate is harmless
    // when the uniforms are never written.
    try {
        _enabled = _settings ? _settings.get_boolean('glass-cursor-light') : true;
    }
    catch (e) {
        _enabled = true;
    }
    if (!_enabled) {
        // The uniform itself is cleared by MaterialSettings; this only keeps the
        // next enable from repainting surfaces the pointer never visited.
        forEachGlass(glass => { glass._cursorNear = false; });
    }
}

function _onEvent() {
    _schedule();
    // Not handled: the event must keep travelling to whatever is under it.
    return false;
}

export function startCursorLight(settings) {
    stopCursorLight();
    _settings = settings ?? null;
    _readSetting();
    if (_settings) {
        _settingsId = _settings.connect('changed::glass-cursor-light', _readSetting);
    }
    _eventId = global.stage.connect('captured-event', _onEvent);
    // One pass without waiting for a pointer event, so the edge is already right
    // at login.
    GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
        if (_enabled)
            _apply();
        return GLib.SOURCE_REMOVE;
    });
}

export function stopCursorLight() {
    if (_eventId) {
        global.stage.disconnect(_eventId);
        _eventId = 0;
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
    _enabled = true;
    _announced = false;
}
