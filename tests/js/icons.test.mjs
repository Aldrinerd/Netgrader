// tests/js/icons.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';

globalThis.document = { querySelector: () => ({ content: '/static/icons/sprite.svg?v=7' }) };
const { iconMarkup } = await import('../../static/js/core/icons.js');

test('iconMarkup points at the versioned sprite', () => {
    assert.equal(iconMarkup('check'),
        '<svg class="icon" aria-hidden="true"><use href="/static/icons/sprite.svg?v=7#check"></use></svg>');
});

test('iconMarkup refuses anything that is not a plain icon id', () => {
    for (const bad of ['"><img src=x>', 'Check', 'a b', '']) {
        assert.throws(() => iconMarkup(bad));
    }
});
