// static/js/core/storage.js
// localStorage that never throws. Where site data is blocked, merely reading
// window.localStorage raises SecurityError; callers must carry on without it.

export function readStored(key) {
    try {
        return localStorage.getItem(key);
    } catch (e) {
        return null;
    }
}

export function writeStored(key, value) {
    try {
        localStorage.setItem(key, value);
    } catch (e) {
        // Storage unavailable or full: the setting simply isn't remembered.
    }
}
