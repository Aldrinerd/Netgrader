// tests/js/store.test.mjs
import { test, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { saveSession, loadSession, clearSession, parseHash, formatHash } from '../../static/js/core/store.js';

afterEach(() => { delete globalThis.sessionStorage; });

function memoryStorage() {
    const m = new Map();
    return {
        getItem: (k) => (m.has(k) ? m.get(k) : null),
        setItem: (k, v) => m.set(k, String(v)),
        removeItem: (k) => m.delete(k),
        _map: m,
    };
}

test('round-trips JSON under a namespaced key', () => {
    globalThis.sessionStorage = memoryStorage();
    assert.equal(saveSession('grading', { a: [1, 2] }), true);
    assert.deepEqual(loadSession('grading'), { a: [1, 2] });
    assert.ok(globalThis.sessionStorage._map.has('netgrader:grading'));
    clearSession('grading');
    assert.equal(loadSession('grading'), null);
});

test('no sessionStorage, a throwing getter, or a full quota never throws', () => {
    delete globalThis.sessionStorage;     // newer Node versions ship a global one
    assert.equal(saveSession('k', 1), false);
    assert.equal(loadSession('k'), null);
    assert.doesNotThrow(() => clearSession('k'));

    Object.defineProperty(globalThis, 'sessionStorage', {
        configurable: true,
        get() { throw new DOMException('denied', 'SecurityError'); },
    });
    assert.equal(saveSession('k', 1), false);
    assert.equal(loadSession('k'), null);
    delete globalThis.sessionStorage;

    globalThis.sessionStorage = { setItem() { throw new DOMException('full', 'QuotaExceededError'); }, getItem: () => null, removeItem() {} };
    assert.equal(saveSession('k', { big: 'x' }), false);
});

test('a save that fails leaves no older value behind', () => {
    // Otherwise a refresh would bring back the previous report, not the one
    // just graded.
    globalThis.sessionStorage = memoryStorage();
    saveSession('grading', { report: 'old' });
    const storage = globalThis.sessionStorage;
    storage.setItem = () => { throw new DOMException('full', 'QuotaExceededError'); };
    assert.equal(saveSession('grading', { report: 'new' }), false);
    assert.equal(loadSession('grading'), null);
});

test('a stored value that is not JSON reads as nothing', () => {
    globalThis.sessionStorage = memoryStorage();
    globalThis.sessionStorage.setItem('netgrader:k', '{not json');
    assert.equal(loadSession('k'), null);
});

test('parseHash reads screen and selection', () => {
    assert.deepEqual(parseHash('#grading/ip_r1_g0_0'), { screen: 'grading', selection: 'ip_r1_g0_0' });
    assert.deepEqual(parseHash('#discovery'), { screen: 'discovery', selection: null });
    assert.deepEqual(parseHash('#grading/'), { screen: 'grading', selection: null });
    assert.deepEqual(parseHash(''), { screen: null, selection: null });
    assert.deepEqual(parseHash('#somewhere-else'), { screen: null, selection: null });
});

test('parseHash survives a malformed escape', () => {
    assert.deepEqual(parseHash('#grading/%E0%A4%A'), { screen: 'grading', selection: null });
});

test('formatHash encodes the selection and round-trips', () => {
    assert.equal(formatHash('grading', 'a b/c'), '#grading/a%20b%2Fc');
    assert.equal(formatHash('discovery'), '#discovery');
    assert.deepEqual(parseHash(formatHash('grading', 'a b/c')), { screen: 'grading', selection: 'a b/c' });
});
