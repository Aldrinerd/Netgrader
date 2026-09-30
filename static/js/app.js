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
        // Text only: some messages carry a student's filename.
        const icon = document.createElement('span');
        icon.textContent = '✨';
        const text = document.createElement('span');
        text.textContent = msg;
        toast.append(icon, text);
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
        renderStudyTopics(report);
        // Fired only after the score is rendered. If it never returns, the
        // student still has a complete, final grade on screen.
        requestNarrative(report);
        openReportChat(report);
    }

    // --- Local AI status (header indicator) ---
    // Tells everyone up front whether the paragraphs and chat will come from
    // the local model or not, instead of leaving it to a badge that only
    // appears after a summary loads.
    const aiStatusBtn = document.getElementById('ai-status');
    const aiStatusLabel = document.getElementById('ai-status-label');
    const chatBoxes = new Map();   // host element -> chat box, told when status changes
    let aiStatusPromise = null;

    function refreshAiStatus() {
        aiStatusPromise = fetch('/api/llm/status')
            .then(res => (res.ok ? res.json() : Promise.reject(new Error(`status ${res.status}`))))
            .catch(() => ({ enabled: true, available: false, detail: 'could not reach the server to check' }))
            .then(status => {
                paintAiStatus(status);
                chatBoxes.forEach(box => box.setAvailability(status));
                return status;
            });
        return aiStatusPromise;
    }

    function paintAiStatus(status) {
        if (!aiStatusBtn) return;
        let state, label, title;
        if (status.available) {
            state = 'ready';
            label = `AI: ${status.model}`;
            title = `Local AI model ${status.model} is running on the server. Summaries, briefings and follow-up answers are written by it. Grades never are.`;
        } else if (status.enabled === false) {
            state = 'off';
            label = 'AI: off';
            title = 'The local AI layer is switched off (NCA_LLM_ENABLED=0). Summaries use built-in text; follow-up chat is unavailable.';
        } else {
            state = 'missing';
            label = /not pulled/.test(status.detail || '') ? 'AI: model missing' : 'AI: not installed';
            title = `Local AI unavailable: ${status.detail}. Summaries use built-in text; follow-up chat is unavailable. Click to check again.`;
        }
        aiStatusBtn.dataset.state = state;
        aiStatusBtn.title = title;
        if (aiStatusLabel) aiStatusLabel.textContent = label;
    }

    if (aiStatusBtn) {
        aiStatusBtn.addEventListener('click', async () => {
            if (aiStatusLabel) aiStatusLabel.textContent = 'AI: checking';
            aiStatusBtn.dataset.state = 'checking';
            const status = await refreshAiStatus();
            showToast(status.available ? `Local AI ready (${status.model})` : `Local AI unavailable: ${status.detail}`);
        });
    }
    refreshAiStatus();
    // The server caches its probe for 30 s, so this costs one cheap request.
    setInterval(refreshAiStatus, 60000);

    // --- Follow-up chat ---
    // One reusable box: under a student's report, and under the class briefing.
    // It never shows a prewritten answer. If the model is unavailable the box
    // says so and disables itself.
    function createChatBox(host, { title, suggestions, endpoint, buildPayload, readyNote }) {
        host.style.display = 'block';
        host.innerHTML = `
            <div class="ai-chat-head">
                <span>${escapeHtml(title)}</span>
                <span class="narrative-src model ai-chat-badge">Local AI</span>
            </div>
            <div class="ai-chat-log" aria-live="polite"></div>
            <div class="ai-chat-suggestions"></div>
            <form class="ai-chat-form">
                <textarea class="ai-chat-input" rows="2" maxlength="1000"
                    placeholder="Ask a follow-up question... (Enter to send, Shift+Enter for a new line)"></textarea>
                <button type="submit" class="btn btn-primary btn-sm ai-chat-send">Send</button>
            </form>
            <div class="ai-chat-note"></div>
        `;
        const log = host.querySelector('.ai-chat-log');
        const chips = host.querySelector('.ai-chat-suggestions');
        const form = host.querySelector('.ai-chat-form');
        const input = host.querySelector('.ai-chat-input');
        const sendBtn = host.querySelector('.ai-chat-send');
        const note = host.querySelector('.ai-chat-note');
        const history = [];
        let busy = false;
        let available = false;

        suggestions.forEach(text => {
            const chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'ai-chat-chip';
            chip.textContent = text;
            chip.addEventListener('click', () => ask(text));
            chips.appendChild(chip);
        });

        function addMessage(kind, text) {
            const msg = document.createElement('div');
            msg.className = `ai-msg ai-msg-${kind}`;
            msg.textContent = text;
            log.appendChild(msg);
            log.scrollTop = log.scrollHeight;
            return msg;
        }

        function syncControls() {
            const enabled = available && !busy;
            input.disabled = !available;
            sendBtn.disabled = !enabled;
            chips.querySelectorAll('button').forEach(b => { b.disabled = !enabled; });
            chips.style.display = available && history.length === 0 ? 'flex' : 'none';
        }

        async function ask(question) {
            question = (question || '').trim();
            if (!question || busy || !available) return;
            input.value = '';
            history.push({ role: 'user', content: question });
            addMessage('user', question);
            busy = true;
            syncControls();
            const pending = addMessage('pending', 'Thinking... the local model can take up to a minute on a lab computer.');
            try {
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(buildPayload(history))
                });
                if (!res.ok) throw new Error(await describeFailure(res, `The AI could not answer (error ${res.status}).`));
                const data = await res.json();
                pending.remove();
                history.push({ role: 'assistant', content: data.reply });
                addMessage('assistant', data.reply);
            } catch (err) {
                pending.remove();
                // Drop the unanswered question from history and hand it back,
                // so a retry does not send it twice.
                history.pop();
                addMessage('error', err.message);
                input.value = question;
                // The model may have gone away; re-check so the header and
                // every chat box reflect it.
                refreshAiStatus();
            } finally {
                busy = false;
                syncControls();
                if (available) input.focus();
            }
        }

        form.addEventListener('submit', (e) => { e.preventDefault(); ask(input.value); });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(input.value); }
        });

        const box = {
            setAvailability(status) {
                available = !!status.available;
                if (available) {
                    note.textContent = readyNote(status.model);
                    note.className = 'ai-chat-note';
                } else {
                    note.textContent = `Follow-up questions need the local AI model, which is not available on the server (${status.detail}). Everything above is complete without it.`;
                    note.className = 'ai-chat-note ai-chat-note-off';
                }
                syncControls();
            }
        };
        chatBoxes.set(host, box);
        box.setAvailability({ available: false, detail: 'checking' });
        (aiStatusPromise || refreshAiStatus()).then(status => box.setAvailability(status));
        return box;
    }

    function openReportChat(report) {
        const host = document.getElementById('report-chat');
        if (!host) return;
        // Only the checkpoint findings are used, so the topology is not sent.
        const findings = { ...report, topology: {} };
        createChatBox(host, {
            title: 'Ask about your results',
            suggestions: report.failed_count > 0
                ? ['Why did I lose the most points?', 'Explain my first mistake in simple terms', 'Which show commands should I use to check my work?']
                : ['What could I practise next to go further?'],
            endpoint: '/api/chat/report',
            buildPayload: messages => ({ report: findings, messages }),
            readyNote: model => `Answered by the local model (${model}) using only the graded results above. It cannot change your grade. Check anything important with your instructor.`
        });
    }

    function openClassChat(rows) {
        const host = document.getElementById('batch-chat');
        if (!host) return;
        // The results table, with names (the submission filenames). Only the
        // instructor can reach this, and the model runs on this computer.
        // Rankings are computed by the server, not by the model.
        const students = rows.map(r => ({
            name: r.student,
            status: r.status,
            percentage: r.percentage,
            grade_letter: r.grade_letter,
            total_score: r.total_score,
            max_score: r.max_score,
            failed_count: r.failed_count,
            topics: ((r.report && r.report.study_topics) || []).map(t => t.topic)
        }));
        if (students.length === 0) { host.style.display = 'none'; return; }
        createChatBox(host, {
            title: 'Ask about this class',
            suggestions: ['Who got the lowest grade?', 'Which students need the most help, and with what?', 'Which topic should I reteach first?'],
            endpoint: '/api/chat/class',
            buildPayload: messages => ({ students, messages }),
            readyNote: model => `Answered by the local model (${model}) from this results table, including student names. It runs on this computer; nothing is sent anywhere else.`
        });
    }

    async function requestNarrative(report) {
        const host = document.getElementById('report-narrative');
        if (!host) return;
        host.style.display = 'block';
        host.innerHTML = `<div class="narrative-loading">Preparing your summary...</div>`;
        try {
            const res = await fetch('/api/report/narrative', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(report)
            });
            if (!res.ok) throw new Error('narrative unavailable');
            const data = await res.json();
            const badge = data.source === 'model'
                ? `<span class="narrative-src model">AI summary</span>`
                : `<span class="narrative-src template">Built-in guidance</span>`;
            host.innerHTML = `<div class="narrative-head">Your instructor's summary ${badge}</div>`
                + `<p class="narrative-text">${escapeHtml(data.text)}</p>`;
        } catch (err) {
            // Purely additive: losing it costs the student nothing.
            host.style.display = 'none';
            host.innerHTML = '';
        }
    }

    function renderStudyTopics(report) {
        const host = document.getElementById('report-study-topics');
        if (!host) return;
        const topics = report.study_topics || [];
        if (topics.length === 0) {
            host.style.display = 'none';
            host.innerHTML = '';
            return;
        }
        host.style.display = 'block';
        host.innerHTML = '<div class="study-header">What to study next</div>'
            + topics.map(t => `
                <div class="study-topic">
                    <div class="study-topic-top">
                        <span class="study-topic-name">${escapeHtml(t.topic)}</span>
                        <span class="study-topic-cost">-${t.points_lost} pts</span>
                    </div>
                    <div class="study-topic-why">${escapeHtml(t.why_it_matters)}</div>
                    <div class="study-topic-count">${t.checkpoints_failed} checkpoint${t.checkpoints_failed === 1 ? '' : 's'} affected</div>
                </div>`).join('');
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

        results.forEach(res => reportResultsList.appendChild(buildRuleResultCard(res)));
    }

    // One checkpoint as a card. Shared by the Student Grading report and the
    // instructor's per-student review in Batch Grading, so both show the same
    // detail. Every field is escaped: descriptions and "Found:" values can carry
    // hostnames and config text taken straight from a student's file.
    function buildRuleResultCard(res) {
        const card = document.createElement('div');
        card.className = `rule-result-card ${res.passed ? 'passed' : 'failed'}`;
        card.innerHTML = `
            <div class="rule-res-top">
                <span class="rule-res-desc">${res.passed ? '✅' : '❌'} ${escapeHtml(res.description)}</span>
                <span class="rule-res-pts">${res.points_earned.toFixed(1)} / ${res.points_possible.toFixed(1)} pts</span>
            </div>
            <div class="rule-res-feedback">${escapeHtml(res.feedback)}</div>
            ${res.actual_value ? `<div class="rule-res-actual">Found: ${escapeHtml(res.actual_value)}</div>` : ''}
            ${res.guidance ? `<div class="rule-res-guidance"><span class="guidance-label">How to fix this</span>${escapeHtml(res.guidance)}</div>` : ''}
        `;
        return card;
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
            downloadText(buildReportText(rep), `grade_report_${rep.grade_letter}.txt`);
            showToast("Downloaded grade_report.txt");
        });
    }

    // Plain-text grade report. `studentName` is set when an instructor exports
    // one student's report from Batch Grading.
    function buildReportText(rep, studentName) {
        let reportTxt = `================================================================================\n`;
        reportTxt += `STUDENT LAB EVALUATION & GRADE REPORT\n`;
        reportTxt += `================================================================================\n`;
        if (studentName) reportTxt += `Student     : ${studentName}\n`;
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
            if (r.guidance) reportTxt += `   Guidance: ${r.guidance}\n`;
            reportTxt += `\n`;
        });

        if (rep.study_topics && rep.study_topics.length) {
            reportTxt += `WHAT TO STUDY NEXT:\n\n`;
            rep.study_topics.forEach((t, i) => {
                reportTxt += `${i + 1}. ${t.topic}  (-${t.points_lost} pts, ${t.checkpoints_failed} checkpoints)\n`;
                reportTxt += `   ${t.why_it_matters}\n\n`;
            });
        }

        return reportTxt;
    }

    function downloadText(text, filename) {
        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // --- SHARED TOPOLOGY GRAPH RENDERER ---
    // The idle panel markup is captured once, because showLoading() replaces the
    // panel's contents. Without this snapshot the #empty-state-title and
    // #empty-state-desc elements are destroyed on the first load and can never
    // be restored, leaving the panel stuck on a stale progress message.
    const emptyStateDefaultHTML = emptyState ? emptyState.innerHTML : '';
    let pendingOperations = 0;

    // Escapes for both element content and quoted attribute values. Anything
    // taken from an uploaded file (device names, descriptions, config lines)
    // or a filename must pass through this before reaching innerHTML.
    function escapeHtml(text) {
        return (text == null ? '' : String(text))
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function showLoading(msg) {
        if (!emptyState) return;
        pendingOperations++;
        emptyState.dataset.panelState = 'loading';
        emptyState.style.display = 'block';
        emptyState.innerHTML = `<div class="status-dot pulsing" style="width:24px;height:24px;margin:0 auto 12px;"></div><p>${escapeHtml(msg)}</p>`;
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

    // Devices to ring in red on the map. Set only when an instructor opens a
    // student's mistakes from Batch Grading; every other render clears it.
    let highlightedDevices = new Set();

    function renderTopology(data, options = {}) {
        currentTopology = data;
        highlightedDevices = new Set(options.highlightDevices || []);
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

    /**
     * Device icons drawn as silhouettes instead of lettered circles: a short
     * cylinder for routers, a flat box with a port row for switches, and a
     * monitor on a stand for PCs. Everything is centred on (x, y) and stays
     * inside the r=26 glow, so node spacing, dragging and hit areas are
     * unchanged from the circle they replace.
     */
    function createDeviceIcon(x, y, color, kind) {
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

            const glowCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            glowCircle.setAttribute('cx', node.x);
            glowCircle.setAttribute('cy', node.y);
            glowCircle.setAttribute('r', '26');
            glowCircle.setAttribute('fill', isPlaceholder ? 'rgba(156, 163, 175, 0.15)' : (isSwitch ? 'rgba(16, 185, 129, 0.15)' : (isHost ? 'rgba(139, 92, 246, 0.15)' : 'rgba(59, 130, 246, 0.15)')));
            nodeGroup.appendChild(glowCircle);

            if (highlightedDevices.has(dev.hostname)) {
                const ring = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                ring.setAttribute('cx', node.x);
                ring.setAttribute('cy', node.y);
                ring.setAttribute('r', '31');
                ring.classList.add('node-mistake-ring');
                nodeGroup.appendChild(ring);
            }

            nodeGroup.appendChild(createDeviceIcon(node.x, node.y, nodeColor, {
                isPlaceholder, isSwitch, isHost, isL3Switch
            }));

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
                        ${escapeHtml(String(link.classification).toUpperCase())} LINK
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
                            <div class="signal-type">${escapeHtml(sig.signal_type)}</div>
                            <div style="font-size:10.5px;color:#9CA3AF;margin-top:2px;">${escapeHtml(sig.description)}</div>
                            ${sig.evidence ? sig.evidence.map(e => `<span class="evidence-tag">📍 ${escapeHtml(e)}</span>`).join('') : ''}
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
                            <div class="conflict-item-title">${escapeHtml(c)}</div>
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
                            <div style="font-size:13px;font-weight:700;color:#F59E0B;font-family:JetBrains Mono;margin-top:2px;">${escapeHtml(dev.placeholder_for_device)}</div>
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
                            <div style="font-size:13px;font-weight:700;color:#60A5FA;font-family:JetBrains Mono;margin-top:2px;">${escapeHtml(dev.placeholder_for_interface)}</div>
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
                            <strong style="font-family:JetBrains Mono;">${escapeHtml(intf.name)}</strong>
                            <span class="badge ${isDown ? 'badge-red' : 'badge-green'}">${escapeHtml(intf.admin_status)}/${escapeHtml(intf.line_status)}</span>
                        </div>
                        <div style="font-size:10.5px;color:#9CA3AF;margin-top:3px;">
                            ${intf.ip_address ? `IP: <strong>${escapeHtml(intf.ip_address)}/${escapeHtml(intf.cidr)}</strong> (${escapeHtml(intf.network_address)})` : 'IP: (Unassigned)'}
                            ${intf.switchport_mode ? ` | Switchport: <strong>${escapeHtml(intf.switchport_mode)}</strong> (VLAN ${escapeHtml(intf.access_vlan || intf.trunk_native_vlan)})` : ''}
                        </div>
                        ${intf.description ? `<div style="font-size:10.5px;color:#60A5FA;">desc: ${escapeHtml(intf.description)}</div>` : ''}
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
                            <strong>${escapeHtml(cdp.device_id)}</strong> on <code>${escapeHtml(cdp.local_interface)}</code> ⟷ <code>${escapeHtml(cdp.remote_interface)}</code>
                            <div style="font-size:9.5px;color:#9CA3AF;">Platform: ${escapeHtml(cdp.platform || 'Cisco')} | Remote IP: ${escapeHtml(cdp.remote_ip || 'N/A')}</div>
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
                    <div class="conflict-item-title">${escapeHtml(c.title)}</div>
                    <div class="conflict-item-desc">${escapeHtml(c.description)}</div>
                `;
                if (c.evidence_citations && c.evidence_citations.length > 0) {
                    c.evidence_citations.forEach(cit => {
                        html += `<span class="evidence-tag">📍 ${escapeHtml(cit)}</span>`;
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
    const batchReviewAllBtn = document.getElementById('batch-review-all-btn');
    const batchCollapseAllBtn = document.getElementById('batch-collapse-all-btn');
    // Table row -> that student's batch result, for "Review all".
    const batchRowData = new WeakMap();
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
            <div class="batch-stat"><span class="batch-stat-value">${s.highest_percentage}%</span><span class="batch-stat-label">Highest</span>${whoScored(data.results, s.highest_percentage)}</div>
            <div class="batch-stat"><span class="batch-stat-value">${s.lowest_percentage}%</span><span class="batch-stat-label">Lowest</span>${whoScored(data.results, s.lowest_percentage)}</div>
            <div class="batch-stat ${s.errors > 0 ? 'batch-stat-error' : ''}"><span class="batch-stat-value">${s.errors}</span><span class="batch-stat-label">Errors</span></div>
        `;

        batchTableBody.innerHTML = '';
        data.results.forEach(row => {
            const tr = document.createElement('tr');
            const failed = row.status !== 'graded';
            tr.className = failed ? 'batch-row-error' : '';
            tr.dataset.student = row.student;
            tr.dataset.pct = row.percentage;
            tr.dataset.graded = failed ? '0' : '1';
            const statusText = failed ? row.status : `${row.passed_count} passed / ${row.failed_count} failed`;
            tr.innerHTML = `
                <td class="batch-student">${escapeHtml(row.student)}</td>
                <td>${row.total_score} / ${row.max_score}</td>
                <td class="batch-pct">${row.percentage}%</td>
                <td><span class="grade-chip grade-${escapeHtml(row.grade_letter.replace('+','plus').replace('-','none'))}">${escapeHtml(row.grade_letter)}</span></td>
                <td class="batch-status">${escapeHtml(statusText)}</td>
                <td class="batch-review-cell"></td>
            `;
            if (!failed && row.report) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn btn-outline btn-sm batch-review-btn';
                btn.textContent = row.failed_count > 0 ? `🔍 Review (${row.failed_count})` : '✅ Review';
                btn.addEventListener('click', () => toggleStudentReview(tr, row));
                batchRowData.set(tr, row);
                tr.querySelector('.batch-review-cell').appendChild(btn);
            } else {
                tr.querySelector('.batch-review-cell').textContent = '—';
            }
            batchTableBody.appendChild(tr);
        });

        batchSort = { key: null, dir: 1 };
        paintSortHeaders();
        batchResults.style.display = 'block';
        requestClassBriefing(data.results);
        openClassChat(data.results);
    }

    // Names under the Highest / Lowest cards. Names are the submission
    // filenames, so this answers "who got the lowest?" without asking the AI.
    function whoScored(rows, pct) {
        const names = rows.filter(r => r.status === 'graded' && r.percentage === pct).map(r => r.student);
        if (names.length === 0) return '';
        const shown = names.slice(0, 2).map(escapeHtml).join('<br>');
        const more = names.length > 2 ? `<br>+${names.length - 2} more` : '';
        return `<span class="batch-stat-who" title="${escapeHtml(names.join('; '))}">${shown}${more}</span>`;
    }

    // --- Sortable batch table ---
    // Click Student to sort by name, Score / % / Grade to sort by percentage;
    // click again to reverse. Open review rows travel with their student, and
    // ungradeable submissions always stay at the bottom.
    let batchSort = { key: null, dir: 1 };

    function sortBatchTable(key) {
        if (!batchTableBody) return;
        // Scores open lowest-first: the students who need attention.
        batchSort = { key, dir: batchSort.key === key ? -batchSort.dir : 1 };
        const pairs = Array.from(batchTableBody.children)
            .filter(tr => !tr.classList.contains('batch-detail-row'))
            .map(tr => {
                const next = tr.nextElementSibling;
                return [tr, next && next.classList.contains('batch-detail-row') ? next : null];
            });
        const value = tr => (key === 'student' ? tr.dataset.student.toLowerCase() : parseFloat(tr.dataset.pct));
        pairs.sort(([a], [b]) => {
            const aErr = a.dataset.graded !== '1';
            const bErr = b.dataset.graded !== '1';
            if (aErr !== bErr) return aErr ? 1 : -1;
            const va = value(a), vb = value(b);
            return (va < vb ? -1 : va > vb ? 1 : 0) * batchSort.dir;
        });
        pairs.forEach(([tr, detail]) => {
            batchTableBody.appendChild(tr);
            if (detail) batchTableBody.appendChild(detail);
        });
        paintSortHeaders();
    }

    function paintSortHeaders() {
        document.querySelectorAll('.batch-sort').forEach(btn => {
            const active = btn.dataset.sort === batchSort.key;
            btn.classList.toggle('active', active);
            btn.dataset.dir = active ? (batchSort.dir === 1 ? 'asc' : 'desc') : '';
            btn.closest('th').setAttribute('aria-sort', active ? (batchSort.dir === 1 ? 'ascending' : 'descending') : 'none');
        });
    }

    document.querySelectorAll('.batch-sort').forEach(btn => {
        btn.addEventListener('click', () => sortBatchTable(btn.dataset.sort));
    });

    // --- Per-student review: where did this student go wrong? ---

    // Opens (or closes) a detail row under the student's table row listing every
    // missed checkpoint, grouped by device, with the same feedback, "Found:"
    // value and fix guidance the student would see in Student Grading.
    function toggleStudentReview(tr, row, forceOpen) {
        const next = tr.nextElementSibling;
        const isOpen = next && next.classList.contains('batch-detail-row');
        if (isOpen && forceOpen !== true) {
            next.remove();
            tr.classList.remove('batch-row-open');
            return;
        }
        if (isOpen) return;

        const detail = document.createElement('tr');
        detail.className = 'batch-detail-row';
        const td = document.createElement('td');
        td.colSpan = 6;
        td.appendChild(buildStudentReview(row));
        detail.appendChild(td);
        tr.after(detail);
        tr.classList.add('batch-row-open');
    }

    function buildStudentReview(row) {
        const report = row.report;
        const missed = report.results.filter(r => !r.passed);
        const pointsLost = missed.reduce((sum, r) => sum + (r.points_possible - r.points_earned), 0);

        const wrap = document.createElement('div');
        wrap.className = 'batch-review';

        const head = document.createElement('div');
        head.className = 'batch-review-head';
        head.innerHTML = missed.length
            ? `<span class="batch-review-title">❌ ${missed.length} checkpoint${missed.length === 1 ? '' : 's'} missed · −${pointsLost.toFixed(1)} pts</span>`
            : `<span class="batch-review-title ok">✅ Every checkpoint passed</span>`;

        const actions = document.createElement('div');
        actions.className = 'batch-review-actions';
        const mapBtn = makeReviewButton('🗺️ Show on map', () => showStudentOnMap(row, missed));
        const passedBtn = makeReviewButton('Show passed too', () => {
            showingPassed = !showingPassed;
            passedBtn.textContent = showingPassed ? 'Mistakes only' : 'Show passed too';
            fillList();
        });
        const dlBtn = makeReviewButton('📥 Report', () => {
            const safe = row.student.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '').toLowerCase() || 'student';
            downloadText(buildReportText(report, row.student), `grade_report_${safe}.txt`);
        });
        actions.append(mapBtn, passedBtn, dlBtn);
        head.appendChild(actions);
        wrap.appendChild(head);

        const topics = report.study_topics || [];
        if (topics.length) {
            const t = document.createElement('div');
            t.className = 'batch-review-topics';
            t.innerHTML = '<span class="batch-review-label">Weakest areas:</span> '
                + topics.slice(0, 3).map(tp => `${escapeHtml(tp.topic)} <span class="batch-review-cost">−${tp.points_lost}</span>`).join(' · ');
            wrap.appendChild(t);
        }

        const list = document.createElement('div');
        list.className = 'batch-review-list';
        wrap.appendChild(list);

        let showingPassed = false;
        function fillList() {
            list.innerHTML = '';
            const shown = showingPassed ? report.results : missed;
            if (shown.length === 0) {
                list.innerHTML = '<div class="batch-review-empty">Nothing to fix for this student.</div>';
                return;
            }
            // Group by device so the instructor sees *where* the mistakes are,
            // not just a flat list.
            const byDevice = new Map();
            shown.forEach(r => {
                const key = r.target_device || 'General';
                if (!byDevice.has(key)) byDevice.set(key, []);
                byDevice.get(key).push(r);
            });
            byDevice.forEach((items, device) => {
                const miss = items.filter(r => !r.passed).length;
                const group = document.createElement('div');
                group.className = 'batch-review-device';
                group.innerHTML = `<div class="batch-review-device-name">${escapeHtml(device)}`
                    + (miss ? ` <span class="batch-review-device-count">${miss} missed</span>` : '')
                    + `</div>`;
                items.forEach(r => group.appendChild(buildRuleResultCard(r)));
                list.appendChild(group);
            });
        }
        fillList();
        return wrap;
    }

    function makeReviewButton(label, onClick) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-outline btn-sm';
        btn.textContent = label;
        btn.addEventListener('click', onClick);
        return btn;
    }

    // Draws the student's own topology on the main map with the devices they
    // got wrong ringed in red.
    function showStudentOnMap(row, missed) {
        const report = row.report;
        if (!report.topology) return;
        const devices = new Set(missed.map(r => r.target_device).filter(Boolean));
        renderTopology(report.topology, { highlightDevices: devices });
        if (canvasMainTitle) canvasMainTitle.textContent = `Reviewing: ${row.student}`;
        showToast(devices.size
            ? `${row.student}: ${devices.size} device${devices.size === 1 ? '' : 's'} with mistakes ringed in red`
            : `${row.student}: no device-level mistakes`);
    }

    if (batchReviewAllBtn) {
        batchReviewAllBtn.addEventListener('click', () => {
            Array.from(batchTableBody.children).forEach(tr => {
                const row = batchRowData.get(tr);
                if (row) toggleStudentReview(tr, row, true);
            });
        });
    }

    if (batchCollapseAllBtn) {
        batchCollapseAllBtn.addEventListener('click', () => {
            batchTableBody.querySelectorAll('.batch-detail-row').forEach(d => d.remove());
            batchTableBody.querySelectorAll('.batch-row-open').forEach(r => r.classList.remove('batch-row-open'));
        });
    }

    async function requestClassBriefing(rows) {
        const host = document.getElementById('batch-briefing');
        if (!host) return;
        const categories = rows
            .filter(r => r.status === 'graded')
            .map(r => r.failed_categories || []);
        if (categories.length === 0) { host.style.display = 'none'; return; }

        host.style.display = 'block';
        host.innerHTML = `<div class="narrative-loading">Analysing class performance...</div>`;
        try {
            const res = await fetch('/api/class/briefing', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ categories_per_student: categories })
            });
            if (!res.ok) throw new Error('briefing unavailable');
            const data = await res.json();
            const badge = data.source === 'model'
                ? `<span class="narrative-src model">AI briefing</span>`
                : `<span class="narrative-src template">Built-in analysis</span>`;
            const concepts = (data.analysis.concepts || []).slice(0, 5).map(c => `
                <div class="concept-row">
                    <span class="concept-name">${escapeHtml(c.topic)}</span>
                    <span class="concept-count">${c.students_affected} of ${data.analysis.submissions_analysed}</span>
                </div>`).join('');
            host.innerHTML = `<div class="narrative-head">Instructional recommendations ${badge}</div>`
                + `<p class="narrative-text">${escapeHtml(data.briefing)}</p>`
                + `<div class="concept-list">${concepts}</div>`;
        } catch (err) {
            host.style.display = 'none';
            host.innerHTML = '';
        }
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
