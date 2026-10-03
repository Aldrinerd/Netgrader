// tests/js/display-boot.test.mjs
// display-boot.js is a classic script, so it is loaded into a fake browser
// with Node's vm module rather than imported.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const SRC = readFileSync(new URL('../../static/js/display-boot.js', import.meta.url), 'utf8');

function boot({ stored, storageThrows = false, prefersLight = false, reduced = false } = {}) {
    const attrs = {};
    const listeners = [];
    const media = {
        '(prefers-color-scheme: light)': { matches: prefersLight },
        '(prefers-reduced-motion: reduce)': { matches: reduced },
    };
    const store = new Map(stored === undefined ? [] : [['netgrader.display', stored]]);
    const localStorage = {
        getItem: k => { if (storageThrows) throw new Error('blocked'); return store.has(k) ? store.get(k) : null; },
        setItem: (k, v) => { if (storageThrows) throw new Error('blocked'); store.set(k, v); },
    };
    const window = {
        matchMedia: q => ({
            get matches() { return media[q].matches; },
            addEventListener: (_t, fn) => listeners.push({ q, fn }),
        }),
    };
    Object.defineProperty(window, 'localStorage', {
        get() { if (storageThrows) throw new Error('SecurityError'); return localStorage; },
    });
    const document = { documentElement: { setAttribute: (k, v) => { attrs[k] = v; } } };
    vm.runInNewContext(SRC, { window, document });
    return { api: window.NetgraderDisplay, attrs, store, media, listeners };
}

test('applies defaults when nothing is stored', () => {
    const { attrs } = boot();
    assert.deepEqual(attrs, { 'data-theme': 'dark', 'data-contrast': 'standard', 'data-text-size': 'md', 'data-motion': 'full' });
});

test('applies stored settings before the page draws', () => {
    const { attrs } = boot({ stored: JSON.stringify({ theme: 'light', contrast: 'high', textSize: 'xl', motion: 'reduce' }) });
    assert.deepEqual(attrs, { 'data-theme': 'light', 'data-contrast': 'high', 'data-text-size': 'xl', 'data-motion': 'reduce' });
});

test('corrupt or hostile stored values fall back to defaults', () => {
    for (const stored of ['not json', '[]', '"x"', JSON.stringify({ theme: 'neon', textSize: 99, contrast: null })]) {
        const { attrs } = boot({ stored });
        assert.equal(attrs['data-theme'], 'dark');
        assert.equal(attrs['data-text-size'], 'md');
        assert.equal(attrs['data-contrast'], 'standard');
    }
});

test('blocked storage still loads with defaults and saving does not throw', () => {
    const { api, attrs } = boot({ storageThrows: true });
    assert.equal(attrs['data-theme'], 'dark');
    assert.doesNotThrow(() => api.save({ theme: 'light' }));
});

test('follow system resolves from the media query', () => {
    const { attrs } = boot({ stored: JSON.stringify({ theme: 'system' }), prefersLight: true, reduced: true });
    assert.equal(attrs['data-theme'], 'light');
    assert.equal(attrs['data-motion'], 'reduce');
});

test('follow system updates live when the computer switches theme', () => {
    const { attrs, media, listeners } = boot({ stored: JSON.stringify({ theme: 'system' }) });
    assert.equal(attrs['data-theme'], 'dark');
    media['(prefers-color-scheme: light)'].matches = true;
    listeners.filter(l => l.q === '(prefers-color-scheme: light)').forEach(l => l.fn());
    assert.equal(attrs['data-theme'], 'light');
});

test('save then load round-trips through storage', () => {
    const { api, store } = boot();
    api.save({ theme: 'light', textSize: 'lg', contrast: 'standard', motion: 'system' });
    assert.equal(JSON.parse(store.get('netgrader.display')).textSize, 'lg');
    assert.equal(api.load().theme, 'light');
});
