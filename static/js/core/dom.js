// static/js/core/dom.js
// The only module allowed to build markup from strings. Anything taken from
// an uploaded file (device names, descriptions, config lines) or a filename
// must pass through escapeHtml before reaching innerHTML (issue #31).

// Escapes for both element content and quoted attribute values.
export function escapeHtml(text) {
    return (text == null ? '' : String(text))
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
