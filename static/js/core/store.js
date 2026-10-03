// static/js/core/store.js
// The last report, selection and screen, kept for this browser tab (issue #29).
// sessionStorage, so it is gone when the browser closes. Never throws: a
// private window, blocked site data or a full quota means nothing is kept.

const PREFIX = 'netgrader:';
const SCREENS = ['discovery', 'instructor', 'grading'];

// Returns false when the value could not be kept (unavailable or too large).
// An older value under the same key is removed then, so a refresh never
// brings back something the caller has since replaced.
export function saveSession(key, value) {
    try {
        sessionStorage.setItem(PREFIX + key, JSON.stringify(value));
        return true;
    } catch (e) {
        clearSession(key);
        return false;
    }
}

export function loadSession(key) {
    try {
        const raw = sessionStorage.getItem(PREFIX + key);
        return raw == null ? null : JSON.parse(raw);
    } catch (e) {
        return null;
    }
}

export function clearSession(key) {
    try {
        sessionStorage.removeItem(PREFIX + key);
    } catch (e) {
        // Nothing was kept, so there is nothing to clear.
    }
}

// "#grading/ip_r1_g0_0" -> { screen: 'grading', selection: 'ip_r1_g0_0' }.
// Anything unrecognised reads as no screen, so the caller keeps its own.
export function parseHash(hash) {
    const body = String(hash || '').replace(/^#/, '');
    const slash = body.indexOf('/');
    const screen = slash < 0 ? body : body.slice(0, slash);
    if (SCREENS.indexOf(screen) < 0) return { screen: null, selection: null };
    let selection = null;
    if (slash >= 0 && body.length > slash + 1) {
        try {
            selection = decodeURIComponent(body.slice(slash + 1));
        } catch (e) {
            selection = null;
        }
    }
    return { screen, selection };
}

export function formatHash(screen, selection) {
    return selection ? `#${screen}/${encodeURIComponent(selection)}` : `#${screen}`;
}
