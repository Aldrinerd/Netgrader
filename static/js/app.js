// static/js/app.js
document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const filePreviewList = document.getElementById('file-preview-list');
    const selectedFilesUl = document.getElementById('selected-files-ul');
    const fileCount = document.getElementById('file-count');
    const clearFilesBtn = document.getElementById('clear-files-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    const resetBtn = document.getElementById('reset-btn');
    const emptyState = document.getElementById('empty-state');
    const svg = document.getElementById('topology-svg');
    const diagnosticDrawer = document.getElementById('diagnostic-drawer');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const drawerTitle = document.getElementById('drawer-title');
    const drawerEntityType = document.getElementById('drawer-entity-type');
    const drawerBody = document.getElementById('drawer-body');
    const conflictCard = document.getElementById('conflict-summary-card');
    const conflictBadgeCount = document.getElementById('conflict-badge-count');
    const conflictItemsList = document.getElementById('conflict-items-list');
    const presetItems = document.querySelectorAll('.preset-item');

    let selectedFiles = [];
    let currentTopology = null;
    let simulationNodes = [];
    let simulationLinks = [];
    let isDraggingNode = false;
    let draggedNode = null;

    // --- Event Listeners: Presets ---
    presetItems.forEach(item => {
        item.addEventListener('click', async () => {
            const presetId = item.getAttribute('data-preset-id');
            presetItems.forEach(p => p.classList.remove('active'));
            item.classList.add('active');
            await loadPresetTopology(presetId);
        });
    });

    async function loadPresetTopology(presetId) {
        try {
            showLoading("Running multi-signal inference on preset...");
            const response = await fetch(`/api/presets/${presetId}`);
            if (!response.ok) throw new Error(`HTTP error ${response.status}`);
            const data = await response.json();
            renderTopology(data);
        } catch (err) {
            alert(`Failed to load preset: ${err.message}`);
        }
    }

    // --- Event Listeners: File Upload ---
    browseBtn.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function handleFiles(files) {
        selectedFiles = Array.from(files);
        if (selectedFiles.length === 0) return;

        filePreviewList.style.display = 'block';
        fileCount.textContent = `${selectedFiles.length} file(s) selected`;
        selectedFilesUl.innerHTML = '';

        selectedFiles.forEach(f => {
            const li = document.createElement('li');
            li.textContent = `${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
            selectedFilesUl.appendChild(li);
        });
    }

    clearFilesBtn.addEventListener('click', () => {
        selectedFiles = [];
        fileInput.value = '';
        filePreviewList.style.display = 'none';
    });

    analyzeBtn.addEventListener('click', async () => {
        if (selectedFiles.length === 0) return;
        const formData = new FormData();
        selectedFiles.forEach(f => formData.append('files', f));

        try {
            showLoading("Parsing Cisco outputs and discovering topology...");
            const res = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });
            if (!res.ok) throw new Error(`Upload failed with status ${res.status}`);
            const data = await res.json();
            renderTopology(data);
        } catch (err) {
            alert(`Analysis error: ${err.message}`);
        }
    });

    resetBtn.addEventListener('click', () => {
        currentTopology = null;
        selectedFiles = [];
        fileInput.value = '';
        filePreviewList.style.display = 'none';
        presetItems.forEach(p => p.classList.remove('active'));
        svg.innerHTML = '';
        emptyState.style.display = 'block';
        diagnosticDrawer.style.display = 'none';
        conflictCard.style.display = 'none';
    });

    closeDrawerBtn.addEventListener('click', () => {
        diagnosticDrawer.style.display = 'none';
    });

    function showLoading(msg) {
        emptyState.style.display = 'block';
        emptyState.innerHTML = `<div class="status-dot pulsing" style="width:24px;height:24px;margin:0 auto 12px;"></div><p>${msg}</p>`;
    }

    // --- Topology Graph Renderer ---
    function renderTopology(data) {
        currentTopology = data;
        emptyState.style.display = 'none';
        svg.innerHTML = '';

        const devices = Object.values(data.devices);
        const links = data.links || [];
        const conflicts = data.conflicts || [];

        // Render Conflict Card
        renderConflictSummary(conflicts);

        if (devices.length === 0) {
            emptyState.style.display = 'block';
            emptyState.innerHTML = `<div class="empty-icon">⚠️</div><h3>No Devices Found</h3><p>Could not extract device configurations from uploaded files.</p>`;
            return;
        }

        // Initialize node positions in a circle/mesh
        const rect = svg.getBoundingClientRect();
        const width = rect.width || 800;
        const height = rect.height || 600;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) * 0.32;

        const devEntries = Object.entries(data.devices || {});
        const hasCoordinates = devEntries.some(([_, d]) => d.x_coord !== null && d.y_coord !== null);

        if (hasCoordinates) {
            let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
            devEntries.forEach(([_, d]) => {
                if (d.x_coord !== null && d.y_coord !== null) {
                    minX = Math.min(minX, d.x_coord);
                    maxX = Math.max(maxX, d.x_coord);
                    minY = Math.min(minY, d.y_coord);
                    maxY = Math.max(maxY, d.y_coord);
                }
            });
            const spanX = (maxX - minX) || 1;
            const spanY = (maxY - minY) || 1;
            const padding = 70;

            simulationNodes = devEntries.map(([devKey, d], idx) => {
                let x = centerX + radius * Math.cos((idx / devEntries.length) * 2 * Math.PI - Math.PI / 2);
                let y = centerY + radius * Math.sin((idx / devEntries.length) * 2 * Math.PI - Math.PI / 2);
                if (d.x_coord !== null && d.y_coord !== null) {
                    x = padding + ((d.x_coord - minX) / spanX) * (width - 2 * padding);
                    y = padding + ((d.y_coord - minY) / spanY) * (height - 2 * padding);
                }
                return {
                    id: devKey,
                    device: d,
                    x: x,
                    y: y,
                    vx: 0,
                    vy: 0
                };
            });
        } else {
            simulationNodes = devEntries.map(([devKey, d], idx) => {
                const angle = (idx / devEntries.length) * 2 * Math.PI - Math.PI / 2;
                return {
                    id: devKey,
                    device: d,
                    x: centerX + radius * Math.cos(angle),
                    y: centerY + radius * Math.sin(angle),
                    vx: 0,
                    vy: 0
                };
            });
        }



        simulationLinks = links.map(l => {
            const source = simulationNodes.find(n => n.id === l.source_device);
            const target = simulationNodes.find(n => n.id === l.target_device);
            return {
                data: l,
                source: source || { x: centerX - 100, y: centerY, id: l.source_device },
                target: target || { x: centerX + 100, y: centerY, id: l.target_device }
            };
        });

        drawSvgGraph();
    }

    function drawSvgGraph() {
        svg.innerHTML = '';
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        svg.appendChild(defs);

        // SVG Container Group for Panning/Zooming
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('id', 'graph-root');
        svg.appendChild(g);

        // 1. Draw Links
        simulationLinks.forEach(linkObj => {
            const link = linkObj.data;
            const src = linkObj.source;
            const tgt = linkObj.target;

            const lineGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            lineGroup.classList.add('graph-link-group');
            lineGroup.style.cursor = 'pointer';

            const hasConflict = link.conflicts && link.conflicts.length > 0;
            let strokeColor = '#10B981'; // Green
            let strokeDash = 'none';

            if (hasConflict) {
                strokeColor = '#EF4444'; // Red
            } else if (link.classification === 'inferred') {
                strokeColor = '#F59E0B'; // Amber
                strokeDash = '6,4';
            } else if (link.classification === 'unverified') {
                strokeColor = '#6B7280';
                strokeDash = '3,3';
            }

            // Line
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', src.x);
            line.setAttribute('y1', src.y);
            line.setAttribute('x2', tgt.x);
            line.setAttribute('y2', tgt.y);
            line.setAttribute('stroke', strokeColor);
            line.setAttribute('stroke-width', hasConflict ? '3.5' : '2.5');
            line.setAttribute('stroke-dasharray', strokeDash);
            line.setAttribute('stroke-linecap', 'round');
            lineGroup.appendChild(line);

            // Midpoint Confidence Tag
            const midX = (src.x + tgt.x) / 2;
            const midY = (src.y + tgt.y) / 2;

            const badgeBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            const confText = hasConflict ? 'ERR' : `${Math.round(link.confidence * 100)}%`;
            badgeBg.setAttribute('x', midX - 20);
            badgeBg.setAttribute('y', midY - 10);
            badgeBg.setAttribute('width', '40');
            badgeBg.setAttribute('height', '20');
            badgeBg.setAttribute('rx', '10');
            badgeBg.setAttribute('fill', '#111827');
            badgeBg.setAttribute('stroke', strokeColor);
            badgeBg.setAttribute('stroke-width', '1');
            lineGroup.appendChild(badgeBg);

            const badgeLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            badgeLabel.setAttribute('x', midX);
            badgeLabel.setAttribute('y', midY + 4);
            badgeLabel.setAttribute('text-anchor', 'middle');
            badgeLabel.setAttribute('fill', strokeColor);
            badgeLabel.setAttribute('font-size', '10px');
            badgeLabel.setAttribute('font-weight', 'bold');
            badgeLabel.setAttribute('font-family', 'JetBrains Mono, monospace');
            badgeLabel.textContent = confText;
            lineGroup.appendChild(badgeLabel);

            lineGroup.addEventListener('click', (e) => {
                e.stopPropagation();
                openEdgeDiagnosticDrawer(link);
            });

            g.appendChild(lineGroup);
        });

        // 2. Draw Nodes
        simulationNodes.forEach(node => {
            const dev = node.device;
            const nodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            nodeGroup.classList.add('graph-node-group');
            nodeGroup.style.cursor = 'grab';

            const isPlaceholder = dev.is_placeholder || dev.display_name === '???';
            const isSwitch = dev.device_type === 'switch';
            let nodeColor = '#3B82F6';
            if (isPlaceholder) {
                nodeColor = '#9CA3AF';
            } else if (isSwitch) {
                nodeColor = '#10B981';
            }

            // Outer Glow Circle
            const glowCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            glowCircle.setAttribute('cx', node.x);
            glowCircle.setAttribute('cy', node.y);
            glowCircle.setAttribute('r', '28');
            glowCircle.setAttribute('fill', isPlaceholder ? 'rgba(156, 163, 175, 0.15)' : (isSwitch ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.15)'));
            nodeGroup.appendChild(glowCircle);

            // Main Circle
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', node.x);
            circle.setAttribute('cy', node.y);
            circle.setAttribute('r', '22');
            circle.setAttribute('fill', '#1F2937');
            circle.setAttribute('stroke', nodeColor);
            circle.setAttribute('stroke-width', '2');
            if (isPlaceholder) {
                circle.setAttribute('stroke-dasharray', '4,3');
            }
            nodeGroup.appendChild(circle);

            // Icon Text (R / SW / ?)
            const iconText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            iconText.setAttribute('x', node.x);
            iconText.setAttribute('y', node.y + 4);
            iconText.setAttribute('text-anchor', 'middle');
            iconText.setAttribute('fill', nodeColor);
            iconText.setAttribute('font-size', '11px');
            iconText.setAttribute('font-weight', 'bold');
            iconText.setAttribute('font-family', 'Outfit, sans-serif');
            iconText.textContent = isPlaceholder ? '?' : (isSwitch ? 'SW' : 'R');
            nodeGroup.appendChild(iconText);

            // Hostname Label Below
            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', node.x);
            label.setAttribute('y', node.y + 38);
            label.setAttribute('text-anchor', 'middle');
            label.setAttribute('fill', '#F9FAFB');
            label.setAttribute('font-size', '12px');
            label.setAttribute('font-weight', '600');
            label.setAttribute('font-family', 'JetBrains Mono, monospace');
            label.textContent = isPlaceholder ? '???' : (dev.display_name || dev.hostname);
            nodeGroup.appendChild(label);

            // Node Interactions
            nodeGroup.addEventListener('click', (e) => {
                e.stopPropagation();
                openNodeDiagnosticDrawer(dev);
            });

            // Drag Events
            nodeGroup.addEventListener('mousedown', (e) => {
                isDraggingNode = true;
                draggedNode = node;
                nodeGroup.style.cursor = 'grabbing';
            });

            g.appendChild(nodeGroup);
        });
    }

    // Global SVG Dragging Listeners
    svg.addEventListener('mousemove', (e) => {
        if (isDraggingNode && draggedNode) {
            const rect = svg.getBoundingClientRect();
            draggedNode.x = e.clientX - rect.left;
            draggedNode.y = e.clientY - rect.top;
            drawSvgGraph();
        }
    });

    window.addEventListener('mouseup', () => {
        if (isDraggingNode) {
            isDraggingNode = false;
            draggedNode = null;
        }
    });

    // --- Diagnostic Drawers ---
    function openEdgeDiagnosticDrawer(link) {
        diagnosticDrawer.style.display = 'flex';
        drawerEntityType.textContent = 'LINK INFERENCE AUDIT';
        drawerEntityType.className = 'drawer-badge badge-green';
        drawerTitle.textContent = `${link.source_device} (${link.source_interface}) ⟷ ${link.target_device} (${link.target_interface})`;

        let html = `
            <div class="diag-section">
                <div class="diag-section-title">Inference Confidence Score</div>
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                    <span style="font-size:24px;font-weight:700;color:${link.confidence >= 0.8 ? '#10B981' : '#F59E0B'};font-family:JetBrains Mono;">
                        ${(link.confidence * 100).toFixed(1)}%
                    </span>
                    <span class="badge ${link.classification === 'verified' ? 'badge-green' : 'badge-amber'}">
                        ${link.classification.toUpperCase()} LINK
                    </span>
                    <span style="font-size:11px;color:#9CA3AF;">Noisy-OR Fused Probability</span>
                </div>
            </div>

            <div class="diag-section">
                <div class="diag-section-title">Contributing Mathematical Signals (${link.signals.length})</div>
        `;

        link.signals.forEach(sig => {
            html += `
                <div class="signal-row">
                    <div>
                        <div class="signal-type">${sig.signal_type}</div>
                        <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">${sig.description}</div>
                        ${sig.evidence.map(e => `<span class="evidence-tag">📍 ${e}</span>`).join('')}
                    </div>
                    <div class="signal-weight">+${(sig.weight * 100).toFixed(0)}%</div>
                </div>
            `;
        });
        html += `</div>`;

        if (link.conflicts && link.conflicts.length > 0) {
            html += `
                <div class="diag-section">
                    <div class="diag-section-title" style="color:#EF4444;">Associated Conflicts / Errors</div>
                    ${link.conflicts.map(c => `
                        <div class="conflict-item-card" style="margin-bottom:6px;">
                            <div class="conflict-item-title">${c}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        drawerBody.innerHTML = html;
    }

    function openNodeDiagnosticDrawer(dev) {
        diagnosticDrawer.style.display = 'flex';
        const isPlaceholder = dev.is_placeholder || dev.display_name === '???';

        if (isPlaceholder) {
            drawerEntityType.textContent = 'UNKNOWN DEVICE / PEER';
            drawerEntityType.className = 'drawer-badge badge-amber';
            drawerTitle.textContent = `??? (Unknown Connection)`;

            let html = `
                <div class="diag-section">
                    <div class="diag-section-title">Connection Overview</div>
                    <div style="font-size:13px;color:#E5E7EB;margin-bottom:12px;line-height:1.5;">
                        This node represents an active physical or logical connection where the remote peer configuration was not uploaded or is an external/unmanaged device.
                    </div>
            `;
            if (dev.placeholder_for_device) {
                html += `
                    <div class="signal-row">
                        <div>
                            <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.5px;">Discovered Peer ID</div>
                            <div style="font-size:14px;font-weight:700;color:#F59E0B;font-family:JetBrains Mono;margin-top:2px;">${dev.placeholder_for_device}</div>
                            <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">Identified via discovery protocols (CDP/LLDP). Configuration file was not submitted.</div>
                        </div>
                    </div>
                `;
            }
            if (dev.placeholder_for_interface) {
                html += `
                    <div class="signal-row">
                        <div>
                            <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.5px;">Local Connected Port</div>
                            <div style="font-size:14px;font-weight:700;color:#60A5FA;font-family:JetBrains Mono;margin-top:2px;">${dev.placeholder_for_interface}</div>
                            <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">Port has active carrier status (up/up).</div>
                        </div>
                    </div>
                `;
            }
            html += `</div>`;
            drawerBody.innerHTML = html;
            return;
        }

        drawerEntityType.textContent = 'DEVICE PROFILE';
        drawerEntityType.className = 'drawer-badge badge-blue';
        drawerTitle.textContent = `${dev.hostname} (${dev.device_type.toUpperCase()})`;

        let html = `
            <div class="diag-section">
                <div class="diag-section-title">Interfaces & IP Allocation</div>
        `;

        Object.values(dev.interfaces).forEach(intf => {
            const isDown = intf.admin_status === 'administratively down' || intf.line_status === 'down';
            html += `
                <div class="signal-row" style="flex-direction:column;align-items:flex-start;">
                    <div style="display:flex;justify-content:space-between;width:100%;">
                        <strong style="font-family:JetBrains Mono;">${intf.name}</strong>
                        <span class="badge ${isDown ? 'badge-red' : 'badge-green'}">${intf.admin_status}/${intf.line_status}</span>
                    </div>
                    <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">
                        ${intf.ip_address ? `IP: <strong>${intf.ip_address}/${intf.cidr}</strong> (${intf.network_address})` : 'IP: (Unassigned)'}
                        ${intf.switchport_mode ? ` | Switchport: <strong>${intf.switchport_mode}</strong> (VLAN ${intf.access_vlan || intf.trunk_native_vlan})` : ''}
                    </div>
                    ${intf.description ? `<div style="font-size:11px;color:#60A5FA;">desc: ${intf.description}</div>` : ''}
                </div>
            `;
        });
        html += `</div>`;

        if (dev.cdp_neighbors && dev.cdp_neighbors.length > 0) {
            html += `
                <div class="diag-section">
                    <div class="diag-section-title">CDP Neighbors Detail (${dev.cdp_neighbors.length})</div>
            `;
            dev.cdp_neighbors.forEach(cdp => {
                html += `
                    <div class="signal-row">
                        <div>
                            <strong>${cdp.device_id}</strong> on <code>${cdp.local_interface}</code> ⟷ <code>${cdp.remote_interface}</code>
                            <div style="font-size:10px;color:#9CA3AF;">Platform: ${cdp.platform || 'Cisco'} | Remote IP: ${cdp.remote_ip || 'N/A'}</div>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        }

        drawerBody.innerHTML = html;
    }

    function renderConflictSummary(conflicts) {
        if (!conflicts || conflicts.length === 0) {
            conflictCard.style.display = 'none';
            return;
        }

        conflictCard.style.display = 'block';
        conflictBadgeCount.textContent = `${conflicts.length} Issues`;
        conflictItemsList.innerHTML = '';

        conflicts.forEach(c => {
            const card = document.createElement('div');
            card.className = `conflict-item-card ${c.severity === 'warning' ? 'warning' : ''}`;
            card.innerHTML = `
                <div class="conflict-item-title">[!] ${c.title}</div>
                <div class="conflict-item-desc">${c.description}</div>
                ${c.evidence_citations.map(cit => `<span class="evidence-tag">📍 Citation: ${cit}</span>`).join('')}
            `;
            conflictItemsList.appendChild(card);
        });
    }
});
