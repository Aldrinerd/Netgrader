// static/js/core/dom.js
// The only module allowed to build markup from strings, and the home of el(),
// which builds nodes without any. Anything taken from an uploaded file (device
// names, descriptions, config lines) or a filename must pass through
// escapeHtml before reaching innerHTML (issue #31).

// Escapes for both element content and quoted attribute values.
export function escapeHtml(text) {
    return (text == null ? '' : String(text))
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Builds an element without parsing HTML, so values from a file can never
// become markup. attrs: className, text (textContent), and any other key as
// an attribute -- null/false skipped, true as an empty attribute. Children
// are nodes or strings; strings become text nodes.
export function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
        if (value == null || value === false) continue;
        if (key === 'className') node.className = value;
        else if (key === 'text') node.textContent = value;
        else node.setAttribute(key, value === true ? '' : String(value));
    }
    for (const child of [].concat(children)) {
        if (child == null || child === false) continue;
        node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
    }
    return node;
}
