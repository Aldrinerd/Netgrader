// static/js/map/svg-shapes.js
// SVG building blocks for the topology map. Pure functions: no module state.

// Short interface names for map labels.
export function shortInterfaceName(name) {
    if (!name || name === 'Unspecified') return '';
    return name
        .replace(/^GigabitEthernet/i, 'Gi')
        .replace(/^FastEthernet/i, 'Fa')
        .replace(/^Ethernet/i, 'Eth')
        .replace(/^Serial/i, 'Se')
        .replace(/^Loopback/i, 'Lo')
        .replace(/^Vlan/i, 'Vl')
        .replace(/^Port-channel/i, 'Po');
}

export function createSvgBadge(x, y, text, badgeClass = 'port-label-badge', isIp = false) {
    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.classList.add(badgeClass);

    const charWidth = isIp ? 5.8 : 6.4;
    const width = Math.max(26, text.length * charWidth + 8);
    const height = 15;

    const rectElem = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rectElem.setAttribute('x', x - width / 2);
    rectElem.setAttribute('y', y - height / 2);
    rectElem.setAttribute('width', width);
    rectElem.setAttribute('height', height);
    rectElem.setAttribute('rx', '3');
    rectElem.setAttribute('ry', '3');
    rectElem.setAttribute('fill', isIp ? '#064E3B' : '#0F172A');
    rectElem.setAttribute('stroke', isIp ? '#10B981' : '#3B82F6');
    rectElem.setAttribute('stroke-width', '1');

    const textElem = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    textElem.setAttribute('x', x);
    textElem.setAttribute('y', y + 3.5);
    textElem.setAttribute('text-anchor', 'middle');
    textElem.setAttribute('font-family', 'JetBrains Mono, monospace');
    textElem.setAttribute('font-size', isIp ? '9px' : '9.5px');
    textElem.setAttribute('font-weight', '600');
    textElem.setAttribute('fill', isIp ? '#6EE7B7' : '#93C5FD');
    textElem.textContent = text;

    group.appendChild(rectElem);
    group.appendChild(textElem);
    return group;
}

/**
 * Device icons drawn as silhouettes instead of lettered circles: a short
 * cylinder for routers, a flat box with a port row for switches, and a
 * monitor on a stand for PCs. Everything is centred on (x, y) and stays
 * inside the r=26 glow, so node spacing, dragging and hit areas are
 * unchanged from the circle they replace.
 */
export function createDeviceIcon(x, y, color, kind) {
    const NS = 'http://www.w3.org/2000/svg';
    const group = document.createElementNS(NS, 'g');

    const shape = (name, attrs) => {
        const el = document.createElementNS(NS, name);
        const merged = Object.assign({ fill: '#1F2937', stroke: color, 'stroke-width': 2 }, attrs);
        for (const [key, value] of Object.entries(merged)) el.setAttribute(key, value);
        // A device we only inferred is outlined, never solid.
        if (kind.isPlaceholder) el.setAttribute('stroke-dasharray', '4,3');
        group.appendChild(el);
        return el;
    };

    const caption = (content, dy, size) => {
        const el = document.createElementNS(NS, 'text');
        el.setAttribute('x', x);
        el.setAttribute('y', y + dy);
        el.setAttribute('text-anchor', 'middle');
        el.setAttribute('fill', color);
        el.setAttribute('font-size', size + 'px');
        el.setAttribute('font-weight', 'bold');
        el.setAttribute('font-family', 'Outfit, sans-serif');
        el.textContent = content;
        group.appendChild(el);
        return el;
    };

    if (kind.isPlaceholder) {
        shape('circle', { cx: x, cy: y, r: 20 });
        caption('?', 4, 10.5);
        return group;
    }

    if (kind.isHost) {
        shape('rect', { x: x - 17, y: y - 14, width: 34, height: 23, rx: 2.5 });
        shape('rect', {
            x: x - 12.5, y: y - 9.5, width: 25, height: 14, rx: 1,
            fill: color, 'fill-opacity': 0.22, stroke: 'none', 'stroke-width': 0
        });
        shape('rect', { x: x - 4, y: y + 9, width: 8, height: 4, 'stroke-width': 1.5 });
        shape('line', {
            x1: x - 12, y1: y + 14.5, x2: x + 12, y2: y + 14.5,
            fill: 'none', 'stroke-width': 2.5, 'stroke-linecap': 'round'
        });
        return group;
    }

    if (kind.isSwitch) {
        shape('rect', { x: x - 23, y: y - 11, width: 46, height: 22, rx: 3 });
        for (let i = 0; i < 5; i++) {
            shape('rect', {
                x: x - 17 + i * 7, y: y + 3, width: 4, height: 4, rx: 0.5,
                fill: color, 'fill-opacity': 0.55, stroke: 'none', 'stroke-width': 0
            });
        }
        if (kind.isL3Switch) caption('L3', -1.5, 8.5);
        return group;
    }

    // Router: a short cylinder. Body silhouette first, then the top rim
    // ellipse over it so the near edge of the lid reads correctly.
    const rx = 20;
    const ry = 6;
    const half = 9;
    shape('path', {
        d: `M ${x - rx} ${y - half}`
            + ` L ${x - rx} ${y + half}`
            + ` A ${rx} ${ry} 0 0 0 ${x + rx} ${y + half}`
            + ` L ${x + rx} ${y - half}`
            + ` A ${rx} ${ry} 0 0 0 ${x - rx} ${y - half} Z`
    });
    shape('ellipse', { cx: x, cy: y - half, rx: rx, ry: ry });
    return group;
}
