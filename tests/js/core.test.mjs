// tests/js/core.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { escapeHtml } from '../../static/js/core/dom.js';
import { describeFailure } from '../../static/js/core/api.js';

test('escapeHtml escapes the five HTML-significant characters', () => {
    assert.equal(escapeHtml(`<a href="x" title='y'>&</a>`),
        '&lt;a href=&quot;x&quot; title=&#39;y&#39;&gt;&amp;&lt;/a&gt;');
});

test('escapeHtml turns null and undefined into an empty string', () => {
    assert.equal(escapeHtml(null), '');
    assert.equal(escapeHtml(undefined), '');
});

test('escapeHtml stringifies numbers', () => {
    assert.equal(escapeHtml(82.5), '82.5');
});

const fakeResponse = (body, { json = true, status = 500, statusText = 'Server Error' } = {}) => ({
    status, statusText,
    json: async () => { if (!json) throw new SyntaxError('not json'); return body; },
});

test('describeFailure returns a string detail', async () => {
    assert.equal(await describeFailure(fakeResponse({ detail: 'bad file' })), 'bad file');
});

test('describeFailure serialises a structured detail', async () => {
    assert.equal(await describeFailure(fakeResponse({ detail: [{ loc: ['x'] }] })), '[{"loc":["x"]}]');
});

test('describeFailure falls back when the body is not JSON', async () => {
    assert.equal(await describeFailure(fakeResponse(null, { json: false }), 'Upload failed'), 'Upload failed');
    assert.equal(await describeFailure(fakeResponse(null, { json: false })), 'Server error 500 Server Error');
});
