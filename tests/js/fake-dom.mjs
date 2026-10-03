// tests/js/fake-dom.mjs
// The smallest DOM the report components need under Node: elements, text,
// attributes, events with bubbling, focus, and querySelector for simple
// selectors (tag, .class, #id, [attr="value"], joined by spaces).

class FakeNode {
    constructor(doc) { this.ownerDocument = doc; this.parentNode = null; this.childNodes = []; }
    appendChild(child) {
        if (child.parentNode) child.parentNode.removeChild(child);
        child.parentNode = this;
        this.childNodes.push(child);
        return child;
    }
    removeChild(child) {
        this.childNodes = this.childNodes.filter(c => c !== child);
        child.parentNode = null;
        return child;
    }
    get textContent() { return this.childNodes.map(c => c.textContent).join(''); }
    set textContent(value) {
        this.childNodes.forEach(c => { c.parentNode = null; });
        this.childNodes = [];
        if (value !== '' && value != null) this.appendChild(new FakeText(this.ownerDocument, String(value)));
    }
}

class FakeText extends FakeNode {
    constructor(doc, data) { super(doc); this.nodeType = 3; this.data = data; }
    get textContent() { return this.data; }
}

class FakeElement extends FakeNode {
    constructor(doc, tag) {
        super(doc);
        this.nodeType = 1;
        this.tagName = tag.toUpperCase();
        this.attributes = {};
        this.listeners = {};
        this.style = {};
    }
    get className() { return this.attributes.class || ''; }
    set className(v) { this.attributes.class = String(v); }
    get id() { return this.attributes.id || ''; }
    get hidden() { return 'hidden' in this.attributes; }
    set hidden(v) { if (v) this.attributes.hidden = ''; else delete this.attributes.hidden; }
    get children() { return this.childNodes.filter(c => c.nodeType === 1); }
    setAttribute(k, v) { this.attributes[k] = String(v); }
    getAttribute(k) { return k in this.attributes ? this.attributes[k] : null; }
    removeAttribute(k) { delete this.attributes[k]; }
    hasAttribute(k) { return k in this.attributes; }
    addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); }
    dispatchEvent(event) {
        event.target = event.target || this;
        for (let node = this; node && !event.stopped; node = node.parentNode) {
            (node.listeners && node.listeners[event.type] || []).forEach(fn => fn(event));
        }
        return !event.defaultPrevented;
    }
    click() { this.dispatchEvent(fakeEvent('click')); }
    focus() { this.ownerDocument.activeElement = this; }
    querySelectorAll(selector) {
        const out = [];
        const walk = node => node.children.forEach(child => {
            if (matches(child, selector)) out.push(child);
            walk(child);
        });
        walk(this);
        return out;
    }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}

function matchesCompound(node, compound) {
    const parts = compound.match(/^[a-z]+|\.[\w-]+|#[\w-]+|\[[\w-]+(="[^"]*")?\]/gi) || [];
    if (parts.join('') !== compound) throw new Error(`fake-dom cannot parse selector: ${compound}`);
    return parts.every(p => {
        if (p[0] === '.') return node.className.split(/\s+/).indexOf(p.slice(1)) >= 0;
        if (p[0] === '#') return node.id === p.slice(1);
        if (p[0] === '[') {
            const m = p.match(/^\[([\w-]+)(?:="([^"]*)")?\]$/);
            return m[2] === undefined ? node.hasAttribute(m[1]) : node.getAttribute(m[1]) === m[2];
        }
        return node.tagName === p.toUpperCase();
    });
}

function matches(node, selector) {
    const chain = selector.trim().split(/\s+/);
    if (!matchesCompound(node, chain[chain.length - 1])) return false;
    let i = chain.length - 2;
    for (let up = node.parentNode; up && i >= 0; up = up.parentNode) {
        if (up.nodeType === 1 && matchesCompound(up, chain[i])) i--;
    }
    return i < 0;
}

export function fakeEvent(type, props = {}) {
    return {
        type, defaultPrevented: false, stopped: false, ...props,
        preventDefault() { this.defaultPrevented = true; },
        stopPropagation() { this.stopped = true; },
    };
}

// Installs a fresh fake document on globalThis and returns it.
export function installFakeDocument() {
    const doc = {
        activeElement: null,
        createElement: tag => new FakeElement(doc, tag),
        createElementNS: (_ns, tag) => new FakeElement(doc, tag),
        createTextNode: text => new FakeText(doc, text),
        querySelector: () => null,
    };
    doc.body = new FakeElement(doc, 'body');
    globalThis.document = doc;
    return doc;
}
