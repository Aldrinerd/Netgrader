// static/js/app.js
document.addEventListener('DOMContentLoaded', () => {
    // --- Mode Navigation Elements ---
    const modeTabs = document.querySelectorAll('.mode-tab-btn');
    const modePanels = {
        visualizer: document.getElementById('panel-mode-visualizer'),
        teacher: document.getElementById('panel-mode-teacher'),
        student: document.getElementById('panel-mode-student')
    };
    let currentMode = 'visualizer';

    // --- Common DOM Elements ---
    const resetBtn = document.getElementById('reset-btn');
    const svg = document.getElementById('topology-svg');
    const emptyState = document.getElementById('empty-state');
    const emptyStateTitle = document.getElementById('empty-state-title');
    const emptyStateDesc = document.getElementById('empty-state-desc');
    const canvasMainTitle = document.getElementById('canvas-main-title');
    const engineStatusLabel = document.getElementById('engine-status-label');
    const diagnosticDrawer = document.getElementById('diagnostic-drawer');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const drawerTitle = document.getElementById('drawer-title');
    const drawerEntityType = document.getElementById('drawer-entity-type');
    const drawerBody = document.getElementById('drawer-body');
    const toastContainer = document.getElementById('toast-container');

    const togglePortsBtn = document.getElementById('toggle-ports-btn');
    const toggleIpsBtn = document.getElementById('toggle-ips-btn');
    const zoomFitBtn = document.getElementById('zoom-fit-btn');

    // --- Mode 1: Visualizer Elements ---
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const filePreviewList = document.getElementById('file-preview-list');
    const selectedFilesUl = document.getElementById('selected-files-ul');
    const fileCount = document.getElementById('file-count');
    const clearFilesBtn = document.getElementById('clear-files-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    const conflictCard = document.getElementById('conflict-summary-card');
    const conflictBadgeCount = document.getElementById('conflict-badge-count');
    const conflictItemsList = document.getElementById('conflict-items-list');

    // --- Mode 2: Teacher Studio Elements ---
    const teacherDropZone = document.getElementById('teacher-drop-zone');
    const teacherFileInput = document.getElementById('teacher-file-input');
    const teacherBrowseBtn = document.getElementById('teacher-browse-btn');
    const teacherFilePreview = document.getElementById('teacher-file-preview');
    const teacherFilesUl = document.getElementById('teacher-files-ul');
    const teacherFileName = document.getElementById('teacher-file-name');
    const teacherClearBtn = document.getElementById('teacher-clear-btn');
    const teacherLabTitle = document.getElementById('teacher-lab-title');
    const teacherLabDesc = document.getElementById('teacher-lab-desc');
    const teacherTotalPoints = document.getElementById('teacher-total-points');
    const teacherGenerateBtn = document.getElementById('teacher-generate-btn');
    const teacherResultCard = document.getElementById('teacher-result-card');
    const teacherInstructionsPreview = document.getElementById('teacher-instructions-preview');
    const teacherRulesCountBadge = document.getElementById('teacher-rules-count-badge');
    const teacherDownloadBtn = document.getElementById('teacher-download-btn');
    const teacherCopyBtn = document.getElementById('teacher-copy-btn');

    // --- Mode 3: Student Portal Elements ---
    const studentInstDropZone = document.getElementById('student-inst-drop-zone');
    const studentInstInput = document.getElementById('student-inst-input');
    const studentInstBrowseBtn = document.getElementById('student-inst-browse-btn');
    const studentInstStatus = document.getElementById('student-inst-status');
    const studentInstInfo = document.getElementById('student-inst-info');
    const criteriaLabTitle = document.getElementById('criteria-lab-title');
    const criteriaPointsTag = document.getElementById('criteria-points-tag');
    const criteriaRulesTag = document.getElementById('criteria-rules-tag');

    const studentSubDropZone = document.getElementById('student-sub-drop-zone');
    const studentSubInput = document.getElementById('student-sub-input');
    const studentSubBrowseBtn = document.getElementById('student-sub-browse-btn');
    const studentSubPreview = document.getElementById('student-sub-preview');
    const studentSubFilesUl = document.getElementById('student-sub-files-ul');
    const studentSubCount = document.getElementById('student-sub-count');
    const studentSubClearBtn = document.getElementById('student-sub-clear-btn');
    const studentEvaluateBtn = document.getElementById('student-evaluate-btn');

    const studentReportCard = document.getElementById('student-report-card');
    const reportGradeLetter = document.getElementById('report-grade-letter');
    const reportEarnedScore = document.getElementById('report-earned-score');
    const reportMaxScore = document.getElementById('report-max-score');
    const reportProgressFill = document.getElementById('report-progress-fill');
    const reportPassedTag = document.getElementById('report-passed-tag');
    const reportFailedTag = document.getElementById('report-failed-tag');
    const filterCountAll = document.getElementById('filter-count-all');
    const filterCountFailed = document.getElementById('filter-count-failed');
    const filterCountPassed = document.getElementById('filter-count-passed');
    const reportResultsList = document.getElementById('report-results-list');
    const filterChips = document.querySelectorAll('.filter-chip');
    const studentDownloadReportBtn = document.getElementById('student-download-report-btn');

    // State Variables
    let selectedFiles = [];
    let teacherSelectedFiles = [];
    let generatedInstructionsText = "";
    let studentInstructionsFile = null;
    let studentSubmissionFiles = [];
    let latestEvaluationReport = null;

    let currentTopology = null;
    let simulationNodes = [];
    let simulationLinks = [];

    // Canvas Interaction State
    let isDraggingNode = false;
    let draggedNode = null;
    let isPanning = false;
    let panStartX = 0;
    let panStartY = 0;
    let viewTransform = { x: 0, y: 0, k: 1 };

    let showPortLabels = true;
    let showIpLabels = false;

    // Helper: Toast Notifications
    function showToast(msg, duration = 3000) {
        if (!toastContainer) return;
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `<span>✨</span><span>${msg}</span>`;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            toast.style.transition = 'all 0.25s ease';
            setTimeout(() => toast.remove(), 250);
        }, duration);
    }

    // Helper: Short interface names
    function shortInterfaceName(name) {
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

    // --- Mode Switching ---
    function switchMode(mode) {
        currentMode = mode;
        modeTabs.forEach(t => t.classList.toggle('active', t.getAttribute('data-mode') === mode));
        
        Object.entries(modePanels).forEach(([mKey, panel]) => {
            if (panel) panel.classList.toggle('active', mKey === mode);
        });

        if (mode === 'visualizer') {
            if (canvasMainTitle) canvasMainTitle.textContent = 'Topology Discovery';
            if (engineStatusLabel) engineStatusLabel.textContent = 'Inference Engine: Active';
        } else if (mode === 'teacher') {
            if (canvasMainTitle) canvasMainTitle.textContent = 'Reference Topology Studio';
            if (engineStatusLabel) engineStatusLabel.textContent = 'Teacher Studio: Ready';
        } else if (mode === 'student') {
            if (canvasMainTitle) canvasMainTitle.textContent = 'Student Evaluation View';
            if (engineStatusLabel) engineStatusLabel.textContent = 'Evaluation Engine: Ready';
        }
        if (pendingOperations === 0) applyEmptyStateText(mode);
    }

    modeTabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            const mode = tab.getAttribute('data-mode');
            switchMode(mode);
        });
    });

    // --- Common Toggle Event Listeners ---
    if (togglePortsBtn) {
        togglePortsBtn.addEventListener('click', () => {
            showPortLabels = !showPortLabels;
            togglePortsBtn.classList.toggle('active', showPortLabels);
            drawSvgGraph();
        });
    }

    if (toggleIpsBtn) {
        toggleIpsBtn.addEventListener('click', () => {
            showIpLabels = !showIpLabels;
            toggleIpsBtn.classList.toggle('active', showIpLabels);
            drawSvgGraph();
        });
    }

    if (zoomFitBtn) {
        zoomFitBtn.addEventListener('click', () => {
            fitGraphToViewport();
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            currentTopology = null;
            selectedFiles = [];
            teacherSelectedFiles = [];
            studentSubmissionFiles = [];
            studentInstructionsFile = null;
            latestEvaluationReport = null;

            if (fileInput) fileInput.value = '';
            if (teacherFileInput) teacherFileInput.value = '';
            if (studentInstInput) studentInstInput.value = '';
            if (studentSubInput) studentSubInput.value = '';

            if (filePreviewList) filePreviewList.style.display = 'none';
            if (teacherFilePreview) teacherFilePreview.style.display = 'none';
            if (teacherResultCard) teacherResultCard.style.display = 'none';
            if (studentInstInfo) studentInstInfo.style.display = 'none';
            if (studentSubPreview) studentSubPreview.style.display = 'none';
            if (studentReportCard) studentReportCard.style.display = 'none';
            if (studentInstStatus) {
                studentInstStatus.textContent = 'Required';
                studentInstStatus.className = 'badge badge-amber';
            }

            svg.innerHTML = '';
            if (emptyState) emptyState.style.display = 'block';
            if (diagnosticDrawer) diagnosticDrawer.style.display = 'none';
            if (conflictCard) conflictCard.style.display = 'none';
            viewTransform = { x: 0, y: 0, k: 1 };
            showToast("View reset successfully.");
        });
    }

    if (closeDrawerBtn) {
        closeDrawerBtn.addEventListener('click', () => {
            if (diagnosticDrawer) diagnosticDrawer.style.display = 'none';
        });
    }

    // --- Resizable Sidebar Splitter Logic ---
    const sidebarResizer = document.getElementById('sidebar-resizer');
    const controlPanel = document.getElementById('control-panel');
    const workspaceGrid = document.getElementById('workspace-grid');

    if (sidebarResizer && controlPanel && workspaceGrid) {
        // Restore saved width from localStorage
        const savedWidth = localStorage.getItem('network_eval_sidebar_width');
        if (savedWidth) {
            const widthVal = parseInt(savedWidth, 10);
            if (!isNaN(widthVal) && widthVal >= 320 && widthVal <= 800) {
                document.documentElement.style.setProperty('--sidebar-width', `${widthVal}px`);
            }
        }

        let isResizingSidebar = false;

        const onResizeStart = (e) => {
            isResizingSidebar = true;
            sidebarResizer.classList.add('is-dragging');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        };

        const onResizeMove = (e) => {
            if (!isResizingSidebar) return;
            const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
            const gridRect = workspaceGrid.getBoundingClientRect();
            let newWidth = clientX - gridRect.left;

            // Constrain width bounds (min 320px, max 800px / window max)
            const maxWidth = Math.min(800, window.innerWidth - 300);
            newWidth = Math.max(320, Math.min(newWidth, maxWidth));

            document.documentElement.style.setProperty('--sidebar-width', `${newWidth}px`);
            localStorage.setItem('network_eval_sidebar_width', `${newWidth}`);

            if (currentTopology && typeof fitGraphToViewport === 'function') {
                clearTimeout(window._resizerTimer);
                window._resizerTimer = setTimeout(() => fitGraphToViewport(), 50);
            }
        };

        const onResizeEnd = () => {
            if (isResizingSidebar) {
                isResizingSidebar = false;
                sidebarResizer.classList.remove('is-dragging');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                if (currentTopology && typeof fitGraphToViewport === 'function') {
                    fitGraphToViewport();
                }
            }
        };

        sidebarResizer.addEventListener('mousedown', onResizeStart);
        window.addEventListener('mousemove', onResizeMove);
        window.addEventListener('mouseup', onResizeEnd);

        sidebarResizer.addEventListener('touchstart', onResizeStart, { passive: false });
        window.addEventListener('touchmove', onResizeMove, { passive: false });
        window.addEventListener('touchend', onResizeEnd);

        // Double click to reset to default 440px
        sidebarResizer.addEventListener('dblclick', () => {
            document.documentElement.style.setProperty('--sidebar-width', '440px');
            localStorage.setItem('network_eval_sidebar_width', '440px');
            if (currentTopology && typeof fitGraphToViewport === 'function') {
                fitGraphToViewport();
            }
            showToast("Sidebar width reset to default.");
        });
    }

    // --- Policy Quick Preset Profiles ---
    const policyElements = {
        dynamicSubnetting: document.getElementById('policy-allow-dynamic-subnetting'),
        enforcePrefix: document.getElementById('policy-enforce-prefix-length'),
        verifyGateways: document.getElementById('policy-verify-default-gateways'),
        customHostnames: document.getElementById('policy-allow-custom-hostnames'),
        strictPorts: document.getElementById('policy-strict-port-matching'),
        strictCable: document.getElementById('policy-strict-cable-type'),
        flexibleOspf: document.getElementById('policy-allow-flexible-process-ids'),
        gradeSecurity: document.getElementById('policy-grade-security-baseline'),
        gradeDescriptions: document.getElementById('policy-grade-interface-descriptions')
    };

    const btnProfileDefault = document.getElementById('btn-profile-default');
    const btnProfileDynamic = document.getElementById('btn-profile-dynamic');
    const btnProfileStrict = document.getElementById('btn-profile-strict');
    const profileBtns = [btnProfileDefault, btnProfileDynamic, btnProfileStrict].filter(Boolean);

    function setProfileActive(activeBtn) {
        profileBtns.forEach(btn => btn.classList.toggle('active', btn === activeBtn));
    }

    function applyPolicyValues(values, activeBtn) {
        if (policyElements.dynamicSubnetting) policyElements.dynamicSubnetting.checked = !!values.dynamicSubnetting;
        if (policyElements.enforcePrefix) policyElements.enforcePrefix.checked = !!values.enforcePrefix;
        if (policyElements.verifyGateways) policyElements.verifyGateways.checked = !!values.verifyGateways;
        if (policyElements.customHostnames) policyElements.customHostnames.checked = !!values.customHostnames;
        if (policyElements.strictPorts) policyElements.strictPorts.checked = !!values.strictPorts;
        if (policyElements.strictCable) policyElements.strictCable.checked = !!values.strictCable;
        if (policyElements.flexibleOspf) policyElements.flexibleOspf.checked = !!values.flexibleOspf;
        if (policyElements.gradeSecurity) policyElements.gradeSecurity.checked = !!values.gradeSecurity;
        if (policyElements.gradeDescriptions) policyElements.gradeDescriptions.checked = !!values.gradeDescriptions;
        if (activeBtn) setProfileActive(activeBtn);
    }

    if (btnProfileDefault) {
        btnProfileDefault.addEventListener('click', () => {
            applyPolicyValues({
                dynamicSubnetting: false,
                enforcePrefix: true,
                verifyGateways: true,
                customHostnames: false,
                strictPorts: true,
                strictCable: true,
                flexibleOspf: true,
                gradeSecurity: false,
                gradeDescriptions: false
            }, btnProfileDefault);
            showToast("Loaded Standard CCNA Policy Profile");
        });
    }

    if (btnProfileDynamic) {
        btnProfileDynamic.addEventListener('click', () => {
            applyPolicyValues({
                dynamicSubnetting: true,
                enforcePrefix: true,
                verifyGateways: true,
                customHostnames: true,
                strictPorts: true,
                strictCable: true,
                flexibleOspf: true,
                gradeSecurity: false,
                gradeDescriptions: false
            }, btnProfileDynamic);
            showToast("Loaded Dynamic Subnetting Policy Profile");
        });
    }

    if (btnProfileStrict) {
        btnProfileStrict.addEventListener('click', () => {
            applyPolicyValues({
                dynamicSubnetting: false,
                enforcePrefix: true,
                verifyGateways: true,
                customHostnames: false,
                strictPorts: true,
                strictCable: true,
                flexibleOspf: false,
                gradeSecurity: true,
                gradeDescriptions: true
            }, btnProfileStrict);
            showToast("Loaded Full Security & Strict Policy Profile");
        });
    }

    // Uncheck profile highlight on manual toggle
    Object.values(policyElements).forEach(el => {
        if (el) {
            el.addEventListener('change', () => {
                profileBtns.forEach(btn => btn.classList.remove('active'));
            });
        }
    });

    // Window Resize Handling
    window.addEventListener('resize', () => {
        if (currentTopology && !isDraggingNode && !isPanning) {
            clearTimeout(window._resizeTimer);
            window._resizeTimer = setTimeout(() => {
                fitGraphToViewport();
            }, 80);
        }
    });

    // --- MODE 1: VISUALIZER LOGIC ---


    if (browseBtn && fileInput) browseBtn.addEventListener('click', () => fileInput.click());
    if (dropZone && fileInput) {
        dropZone.addEventListener('click', () => fileInput.click());
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        });
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); });
        });
        dropZone.addEventListener('drop', (e) => {
            handleFiles(e.dataTransfer.files);
        });
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });
    }

    function handleFiles(files) {
        selectedFiles = Array.from(files);
        if (selectedFiles.length === 0) return;

        if (filePreviewList) filePreviewList.style.display = 'block';
        if (fileCount) fileCount.textContent = `${selectedFiles.length} file(s) selected`;
        if (selectedFilesUl) {
            selectedFilesUl.innerHTML = '';
            selectedFiles.forEach(f => {
                const li = document.createElement('li');
                li.textContent = `${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
                selectedFilesUl.appendChild(li);
            });
        }
    }

    if (clearFilesBtn) {
        clearFilesBtn.addEventListener('click', () => {
            selectedFiles = [];
            if (fileInput) fileInput.value = '';
            if (filePreviewList) filePreviewList.style.display = 'none';
        });
    }

    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', async () => {
            if (selectedFiles.length === 0) return;
            const formData = new FormData();
            selectedFiles.forEach(f => formData.append('files', f));

            try {
                showLoading("Parsing Cisco outputs and discovering topology...");
                const res = await fetch('/api/analyze', { method: 'POST', body: formData });
                if (!res.ok) throw new Error(await describeFailure(res, `Upload failed with status ${res.status}`));
                const data = await res.json();
                renderTopology(data);
                showToast("Topology discovery completed.");
            } catch (err) {
                showPanelMessage(`<div class="empty-icon">⚠️</div><h3>Analysis Failed</h3>`
                    + `<p class="empty-error">${escapeHtml(err.message)}</p>`);
                alert(`Analysis error: ${err.message}`);
            } finally {
                hideLoading();
            }
        });
    }

    // --- MODE 2: INSTRUCTOR STUDIO LOGIC ---
    if (teacherBrowseBtn && teacherFileInput) teacherBrowseBtn.addEventListener('click', () => teacherFileInput.click());
    if (teacherDropZone && teacherFileInput) {
        teacherDropZone.addEventListener('click', () => teacherFileInput.click());
        ['dragenter', 'dragover'].forEach(eventName => {
            teacherDropZone.addEventListener(eventName, (e) => { e.preventDefault(); teacherDropZone.classList.add('dragover'); });
        });
        ['dragleave', 'drop'].forEach(eventName => {
            teacherDropZone.addEventListener(eventName, (e) => { e.preventDefault(); teacherDropZone.classList.remove('dragover'); });
        });
        teacherDropZone.addEventListener('drop', (e) => {
            handleTeacherFiles(e.dataTransfer.files);
        });
        teacherFileInput.addEventListener('change', (e) => {
            handleTeacherFiles(e.target.files);
        });
    }

    function handleTeacherFiles(files) {
        teacherSelectedFiles = Array.from(files);
        if (teacherSelectedFiles.length === 0) return;

        if (teacherFilePreview) teacherFilePreview.style.display = 'block';
        if (teacherFileName) teacherFileName.textContent = `${teacherSelectedFiles.length} file(s) selected`;
        if (teacherFilesUl) {
            teacherFilesUl.innerHTML = '';
            teacherSelectedFiles.forEach(f => {
                const li = document.createElement('li');
                li.textContent = `${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
                teacherFilesUl.appendChild(li);
            });
        }
    }

    if (teacherClearBtn) {
        teacherClearBtn.addEventListener('click', () => {
            teacherSelectedFiles = [];
            if (teacherFileInput) teacherFileInput.value = '';
            if (teacherFilePreview) teacherFilePreview.style.display = 'none';
        });
    }

    if (teacherGenerateBtn) {
        teacherGenerateBtn.addEventListener('click', async () => {
            if (teacherSelectedFiles.length === 0) {
                alert("Please upload a reference Packet Tracer (.pkt/.xml) or config bundle.");
                return;
            }

            const formData = new FormData();
            teacherSelectedFiles.forEach(f => formData.append('files', f));
            formData.append('lab_title', teacherLabTitle ? teacherLabTitle.value.trim() || 'Packet Tracer Lab Assignment' : 'Packet Tracer Lab Assignment');
            formData.append('lab_description', teacherLabDesc ? teacherLabDesc.value.trim() : '');
            formData.append('total_points', teacherTotalPoints ? parseFloat(teacherTotalPoints.value) || 100.0 : 100.0);

            // Policy parameters
            formData.append('allow_dynamic_subnetting', document.getElementById('policy-allow-dynamic-subnetting')?.checked ? 'true' : 'false');
            formData.append('enforce_prefix_length', document.getElementById('policy-enforce-prefix-length')?.checked ? 'true' : 'false');
            formData.append('verify_default_gateways', document.getElementById('policy-verify-default-gateways')?.checked ? 'true' : 'false');
            formData.append('allow_custom_hostnames', document.getElementById('policy-allow-custom-hostnames')?.checked ? 'true' : 'false');
            formData.append('strict_port_matching', document.getElementById('policy-strict-port-matching')?.checked ? 'true' : 'false');
            formData.append('strict_cable_type', document.getElementById('policy-strict-cable-type')?.checked ? 'true' : 'false');
            formData.append('allow_flexible_process_ids', document.getElementById('policy-allow-flexible-process-ids')?.checked ? 'true' : 'false');
            formData.append('grade_security_baseline', document.getElementById('policy-grade-security-baseline')?.checked ? 'true' : 'false');
            formData.append('grade_interface_descriptions', document.getElementById('policy-grade-interface-descriptions')?.checked ? 'true' : 'false');

            try {
                showLoading("Extracting reference topology & generating rubric...");
                const res = await fetch('/api/criteria/generate', { method: 'POST', body: formData });
                if (!res.ok) {
                    throw new Error(await describeFailure(res, `Server error ${res.status}`));
                }
                const data = await res.json();

                generatedInstructionsText = data.instructions_txt;
                if (teacherInstructionsPreview) teacherInstructionsPreview.textContent = generatedInstructionsText;
                if (teacherRulesCountBadge) teacherRulesCountBadge.textContent = `${data.criteria.rules.length} Rules (${data.criteria.total_points} pts)`;
                if (teacherResultCard) teacherResultCard.style.display = 'block';

                if (data.topology) {
                    renderTopology(data.topology);
                }
                showToast("Lab instructions & rubric generated!");
            } catch (err) {
                showPanelMessage(`<div class="empty-icon">⚠️</div><h3>Could Not Generate Rubric</h3>`
                    + `<p class="empty-error">${escapeHtml(err.message)}</p>`);
                alert(`Generation Error: ${err.message}`);
            } finally {
                hideLoading();
            }
        });
    }

    if (teacherDownloadBtn) {
        teacherDownloadBtn.addEventListener('click', () => {
            if (!generatedInstructionsText) return;
            const blob = new Blob([generatedInstructionsText], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const titleStr = teacherLabTitle ? teacherLabTitle.value.trim().replace(/[^a-zA-Z0-9_-]/g, '_') : 'lab';
            const filename = (titleStr || 'lab') + '_instructions.txt';
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
            showToast(`Downloaded ${filename}`);
        });
    }

    if (teacherCopyBtn) {
        teacherCopyBtn.addEventListener('click', async () => {
            if (!generatedInstructionsText) return;
            try {
                await navigator.clipboard.writeText(generatedInstructionsText);
                showToast("Copied instructions.txt to clipboard!");
            } catch (e) {
                alert("Failed to copy to clipboard.");
            }
        });
    }

    // --- MODE 3: STUDENT SUBMISSION & GRADING LOGIC ---
    if (studentInstBrowseBtn && studentInstInput) studentInstBrowseBtn.addEventListener('click', () => studentInstInput.click());
    if (studentInstDropZone && studentInstInput) {
        studentInstDropZone.addEventListener('click', () => studentInstInput.click());
        ['dragenter', 'dragover'].forEach(eventName => {
            studentInstDropZone.addEventListener(eventName, (e) => { e.preventDefault(); studentInstDropZone.classList.add('dragover'); });
        });
        ['dragleave', 'drop'].forEach(eventName => {
            studentInstDropZone.addEventListener(eventName, (e) => { e.preventDefault(); studentInstDropZone.classList.remove('dragover'); });
        });
        studentInstDropZone.addEventListener('drop', (e) => {
            if (e.dataTransfer.files.length > 0) handleStudentInstFile(e.dataTransfer.files[0]);
        });
        studentInstInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) handleStudentInstFile(e.target.files[0]);
        });
    }

    async function handleStudentInstFile(file) {
        studentInstructionsFile = file;
        const formData = new FormData();
        formData.append('instructions_file', file);

        try {
            const res = await fetch('/api/criteria/parse', { method: 'POST', body: formData });
            if (!res.ok) {
                const errJson = await res.json();
                throw new Error(errJson.detail || "Invalid instructions file");
            }
            const data = await res.json();
            const crit = data.criteria;

            if (studentInstInfo) studentInstInfo.style.display = 'block';
            if (criteriaLabTitle) criteriaLabTitle.textContent = crit.lab_title;
            if (criteriaPointsTag) criteriaPointsTag.textContent = `${crit.total_points} Total pts`;
            if (criteriaRulesTag) criteriaRulesTag.textContent = `${crit.rules.length} Checkpoints`;

            if (studentInstStatus) {
                studentInstStatus.textContent = '✅ Verified';
                studentInstStatus.className = 'badge badge-green';
            }
            showToast("Instructions rubric verified.");
        } catch (err) {
            if (studentInstStatus) {
                studentInstStatus.textContent = '❌ Error';
                studentInstStatus.className = 'badge badge-red';
            }
            alert(`Error reading instructions file: ${err.message}`);
        }
    }

    if (studentSubBrowseBtn && studentSubInput) studentSubBrowseBtn.addEventListener('click', () => studentSubInput.click());
    if (studentSubDropZone && studentSubInput) {
        studentSubDropZone.addEventListener('click', () => studentSubInput.click());
        ['dragenter', 'dragover'].forEach(eventName => {
            studentSubDropZone.addEventListener(eventName, (e) => { e.preventDefault(); studentSubDropZone.classList.add('dragover'); });
        });
        ['dragleave', 'drop'].forEach(eventName => {
            studentSubDropZone.addEventListener(eventName, (e) => { e.preventDefault(); studentSubDropZone.classList.remove('dragover'); });
        });
        studentSubDropZone.addEventListener('drop', (e) => {
            handleStudentSubFiles(e.dataTransfer.files);
        });
        studentSubInput.addEventListener('change', (e) => {
            handleStudentSubFiles(e.target.files);
        });
    }

    function handleStudentSubFiles(files) {
        studentSubmissionFiles = Array.from(files);
        if (studentSubmissionFiles.length === 0) return;

        if (studentSubPreview) studentSubPreview.style.display = 'block';
        if (studentSubCount) studentSubCount.textContent = `${studentSubmissionFiles.length} file(s) selected`;
        if (studentSubFilesUl) {
            studentSubFilesUl.innerHTML = '';
            studentSubmissionFiles.forEach(f => {
                const li = document.createElement('li');
                li.textContent = `${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
                studentSubFilesUl.appendChild(li);
            });
        }
    }

    if (studentSubClearBtn) {
        studentSubClearBtn.addEventListener('click', () => {
            studentSubmissionFiles = [];
            if (studentSubInput) studentSubInput.value = '';
            if (studentSubPreview) studentSubPreview.style.display = 'none';
        });
    }

    if (studentEvaluateBtn) {
        studentEvaluateBtn.addEventListener('click', async () => {
            if (!studentInstructionsFile) {
                alert("Step 1: Please upload the instructor's instructions.txt first.");
                return;
            }
            if (studentSubmissionFiles.length === 0) {
                alert("Step 2: Please upload your student submission (.pkt, .xml, or config files).");
                return;
            }

            const formData = new FormData();
            formData.append('instructions_file', studentInstructionsFile);
            studentSubmissionFiles.forEach(f => formData.append('student_files', f));

            try {
                showLoading("Grading submission and evaluating relational topology rules...");
                const res = await fetch('/api/evaluate', { method: 'POST', body: formData });
                if (!res.ok) {
                    throw new Error(await describeFailure(res, `Evaluation failed with status ${res.status}`));
                }
                const report = await res.json();
                latestEvaluationReport = report;
                renderEvaluationReport(report);
                showToast(`Grading Complete: Score ${report.percentage}% (${report.grade_letter})`);
            } catch (err) {
                showPanelMessage(`<div class="empty-icon">⚠️</div><h3>Grading Failed</h3>`
                    + `<p class="empty-error">${escapeHtml(err.message)}</p>`);
                alert(`Evaluation Error: ${err.message}`);
            } finally {
                hideLoading();
            }
        });
    }

    function renderEvaluationReport(report) {
        if (studentReportCard) studentReportCard.style.display = 'block';

        if (reportGradeLetter) {
            reportGradeLetter.textContent = report.grade_letter;
            reportGradeLetter.className = `score-grade-badge grade-${report.grade_letter.toLowerCase().charAt(0)}`;
        }
        if (reportEarnedScore) reportEarnedScore.textContent = report.total_score.toFixed(1);
        if (reportMaxScore) reportMaxScore.textContent = report.max_score.toFixed(1);
        if (reportProgressFill) {
            reportProgressFill.style.width = `${Math.min(100, Math.max(0, report.percentage))}%`;
            if (report.percentage < 60) reportProgressFill.className = 'score-progress-fill fill-red';
            else if (report.percentage < 80) reportProgressFill.className = 'score-progress-fill fill-amber';
            else reportProgressFill.className = 'score-progress-fill';
        }

        if (reportPassedTag) reportPassedTag.textContent = `✅ ${report.passed_count} Passed`;
        if (reportFailedTag) reportFailedTag.textContent = `❌ ${report.failed_count} Failed`;

        if (filterCountAll) filterCountAll.textContent = report.results.length;
        if (filterCountFailed) filterCountFailed.textContent = report.failed_count;
        if (filterCountPassed) filterCountPassed.textContent = report.passed_count;

        renderFilteredResults('all');

        if (report.topology) {
            renderTopology(report.topology);
        }
    }

    function renderFilteredResults(filter = 'all') {
        if (!latestEvaluationReport || !reportResultsList) return;
        reportResultsList.innerHTML = '';

        const results = latestEvaluationReport.results.filter(r => {
            if (filter === 'passed') return r.passed;
            if (filter === 'failed') return !r.passed;
            return true;
        });

        if (results.length === 0) {
            reportResultsList.innerHTML = `<div style="text-align:center;color:#9CA3AF;font-size:11.5px;padding:12px;">No items match filter.</div>`;
            return;
        }

        results.forEach(res => {
            const card = document.createElement('div');
            card.className = `rule-result-card ${res.passed ? 'passed' : 'failed'}`;
            card.innerHTML = `
                <div class="rule-res-top">
                    <span class="rule-res-desc">${res.passed ? '✅' : '❌'} ${res.description}</span>
                    <span class="rule-res-pts">${res.points_earned.toFixed(1)} / ${res.points_possible.toFixed(1)} pts</span>
                </div>
                <div class="rule-res-feedback">${res.feedback}</div>
                ${res.actual_value ? `<div class="rule-res-actual">Found: ${res.actual_value}</div>` : ''}
            `;
            reportResultsList.appendChild(card);
        });
    }

    filterChips.forEach(chip => {
        chip.addEventListener('click', () => {
            filterChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            const filter = chip.getAttribute('data-filter');
            renderFilteredResults(filter);
        });
    });

    if (studentDownloadReportBtn) {
        studentDownloadReportBtn.addEventListener('click', () => {
            if (!latestEvaluationReport) return;
            const rep = latestEvaluationReport;
            let reportTxt = `================================================================================\n`;
            reportTxt += `STUDENT LAB EVALUATION & GRADE REPORT\n`;
            reportTxt += `================================================================================\n`;
            reportTxt += `Assignment  : ${rep.lab_title}\n`;
            reportTxt += `Final Grade : ${rep.grade_letter} (${rep.percentage}%)\n`;
            reportTxt += `Total Score : ${rep.total_score} / ${rep.max_score} pts\n`;
            reportTxt += `Summary     : ${rep.passed_count} Passed | ${rep.failed_count} Failed\n`;
            reportTxt += `--------------------------------------------------------------------------------\n\n`;
            reportTxt += `ITEMIZED CHECKLIST BREAKDOWN:\n`;
            rep.results.forEach((r, idx) => {
                const num = String(idx + 1).padStart(2, '0');
                reportTxt += `[${r.passed ? 'PASSED' : 'FAILED'}] #${num} (${r.points_earned}/${r.points_possible} pts): ${r.description}\n`;
                reportTxt += `   Feedback: ${r.feedback}\n`;
                if (r.actual_value) reportTxt += `   Actual  : ${r.actual_value}\n`;
                reportTxt += `\n`;
            });

            const blob = new Blob([reportTxt], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `grade_report_${rep.grade_letter}.txt`;
            a.click();
            URL.revokeObjectURL(url);
            showToast("Downloaded grade_report.txt");
        });
    }

    // --- SHARED TOPOLOGY GRAPH RENDERER ---
    // The idle panel markup is captured once, because showLoading() replaces the
    // panel's contents. Without this snapshot the #empty-state-title and
    // #empty-state-desc elements are destroyed on the first load and can never
    // be restored, leaving the panel stuck on a stale progress message.
    const emptyStateDefaultHTML = emptyState ? emptyState.innerHTML : '';
    let pendingOperations = 0;

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    }

    function showLoading(msg) {
        if (!emptyState) return;
        pendingOperations++;
        emptyState.dataset.panelState = 'loading';
        emptyState.style.display = 'block';
        emptyState.innerHTML = `<div class="status-dot pulsing" style="width:24px;height:24px;margin:0 auto 12px;"></div><p>${msg}</p>`;
    }

    // Lets a handler put its own message in the panel and keep it: hideLoading()
    // will not overwrite a panel that something else has claimed.
    function showPanelMessage(html) {
        if (!emptyState) return;
        emptyState.dataset.panelState = 'message';
        emptyState.style.display = 'block';
        emptyState.innerHTML = html;
    }

    function hideLoading() {
        if (!emptyState) return;
        pendingOperations = Math.max(0, pendingOperations - 1);
        if (pendingOperations > 0) return;   // another request is still running

        // If a handler already put its own result in the panel -- "No Devices
        // Found", a parse error -- leave it alone. Overwriting it would hide the
        // very explanation the user needs and make a failure look like nothing
        // happened at all.
        if (emptyState.dataset.panelState === 'message') return;

        // Otherwise rebuild the idle markup, so #empty-state-title and
        // #empty-state-desc exist again even while the panel stays hidden.
        emptyState.innerHTML = emptyStateDefaultHTML;
        delete emptyState.dataset.panelState;
        applyEmptyStateText(currentMode);

        const hasTopology = currentTopology && Object.keys(currentTopology.devices || {}).length > 0;
        emptyState.style.display = hasTopology ? 'none' : 'block';
    }

    // Re-queries the nodes each time, since showLoading() replaces them.
    function applyEmptyStateText(mode) {
        const titleEl = document.getElementById('empty-state-title');
        const descEl = document.getElementById('empty-state-desc');
        if (!titleEl || !descEl) return;
        if (mode === 'teacher') {
            titleEl.textContent = 'No Reference Network';
            descEl.textContent = 'Upload your Packet Tracer (.pkt/.xml) or config bundle above to inspect reference topology and generate lab instructions.';
        } else if (mode === 'student') {
            titleEl.textContent = 'No Evaluation Run';
            descEl.textContent = "Upload the instructor's instructions.txt and your completed lab solution to run automated grading and visual error detection.";
        } else {
            titleEl.textContent = 'No Network Loaded';
            descEl.textContent = 'Upload a Packet Tracer file or Cisco .txt configuration bundle to run multi-signal topology discovery.';
        }
    }

    // Reads an error body that may not be JSON (a proxy or crash can return HTML).
    async function describeFailure(res, fallback) {
        try {
            const body = await res.json();
            if (body && body.detail) {
                return typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
            }
        } catch (e) { /* response was not JSON */ }
        return fallback || `Server error ${res.status} ${res.statusText}`;
    }

    function renderTopology(data) {
        currentTopology = data;
        if (emptyState) {
            delete emptyState.dataset.panelState;
            emptyState.style.display = 'none';
        }
        svg.innerHTML = '';

        const devices = Object.values(data.devices || {});
        const links = data.links || [];
        const conflicts = data.conflicts || [];

        if (conflictCard) {
            renderConflictSummary(conflicts);
        }

        if (devices.length === 0) {
            showPanelMessage(`<div class="empty-icon">⚠️</div><h3>No Devices Found</h3>`
                + `<p>The file was read, but no device configurations could be extracted from it.</p>`
                + `<p class="empty-hint">If this is a Packet Tracer file, it may have been saved by a newer version than this tool supports. `
                + `Try <strong>File &gt; Save As</strong> in Packet Tracer, or upload a .zip of each device's <code>show running-config</code> output instead.</p>`);
            return;
        }

        const devEntries = Object.entries(data.devices || {});
        const hasCoordinates = devEntries.some(([_, d]) => d.x_coord !== null && d.y_coord !== null);

        if (hasCoordinates) {
            simulationNodes = devEntries.map(([devKey, d]) => {
                const x = d.x_coord !== null ? d.x_coord : 400;
                const y = d.y_coord !== null ? d.y_coord : 300;
                return { id: devKey, device: d, x: x, y: y };
            });
        } else {
            const radius = 220;
            const centerX = 450;
            const centerY = 320;
            simulationNodes = devEntries.map(([devKey, d], idx) => {
                const angle = (idx / devEntries.length) * 2 * Math.PI - Math.PI / 2;
                return {
                    id: devKey,
                    device: d,
                    x: centerX + radius * Math.cos(angle),
                    y: centerY + radius * Math.sin(angle)
                };
            });
        }

        simulationLinks = links.map(l => {
            const source = simulationNodes.find(n => n.id === l.source_device);
            const target = simulationNodes.find(n => n.id === l.target_device);
            return {
                data: l,
                source: source || { x: 200, y: 200, id: l.source_device },
                target: target || { x: 400, y: 200, id: l.target_device }
            };
        });

        fitGraphToViewport();
    }

    function fitGraphToViewport() {
        if (!simulationNodes || simulationNodes.length === 0) return;

        const rect = svg.getBoundingClientRect();
        const width = rect.width || 800;
        const height = rect.height || 600;

        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        simulationNodes.forEach(n => {
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

        viewTransform.k = scale;
        viewTransform.x = (width / 2) - graphCenterX * scale;
        viewTransform.y = (height / 2) - graphCenterY * scale;

        drawSvgGraph();
    }

    function createSvgBadge(x, y, text, badgeClass = 'port-label-badge', isIp = false) {
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

    function drawSvgGraph() {
        svg.innerHTML = '';
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        svg.appendChild(defs);

        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('id', 'graph-root');
        g.setAttribute('transform', `translate(${viewTransform.x}, ${viewTransform.y}) scale(${viewTransform.k})`);
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

            const dx = tgt.x - src.x;
            const dy = tgt.y - src.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const ux = dx / dist;
            const uy = dy / dist;
            const px = -uy;
            const py = ux;

            const midX = (src.x + tgt.x) / 2;
            const midY = (src.y + tgt.y) / 2;

            const badgeBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
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

            const badgeLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
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
            if (showPortLabels) {
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
            if (showIpLabels && currentTopology && currentTopology.devices) {
                const srcDev = currentTopology.devices[link.source_device];
                const tgtDev = currentTopology.devices[link.target_device];
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
            const isHost = dev.device_type === 'host';
            let nodeColor = '#3B82F6';
            if (isPlaceholder) {
                nodeColor = '#9CA3AF';
            } else if (isSwitch) {
                nodeColor = '#10B981';
            } else if (isHost) {
                nodeColor = '#8B5CF6';
            }

            const glowCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            glowCircle.setAttribute('cx', node.x);
            glowCircle.setAttribute('cy', node.y);
            glowCircle.setAttribute('r', '26');
            glowCircle.setAttribute('fill', isPlaceholder ? 'rgba(156, 163, 175, 0.15)' : (isSwitch ? 'rgba(16, 185, 129, 0.15)' : (isHost ? 'rgba(139, 92, 246, 0.15)' : 'rgba(59, 130, 246, 0.15)')));
            nodeGroup.appendChild(glowCircle);

            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', node.x);
            circle.setAttribute('cy', node.y);
            circle.setAttribute('r', '20');
            circle.setAttribute('fill', '#1F2937');
            circle.setAttribute('stroke', nodeColor);
            circle.setAttribute('stroke-width', '2');
            if (isPlaceholder) {
                circle.setAttribute('stroke-dasharray', '4,3');
            }
            nodeGroup.appendChild(circle);

            let badgeLetter = 'R';
            if (isPlaceholder) badgeLetter = '?';
            else if (isSwitch) badgeLetter = 'SW';
            else if (isHost) badgeLetter = 'PC';

            const iconText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            iconText.setAttribute('x', node.x);
            iconText.setAttribute('y', node.y + 4);
            iconText.setAttribute('text-anchor', 'middle');
            iconText.setAttribute('fill', nodeColor);
            iconText.setAttribute('font-size', '10.5px');
            iconText.setAttribute('font-weight', 'bold');
            iconText.setAttribute('font-family', 'Outfit, sans-serif');
            iconText.textContent = badgeLetter;
            nodeGroup.appendChild(iconText);

            const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('x', node.x);
            label.setAttribute('y', node.y + 36);
            label.setAttribute('text-anchor', 'middle');
            label.classList.add('node-hostname-label');
            label.textContent = isPlaceholder ? '???' : (dev.display_name || dev.hostname);
            nodeGroup.appendChild(label);

            nodeGroup.addEventListener('click', (e) => {
                e.stopPropagation();
                openNodeDiagnosticDrawer(dev);
            });

            nodeGroup.addEventListener('mousedown', (e) => {
                e.stopPropagation();
                isDraggingNode = true;
                draggedNode = node;
                nodeGroup.style.cursor = 'grabbing';
            });

            g.appendChild(nodeGroup);
        });
    }

    // --- Interactive Mouse Zoom & Pan ---
    svg.addEventListener('wheel', (e) => {
        if (!currentTopology) return;
        e.preventDefault();

        const rect = svg.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89;
        const newScale = Math.max(0.2, Math.min(viewTransform.k * zoomFactor, 3.5));

        viewTransform.x = mouseX - (mouseX - viewTransform.x) * (newScale / viewTransform.k);
        viewTransform.y = mouseY - (mouseY - viewTransform.y) * (newScale / viewTransform.k);
        viewTransform.k = newScale;

        const g = document.getElementById('graph-root');
        if (g) {
            g.setAttribute('transform', `translate(${viewTransform.x}, ${viewTransform.y}) scale(${viewTransform.k})`);
        }
    }, { passive: false });

    svg.addEventListener('mousedown', (e) => {
        if (e.target === svg || e.target.id === 'graph-root' || e.target.tagName === 'svg') {
            isPanning = true;
            panStartX = e.clientX - viewTransform.x;
            panStartY = e.clientY - viewTransform.y;
            svg.style.cursor = 'grabbing';
        }
    });

    window.addEventListener('mousemove', (e) => {
        if (isDraggingNode && draggedNode) {
            const rect = svg.getBoundingClientRect();
            draggedNode.x = (e.clientX - rect.left - viewTransform.x) / viewTransform.k;
            draggedNode.y = (e.clientY - rect.top - viewTransform.y) / viewTransform.k;
            drawSvgGraph();
        } else if (isPanning) {
            viewTransform.x = e.clientX - panStartX;
            viewTransform.y = e.clientY - panStartY;
            const g = document.getElementById('graph-root');
            if (g) {
                g.setAttribute('transform', `translate(${viewTransform.x}, ${viewTransform.y}) scale(${viewTransform.k})`);
            }
        }
    });

    window.addEventListener('mouseup', () => {
        if (isDraggingNode) {
            isDraggingNode = false;
            draggedNode = null;
        }
        if (isPanning) {
            isPanning = false;
            svg.style.cursor = 'grab';
        }
    });

    // --- Diagnostic Drawer Content ---
    function openEdgeDiagnosticDrawer(link) {
        if (!diagnosticDrawer) return;
        diagnosticDrawer.style.display = 'flex';
        if (drawerEntityType) {
            drawerEntityType.textContent = 'LINK INFERENCE AUDIT';
            drawerEntityType.className = 'drawer-badge badge-green';
        }
        if (drawerTitle) drawerTitle.textContent = `${link.source_device} (${link.source_interface}) ⟷ ${link.target_device} (${link.target_interface})`;

        let html = `
            <div class="diag-section">
                <div class="diag-section-title">Inference Confidence Score</div>
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <span style="font-size:22px;font-weight:700;color:${link.confidence >= 0.8 ? '#10B981' : '#F59E0B'};font-family:JetBrains Mono;">
                        ${(link.confidence * 100).toFixed(1)}%
                    </span>
                    <span class="badge ${link.classification === 'verified' ? 'badge-green' : 'badge-amber'}">
                        ${link.classification.toUpperCase()} LINK
                    </span>
                    <span style="font-size:10.5px;color:#9CA3AF;">Fused Signal Probability</span>
                </div>
            </div>

            <div class="diag-section">
                <div class="diag-section-title">Contributing Evidence Signals (${link.signals ? link.signals.length : 0})</div>
        `;

        if (link.signals) {
            link.signals.forEach(sig => {
                html += `
                    <div class="signal-row">
                        <div>
                            <div class="signal-type">${sig.signal_type}</div>
                            <div style="font-size:10.5px;color:#9CA3AF;margin-top:2px;">${sig.description}</div>
                            ${sig.evidence ? sig.evidence.map(e => `<span class="evidence-tag">📍 ${e}</span>`).join('') : ''}
                        </div>
                        <div class="signal-weight">+${(sig.weight * 100).toFixed(0)}%</div>
                    </div>
                `;
            });
        }
        html += `</div>`;

        if (link.conflicts && link.conflicts.length > 0) {
            html += `
                <div class="diag-section">
                    <div class="diag-section-title" style="color:#EF4444;">Associated Conflicts / Errors</div>
                    ${link.conflicts.map(c => `
                        <div class="conflict-item-card" style="margin-bottom:5px;">
                            <div class="conflict-item-title">${c}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        if (drawerBody) drawerBody.innerHTML = html;
    }

    function openNodeDiagnosticDrawer(dev) {
        if (!diagnosticDrawer) return;
        diagnosticDrawer.style.display = 'flex';
        const isPlaceholder = dev.is_placeholder || dev.display_name === '???';

        if (isPlaceholder) {
            if (drawerEntityType) {
                drawerEntityType.textContent = 'UNKNOWN DEVICE / PEER';
                drawerEntityType.className = 'drawer-badge badge-amber';
            }
            if (drawerTitle) drawerTitle.textContent = `??? (Unknown Connection)`;

            let html = `
                <div class="diag-section">
                    <div class="diag-section-title">Connection Overview</div>
                    <div style="font-size:12px;color:#E5E7EB;margin-bottom:10px;line-height:1.45;">
                        This node represents an active physical or logical connection where the remote peer configuration was not uploaded or is an external/unmanaged device.
                    </div>
            `;
            if (dev.placeholder_for_device) {
                html += `
                    <div class="signal-row">
                        <div>
                            <div style="font-size:9.5px;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.5px;">Discovered Peer ID</div>
                            <div style="font-size:13px;font-weight:700;color:#F59E0B;font-family:JetBrains Mono;margin-top:2px;">${dev.placeholder_for_device}</div>
                            <div style="font-size:10.5px;color:#9CA3AF;margin-top:2px;">Identified via discovery protocols (CDP/LLDP). Configuration file was not submitted.</div>
                        </div>
                    </div>
                `;
            }
            if (dev.placeholder_for_interface) {
                html += `
                    <div class="signal-row">
                        <div>
                            <div style="font-size:9.5px;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.5px;">Local Connected Port</div>
                            <div style="font-size:13px;font-weight:700;color:#60A5FA;font-family:JetBrains Mono;margin-top:2px;">${dev.placeholder_for_interface}</div>
                            <div style="font-size:10.5px;color:#9CA3AF;margin-top:2px;">Port has active carrier status (up/up).</div>
                        </div>
                    </div>
                `;
            }
            html += `</div>`;
            if (drawerBody) drawerBody.innerHTML = html;
            return;
        }

        if (drawerEntityType) {
            drawerEntityType.textContent = 'DEVICE PROFILE';
            drawerEntityType.className = 'drawer-badge badge-blue';
        }
        if (drawerTitle) drawerTitle.textContent = `${dev.hostname} (${(dev.device_type || 'router').toUpperCase()})`;

        let html = `
            <div class="diag-section">
                <div class="diag-section-title">Interfaces & IP Allocation</div>
        `;

        if (dev.interfaces) {
            Object.values(dev.interfaces).forEach(intf => {
                const isDown = intf.admin_status === 'administratively down' || intf.line_status === 'down';
                html += `
                    <div class="signal-row" style="flex-direction:column;align-items:flex-start;">
                        <div style="display:flex;justify-content:space-between;width:100%;">
                            <strong style="font-family:JetBrains Mono;">${intf.name}</strong>
                            <span class="badge ${isDown ? 'badge-red' : 'badge-green'}">${intf.admin_status}/${intf.line_status}</span>
                        </div>
                        <div style="font-size:10.5px;color:#9CA3AF;margin-top:3px;">
                            ${intf.ip_address ? `IP: <strong>${intf.ip_address}/${intf.cidr}</strong> (${intf.network_address})` : 'IP: (Unassigned)'}
                            ${intf.switchport_mode ? ` | Switchport: <strong>${intf.switchport_mode}</strong> (VLAN ${intf.access_vlan || intf.trunk_native_vlan})` : ''}
                        </div>
                        ${intf.description ? `<div style="font-size:10.5px;color:#60A5FA;">desc: ${intf.description}</div>` : ''}
                    </div>
                `;
            });
        }
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
                            <div style="font-size:9.5px;color:#9CA3AF;">Platform: ${cdp.platform || 'Cisco'} | Remote IP: ${cdp.remote_ip || 'N/A'}</div>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        }

        if (drawerBody) drawerBody.innerHTML = html;
    }

    function renderConflictSummary(conflicts) {
        if (!conflicts || conflicts.length === 0) {
            if (conflictCard) conflictCard.style.display = 'none';
            return;
        }

        if (conflictCard) conflictCard.style.display = 'block';
        if (conflictBadgeCount) {
            conflictBadgeCount.textContent = `${conflicts.length} Issue${conflicts.length > 1 ? 's' : ''}`;
            conflictBadgeCount.className = `badge ${conflicts.some(c => c.severity === 'error') ? 'badge-red' : 'badge-amber'}`;
        }
        if (conflictItemsList) {
            conflictItemsList.innerHTML = '';
            conflicts.forEach(c => {
                const card = document.createElement('div');
                card.className = `conflict-item-card ${c.severity === 'warning' ? 'warning' : ''}`;
                let html = `
                    <div class="conflict-item-title">${c.title}</div>
                    <div class="conflict-item-desc">${c.description}</div>
                `;
                if (c.evidence_citations && c.evidence_citations.length > 0) {
                    c.evidence_citations.forEach(cit => {
                        html += `<span class="evidence-tag">📍 ${cit}</span>`;
                    });
                }
                card.innerHTML = html;
                conflictItemsList.appendChild(card);
            });
        }
    }

    // ---------------------------------------------------------------
    // Batch Grading: grade a whole class, export a gradebook CSV
    // ---------------------------------------------------------------
    const batchInstInput = document.getElementById('batch-inst-input');
    const batchSubInput = document.getElementById('batch-sub-input');
    const batchGradeBtn = document.getElementById('batch-grade-btn');
    const batchFileCount = document.getElementById('batch-file-count');
    const batchResults = document.getElementById('batch-results');
    const batchSummary = document.getElementById('batch-summary');
    const batchTableBody = document.getElementById('batch-table-body');
    const batchCsvBtn = document.getElementById('batch-csv-btn');
    let batchCsvText = '';
    let batchLabTitle = 'lab';

    if (batchSubInput) {
        batchSubInput.addEventListener('change', () => {
            const n = batchSubInput.files.length;
            batchFileCount.textContent = n === 0
                ? 'No submissions selected'
                : `${n} submission${n === 1 ? '' : 's'} selected`;
        });
    }

    if (batchGradeBtn) {
        batchGradeBtn.addEventListener('click', async () => {
            if (!batchInstInput.files.length) {
                alert('Please choose the instructions.txt file first.');
                return;
            }
            if (!batchSubInput.files.length) {
                alert('Please choose at least one student submission.');
                return;
            }

            const formData = new FormData();
            formData.append('instructions_file', batchInstInput.files[0]);
            for (const file of batchSubInput.files) {
                formData.append('student_files', file);
            }

            // Batch grading belongs to the left panel, so show progress on the
            // button itself rather than taking over the topology map.
            const originalLabel = batchGradeBtn.innerHTML;
            const count = batchSubInput.files.length;
            batchGradeBtn.disabled = true;
            batchGradeBtn.innerHTML = `<span>Grading ${count} submission${count === 1 ? '' : 's'}...</span>`;

            try {
                const response = await fetch('/api/evaluate/batch', { method: 'POST', body: formData });
                if (!response.ok) {
                    const err = await response.json().catch(() => ({ detail: response.statusText }));
                    throw new Error(err.detail || 'Batch grading failed');
                }
                const data = await response.json();
                batchCsvText = data.csv;
                batchLabTitle = data.lab_title || 'lab';
                renderBatchResults(data);
            } catch (err) {
                alert(`Batch grading failed: ${err.message}`);
            } finally {
                batchGradeBtn.disabled = false;
                batchGradeBtn.innerHTML = originalLabel;
            }
        });
    }

    function renderBatchResults(data) {
        const s = data.summary;
        batchSummary.innerHTML = `
            <div class="batch-stat"><span class="batch-stat-value">${s.graded}</span><span class="batch-stat-label">Graded</span></div>
            <div class="batch-stat"><span class="batch-stat-value">${s.average_percentage}%</span><span class="batch-stat-label">Class Average</span></div>
            <div class="batch-stat"><span class="batch-stat-value">${s.highest_percentage}%</span><span class="batch-stat-label">Highest</span></div>
            <div class="batch-stat"><span class="batch-stat-value">${s.lowest_percentage}%</span><span class="batch-stat-label">Lowest</span></div>
            <div class="batch-stat ${s.errors > 0 ? 'batch-stat-error' : ''}"><span class="batch-stat-value">${s.errors}</span><span class="batch-stat-label">Errors</span></div>
        `;

        batchTableBody.innerHTML = '';
        data.results.forEach(row => {
            const tr = document.createElement('tr');
            const failed = row.status !== 'graded';
            tr.className = failed ? 'batch-row-error' : '';
            const statusText = failed ? row.status : `${row.passed_count} passed / ${row.failed_count} failed`;
            tr.innerHTML = `
                <td class="batch-student">${escapeHtml(row.student)}</td>
                <td>${row.total_score} / ${row.max_score}</td>
                <td class="batch-pct">${row.percentage}%</td>
                <td><span class="grade-chip grade-${row.grade_letter.replace('+','plus').replace('-','none')}">${row.grade_letter}</span></td>
                <td class="batch-status">${escapeHtml(statusText)}</td>
            `;
            batchTableBody.appendChild(tr);
        });

        batchResults.style.display = 'block';
    }

    if (batchCsvBtn) {
        batchCsvBtn.addEventListener('click', () => {
            if (!batchCsvText) return;
            // A BOM keeps Excel from mangling non-ASCII student names.
            const blob = new Blob(['﻿' + batchCsvText], { type: 'text/csv;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `grades_${batchLabTitle.replace(/[^a-z0-9]+/gi, '_').toLowerCase()}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    }

});
