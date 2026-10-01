// static/js/map/topology.js
// The interactive topology map: layout, drawing, zoom, pan and node drag.
// Owns all map state; the rest of the UI talks to it through the returned API.
import { createSvgBadge, createDeviceIcon, shortInterfaceName } from './svg-shapes.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

export function createTopologyMap(svg, { onNodeSelect = () => {}, onLinkSelect = () => {} } = {}) {
    let topology = null;
    let nodes = [];
    let links = [];
    let highlighted = new Set();
    let view = { x: 0, y: 0, k: 1 };
    let labels = { ports: true, ips: false };
    let draggedNode = null;
    let isPanning = false;
    let panStartX = 0;
    let panStartY = 0;

    function applyTransform() {
        const g = svg.querySelector('#graph-root');
        if (g) g.setAttribute('transform', `translate(${view.x}, ${view.y}) scale(${view.k})`);
    }

    function render(data, { highlightDevices = [] } = {}) {
        topology = data;
        highlighted = new Set(highlightDevices);
        // textContent, not replaceChildren(): the latter needs Chrome 86 / Firefox 78 / Safari 14.
        svg.textContent = '';

        const devEntries = Object.entries(data.devices || {});
        const hasCoordinates = devEntries.some(([_, d]) => d.x_coord !== null && d.y_coord !== null);

        if (hasCoordinates) {
            nodes = devEntries.map(([devKey, d]) => ({
                id: devKey,
                device: d,
                x: d.x_coord !== null ? d.x_coord : 400,
                y: d.y_coord !== null ? d.y_coord : 300,
            }));
        } else {
            const radius = 220;
            const centerX = 450;
            const centerY = 320;
            nodes = devEntries.map(([devKey, d], idx) => {
                const angle = (idx / devEntries.length) * 2 * Math.PI - Math.PI / 2;
                return {
                    id: devKey,
                    device: d,
                    x: centerX + radius * Math.cos(angle),
                    y: centerY + radius * Math.sin(angle),
                };
            });
        }

        links = (data.links || []).map(l => ({
            data: l,
            source: nodes.find(n => n.id === l.source_device) || { x: 200, y: 200, id: l.source_device },
            target: nodes.find(n => n.id === l.target_device) || { x: 400, y: 200, id: l.target_device },
        }));

        fit();
    }

    function fit() {
        if (!nodes || nodes.length === 0) return;

        const rect = svg.getBoundingClientRect();
        const width = rect.width || 800;
        const height = rect.height || 600;

        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        nodes.forEach(n => {
            minX = Math.min(minX, n.x);
            maxX = Math.max(maxX, n.x);
            minY = Math.min(minY, n.y);
            maxY = Math.max(maxY, n.y);
        });

        const graphWidth = (maxX - minX) || 100;
        const graphHeight = (maxY - minY) || 100;
        const graphCenterX = (minX + maxX) / 2;
        const graphCenterY = (minY + maxY) / 2;

        const marginX = Math.max(90, width * 0.10);
        const marginY = Math.max(80, height * 0.12);

        const availableWidth = Math.max(100, width - 2 * marginX);
        const availableHeight = Math.max(100, height - 2 * marginY);

        const scaleX = availableWidth / graphWidth;
        const scaleY = availableHeight / graphHeight;
        let scale = Math.min(scaleX, scaleY);
        scale = Math.max(0.35, Math.min(scale, 1.4));

        view.k = scale;
        view.x = (width / 2) - graphCenterX * scale;
        view.y = (height / 2) - graphCenterY * scale;

        draw();
    }

    function draw() {
        svg.textContent = '';
        const defs = document.createElementNS(SVG_NS, 'defs');
        svg.appendChild(defs);

        const g = document.createElementNS(SVG_NS, 'g');
        g.setAttribute('id', 'graph-root');
        g.setAttribute('transform', `translate(${view.x}, ${view.y}) scale(${view.k})`);
        svg.appendChild(g);

        // 1. Draw Links
        links.forEach(linkObj => {
            const link = linkObj.data;
            const src = linkObj.source;
            const tgt = linkObj.target;

            const lineGroup = document.createElementNS(SVG_NS, 'g');
            lineGroup.classList.add('graph-link-group');
            lineGroup.style.cursor = 'pointer';

            const hasConflict = link.conflicts && link.conflicts.length > 0;
            let strokeColor = '#10B981';
            let strokeDash = 'none';

            if (hasConflict) {
                strokeColor = '#EF4444';
            } else if (link.classification === 'inferred') {
                strokeColor = '#F59E0B';
                strokeDash = '6,4';
            } else if (link.classification === 'unverified') {
                strokeColor = '#6B7280';
                strokeDash = '3,3';
            }

            const line = document.createElementNS(SVG_NS, 'line');
            line.setAttribute('x1', src.x);
            line.setAttribute('y1', src.y);
            line.setAttribute('x2', tgt.x);
            line.setAttribute('y2', tgt.y);
            line.setAttribute('stroke', strokeColor);
            line.setAttribute('stroke-width', hasConflict ? '3.5' : '2.5');
            line.setAttribute('stroke-dasharray', strokeDash);
            line.setAttribute('stroke-linecap', 'round');
            lineGroup.appendChild(line);

            const dx = tgt.x - src.x;
            const dy = tgt.y - src.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const ux = dx / dist;
            const uy = dy / dist;
            const px = -uy;
            const py = ux;

            const midX = (src.x + tgt.x) / 2;
            const midY = (src.y + tgt.y) / 2;

            const badgeBg = document.createElementNS(SVG_NS, 'rect');
            const confText = hasConflict ? 'ERR' : `${Math.round(link.confidence * 100)}%`;
            badgeBg.setAttribute('x', midX - 18);
            badgeBg.setAttribute('y', midY - 9);
            badgeBg.setAttribute('width', '36');
            badgeBg.setAttribute('height', '18');
            badgeBg.setAttribute('rx', '9');
            badgeBg.setAttribute('fill', '#111827');
            badgeBg.setAttribute('stroke', strokeColor);
            badgeBg.setAttribute('stroke-width', '1');
            lineGroup.appendChild(badgeBg);

            const badgeLabel = document.createElementNS(SVG_NS, 'text');
            badgeLabel.setAttribute('x', midX);
            badgeLabel.setAttribute('y', midY + 3.5);
            badgeLabel.setAttribute('text-anchor', 'middle');
            badgeLabel.setAttribute('fill', strokeColor);
            badgeLabel.setAttribute('font-size', '9.5px');
            badgeLabel.setAttribute('font-weight', 'bold');
            badgeLabel.setAttribute('font-family', 'JetBrains Mono, monospace');
            badgeLabel.textContent = confText;
            lineGroup.appendChild(badgeLabel);

            const offsetDist = Math.max(48, Math.min(dist * 0.28, 75));
            const portSideOffset = 13;
            const ipSideOffset = -14;

            // Port Labels
            if (labels.ports) {
                const srcPortText = shortInterfaceName(link.source_interface);
                const tgtPortText = shortInterfaceName(link.target_interface);

                if (srcPortText) {
                    const spX = src.x + ux * offsetDist + px * portSideOffset;
                    const spY = src.y + uy * offsetDist + py * portSideOffset;
                    lineGroup.appendChild(createSvgBadge(spX, spY, srcPortText, 'port-label-badge', false));
                }

                if (tgtPortText) {
                    const tpX = tgt.x - ux * offsetDist + px * portSideOffset;
                    const tpY = tgt.y - uy * offsetDist + py * portSideOffset;
                    lineGroup.appendChild(createSvgBadge(tpX, tpY, tgtPortText, 'port-label-badge', false));
                }
            }

            // IP Address Labels
            if (labels.ips && topology && topology.devices) {
                const srcDev = topology.devices[link.source_device];
                const tgtDev = topology.devices[link.target_device];
                const srcIntf = srcDev?.interfaces?.[link.source_interface];
                const tgtIntf = tgtDev?.interfaces?.[link.target_interface];

                if (srcIntf && srcIntf.ip_address) {
                    const ipText = `${srcIntf.ip_address}/${srcIntf.cidr || 24}`;
                    const sipX = src.x + ux * offsetDist + px * ipSideOffset;
                    const sipY = src.y + uy * offsetDist + py * ipSideOffset;
                    lineGroup.appendChild(createSvgBadge(sipX, sipY, ipText, 'ip-label-badge', true));
                }

                if (tgtIntf && tgtIntf.ip_address) {
                    const ipText = `${tgtIntf.ip_address}/${tgtIntf.cidr || 24}`;
                    const tipX = tgt.x - ux * offsetDist + px * ipSideOffset;
                    const tipY = tgt.y - uy * offsetDist + py * ipSideOffset;
                    lineGroup.appendChild(createSvgBadge(tipX, tipY, ipText, 'ip-label-badge', true));
                }
            }

            lineGroup.addEventListener('click', (e) => {
                e.stopPropagation();
                onLinkSelect(link);
            });

            g.appendChild(lineGroup);
        });

        // 2. Draw Nodes
        nodes.forEach(node => {
            const dev = node.device;
            const nodeGroup = document.createElementNS(SVG_NS, 'g');
            nodeGroup.classList.add('graph-node-group');
            nodeGroup.style.cursor = 'grab';

            const isPlaceholder = dev.is_placeholder || dev.display_name === '???';
            const deviceType = dev.device_type || 'router';
            const isL3Switch = deviceType === 'l3_switch';
            const isSwitch = deviceType === 'switch' || isL3Switch;
            const isHost = deviceType === 'host';
            let nodeColor = '#3B82F6';
            if (isPlaceholder) {
                nodeColor = '#9CA3AF';
            } else if (isSwitch) {
                nodeColor = '#10B981';
            } else if (isHost) {
                nodeColor = '#8B5CF6';
            }

            const glowCircle = document.createElementNS(SVG_NS, 'circle');
            glowCircle.setAttribute('cx', node.x);
            glowCircle.setAttribute('cy', node.y);
            glowCircle.setAttribute('r', '26');
            glowCircle.setAttribute('fill', isPlaceholder ? 'rgba(156, 163, 175, 0.15)' : (isSwitch ? 'rgba(16, 185, 129, 0.15)' : (isHost ? 'rgba(139, 92, 246, 0.15)' : 'rgba(59, 130, 246, 0.15)')));
            nodeGroup.appendChild(glowCircle);

            if (highlighted.has(dev.hostname)) {
                const ring = document.createElementNS(SVG_NS, 'circle');
                ring.setAttribute('cx', node.x);
                ring.setAttribute('cy', node.y);
                ring.setAttribute('r', '31');
                ring.classList.add('node-mistake-ring');
                nodeGroup.appendChild(ring);
            }

            nodeGroup.appendChild(createDeviceIcon(node.x, node.y, nodeColor, {
                isPlaceholder, isSwitch, isHost, isL3Switch
            }));

            const label = document.createElementNS(SVG_NS, 'text');
            label.setAttribute('x', node.x);
            label.setAttribute('y', node.y + 36);
            label.setAttribute('text-anchor', 'middle');
            label.classList.add('node-hostname-label');
            label.textContent = isPlaceholder ? '???' : (dev.display_name || dev.hostname);
            nodeGroup.appendChild(label);

            nodeGroup.addEventListener('click', (e) => {
                e.stopPropagation();
                onNodeSelect(dev);
            });

            nodeGroup.addEventListener('mousedown', (e) => {
                e.stopPropagation();
                draggedNode = node;
                nodeGroup.style.cursor = 'grabbing';
            });

            g.appendChild(nodeGroup);
        });
    }

    function reset() {
        topology = null;
        nodes = [];
        links = [];
        highlighted = new Set();
        view = { x: 0, y: 0, k: 1 };
        svg.textContent = '';
    }

    function setLabels(next) {
        labels = { ...labels, ...next };
        draw();
    }

    // Interactive mouse zoom, pan and node drag.
    svg.addEventListener('wheel', (e) => {
        if (!topology) return;
        e.preventDefault();

        const rect = svg.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89;
        const newScale = Math.max(0.2, Math.min(view.k * zoomFactor, 3.5));

        view.x = mouseX - (mouseX - view.x) * (newScale / view.k);
        view.y = mouseY - (mouseY - view.y) * (newScale / view.k);
        view.k = newScale;

        applyTransform();
    }, { passive: false });

    svg.addEventListener('mousedown', (e) => {
        if (e.target === svg || e.target.id === 'graph-root' || e.target.tagName === 'svg') {
            isPanning = true;
            panStartX = e.clientX - view.x;
            panStartY = e.clientY - view.y;
            svg.style.cursor = 'grabbing';
        }
    });

    window.addEventListener('mousemove', (e) => {
        if (draggedNode) {
            const rect = svg.getBoundingClientRect();
            draggedNode.x = (e.clientX - rect.left - view.x) / view.k;
            draggedNode.y = (e.clientY - rect.top - view.y) / view.k;
            draw();
        } else if (isPanning) {
            view.x = e.clientX - panStartX;
            view.y = e.clientY - panStartY;
            applyTransform();
        }
    });

    window.addEventListener('mouseup', () => {
        if (draggedNode) {
            draggedNode = null;
        }
        if (isPanning) {
            isPanning = false;
            svg.style.cursor = 'grab';
        }
    });

    return {
        render,
        fit,
        redraw: draw,
        reset,
        setLabels,
        getLabels: () => ({ ...labels }),
        getTopology: () => topology,
        isInteracting: () => draggedNode !== null || isPanning,
    };
}
