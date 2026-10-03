// tests/js/core.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { escapeHtml, el } from '../../static/js/core/dom.js';
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

function fakeDocument() {
    class FakeNode {
        constructor(tag) { this.tagName = tag; this.attributes = {}; this.childNodes = []; this.className = ''; this.textContent = ''; }
        setAttribute(k, v) { this.attributes[k] = v; }
        appendChild(c) { this.childNodes.push(c); return c; }
    }
    return { createElement: (t) => new FakeNode(t), createTextNode: (t) => ({ nodeType: 3, data: t }) };
}

test('el sets className, text and attributes, skipping null and false', () => {
    globalThis.document = fakeDocument();
    const node = el('button', { className: 'btn', text: 'Go', type: 'button', hidden: true, title: null, disabled: false, tabindex: 0 });
    assert.equal(node.className, 'btn');
    assert.equal(node.textContent, 'Go');
    assert.deepEqual(node.attributes, { type: 'button', hidden: '', tabindex: '0' });
    delete globalThis.document;
});

test('el turns string children into text nodes, never markup', () => {
    globalThis.document = fakeDocument();
    const child = el('span');
    const node = el('li', {}, ['<img src=x onerror=alert(1)>', null, child]);
    assert.equal(node.childNodes.length, 2);
    assert.deepEqual(node.childNodes[0], { nodeType: 3, data: '<img src=x onerror=alert(1)>' });
    assert.equal(node.childNodes[1], child);
    delete globalThis.document;
});
