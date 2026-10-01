// static/js/core/icons.js
// Icons from the vendored Tabler sprite (static/icons/sprite.svg). Names are
// sprite ids from scripts/build_icon_sprite.py -- always literals in code,
// never data from a file or the server.
const SVG_NS = 'http://www.w3.org/2000/svg';

function spriteUrl() {
    const meta = document.querySelector('meta[name="netgrader-icons"]');
    return meta ? meta.content : '/static/icons/sprite.svg';
}

// A decorative icon is hidden from screen readers; pass a label when the icon
// is the only thing that says what something means.
export function icon(id, { label } = {}) {
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('class', 'icon');
    if (label) {
        svg.setAttribute('role', 'img');
        svg.setAttribute('aria-label', label);
    } else {
        svg.setAttribute('aria-hidden', 'true');
    }
    const use = document.createElementNS(SVG_NS, 'use');
    use.setAttribute('href', `${spriteUrl()}#${id}`);
    svg.appendChild(use);
    return svg;
}

// For legacy/app.js templates that still build markup strings.
export function iconMarkup(id) {
    if (!/^[a-z-]+$/.test(id)) throw new Error(`invalid icon name: ${id}`);
    return `<svg class="icon" aria-hidden="true"><use href="${spriteUrl()}#${id}"></use></svg>`;
}
