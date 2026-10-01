// static/js/display-boot.js
// Classic ES5 script, loaded in <head> before any stylesheet paints. Applies
// the saved display settings as attributes on <html> so the first frame is
// already in the right theme and size, and exposes window.NetgraderDisplay for
// the Display menu (static/js/shell/display-menu.js). Settings are personal
// preferences, kept per browser in localStorage; any storage failure falls
// back to defaults.
(function (w, d) {
    var KEY = 'netgrader.display';
    var DEFAULTS = { textSize: 'md', theme: 'dark', contrast: 'standard', motion: 'system' };
    var ALLOWED = {
        textSize: ['sm', 'md', 'lg', 'xl'],
        theme: ['dark', 'light', 'system'],
        contrast: ['standard', 'high'],
        motion: ['system', 'reduce']
    };

    function normalize(raw) {
        var out = {};
        var source = (raw && typeof raw === 'object' && !(raw instanceof Array)) ? raw : {};
        for (var key in DEFAULTS) {
            if (!DEFAULTS.hasOwnProperty(key)) { continue; }
            var value = source[key];
            out[key] = ALLOWED[key].indexOf(value) !== -1 ? value : DEFAULTS[key];
        }
        return out;
    }

    function resolve(settings, env) {
        var s = normalize(settings);
        return {
            theme: s.theme === 'system' ? (env.prefersLight ? 'light' : 'dark') : s.theme,
            contrast: s.contrast,
            textSize: s.textSize,
            motion: (s.motion === 'reduce' || (s.motion === 'system' && env.prefersReducedMotion)) ? 'reduce' : 'full'
        };
    }

    function storage() {
        try { return w.localStorage || null; } catch (e) { return null; }
    }

    function load() {
        var store = storage();
        if (!store) { return normalize({}); }
        try { return normalize(JSON.parse(store.getItem(KEY) || '{}')); } catch (e) { return normalize({}); }
    }

    function save(settings) {
        var store = storage();
        if (!store) { return; }
        try { store.setItem(KEY, JSON.stringify(normalize(settings))); } catch (e) { /* storage full or blocked */ }
    }

    function query(q) {
        return !!(w.matchMedia && w.matchMedia(q).matches);
    }

    function apply(settings) {
        var r = resolve(settings, {
            prefersLight: query('(prefers-color-scheme: light)'),
            prefersReducedMotion: query('(prefers-reduced-motion: reduce)')
        });
        var el = d.documentElement;
        el.setAttribute('data-theme', r.theme);
        el.setAttribute('data-contrast', r.contrast);
        el.setAttribute('data-text-size', r.textSize);
        el.setAttribute('data-motion', r.motion);
        return r;
    }

    var api = { KEY: KEY, DEFAULTS: DEFAULTS, normalize: normalize, resolve: resolve, load: load, save: save, apply: apply };
    w.NetgraderDisplay = api;
    apply(load());

    // "Follow system" must track the computer's setting while the page is open.
    if (w.matchMedia) {
        var queries = ['(prefers-color-scheme: light)', '(prefers-reduced-motion: reduce)'];
        for (var i = 0; i < queries.length; i++) {
            var mql = w.matchMedia(queries[i]);
            var onChange = function () { apply(load()); };
            if (mql.addEventListener) { mql.addEventListener('change', onChange); }
            else if (mql.addListener) { mql.addListener(onChange); }
        }
    }
})(window, document);
