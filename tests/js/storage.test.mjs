// tests/js/storage.test.mjs
import { test, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readStored, writeStored } from '../../static/js/core/storage.js';

afterEach(() => { delete globalThis.localStorage; });

test('no localStorage at all: nothing throws, reads are null', () => {
    delete globalThis.localStorage;
    assert.equal(readStored('k'), null);
    assert.doesNotThrow(() => writeStored('k', 'v'));
});

test('a throwing localStorage getter (blocked site data) is survived', () => {
    Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        get() { throw new DOMException('denied', 'SecurityError'); },
    });
    assert.equal(readStored('k'), null);
    assert.doesNotThrow(() => writeStored('k', 'v'));
});

test('throwing getItem and setItem are survived', () => {
    globalThis.localStorage = {
        getItem() { throw new Error('quota'); },
        setItem() { throw new Error('quota'); },
    };
    assert.equal(readStored('k'), null);
    assert.doesNotThrow(() => writeStored('k', 'v'));
});

test('a working localStorage round-trips', () => {
    const m = new Map();
    globalThis.localStorage = { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)) };
    writeStored('k', 'v');
    assert.equal(readStored('k'), 'v');
});
