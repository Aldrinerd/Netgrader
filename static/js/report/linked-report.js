// static/js/report/linked-report.js
// The linked report (spec 5): missed checkpoints in the list column, the
// student's topology on the map, the selected checkpoint under it. Exactly one
// checkpoint is selected while any are missed; the map follows the selection.
import { el } from '../core/dom.js';
import { icon } from '../core/icons.js';
import { buildLossBar } from './loss-bar.js';
import { createCheckpointList } from './checkpoint-list.js';
import { createCheckpointDetail } from './checkpoint-detail.js';
import {
    missedOf, groupMissed, displayOrder, badgesFor, focusFor, resolveSelection, missedOnDevice,
} from './checkpoints.js';

export function createLinkedReport({ listHost, detailHost, map, onSelectionChange = () => {}, onAsk = () => {} }) {
    let report = null;
    let missed = [];
    let groupBy = 'device';
    let deviceFilter = null;
    let selectedId = null;

    const listSlot = el('div', { className: 'lr-list-slot' });
    const detail = createCheckpointDetail(detailHost, {
        onAsk: result => onAsk(result),
        onBack: () => list.focus(),
    });
    const list = createCheckpointList(listSlot, {
        onSelect: (id, { push }) => select(id, { push }),
        onOpen: () => detail.focus(),
    });

    const visible = () => (deviceFilter ? missedOnDevice(missed, deviceFilter) : missed);
    const groups = () => groupMissed(visible(), groupBy);
    const selected = () => missed.find(r => r.rule_id === selectedId) || null;

    function applyFocus() {
        if (report) map.setFocus(focusFor(selected(), badgesFor(missed)));
    }

    function select(id, { push = false, notify = true } = {}) {
        if (!report) return;
        const target = resolveSelection(displayOrder(groups()), id);
        selectedId = target ? target.rule_id : null;
        list.render({ groups: groups(), selectedId });
        if (target) detail.show(target); else detail.clear();
        applyFocus();
        if (notify && selectedId) onSelectionChange(selectedId, { push });
    }

    function scoreHeader() {
        return el('header', { className: 'lr-score' }, [
            el('span', { className: 'lr-score-pct', text: `${report.percentage}%` }),
            el('span', { className: 'lr-score-pts', text: `${Number(report.total_score).toFixed(1)} / ${Number(report.max_score).toFixed(1)}` }),
            el('span', { className: 'lr-grade', text: report.grade_letter }),
            el('p', { className: 'lr-lab', text: report.lab_title }),
        ]);
    }

    function toolbar() {
        const bar = el('div', { className: 'lr-toolbar' }, [
            el('h3', { className: 'report-subhead', id: 'lr-missed-heading', text: `Missed checkpoints (${visible().length})` }),
        ]);
        const toggle = el('div', { className: 'lr-group-toggle', role: 'group', 'aria-label': 'Group missed checkpoints by' });
        [['device', 'Device'], ['topic', 'Topic']].forEach(([key, label]) => {
            const b = el('button', { type: 'button', className: 'btn btn-sm toggle-btn', 'aria-pressed': String(groupBy === key), text: label });
            b.addEventListener('click', () => { groupBy = key; renderList(); select(selectedId); });
            toggle.appendChild(b);
        });
        bar.appendChild(toggle);
        if (deviceFilter) {
            const chip = el('button', { type: 'button', className: 'lr-filter-chip' }, [
                'Showing ' + deviceFilter + ' only. ', el('strong', { text: 'Show all' }),
            ]);
            chip.addEventListener('click', () => { deviceFilter = null; renderList(); select(selectedId); list.focus(); });
            bar.appendChild(chip);
        }
        return bar;
    }

    function passedDisclosure(passed) {
        const n = passed.length;
        return el('details', { className: 'lr-passed' }, [
            el('summary', { text: `${n} checkpoint${n === 1 ? '' : 's'} passed` }),
            el('ul', {}, passed.map(r => el('li', {}, [icon('check'), el('span', { text: r.description })]))),
        ]);
    }

    function renderList() {
        listHost.textContent = '';
        listHost.appendChild(scoreHeader());
        const loss = buildLossBar(report.study_topics);
        if (loss) listHost.appendChild(loss);
        if (!missed.length) {
            listHost.appendChild(el('p', { className: 'lr-all-passed' }, [
                icon('check'), ` All ${report.results.length} checkpoints passed`,
            ]));
            return;
        }
        listHost.appendChild(toolbar());
        listHost.appendChild(listSlot);
        const passed = report.results.filter(r => r.passed);
        if (passed.length) listHost.appendChild(passedDisclosure(passed));
    }

    return {
        show(next, { selectedId: wanted = null } = {}) {
            report = next;
            missed = missedOf(next);
            deviceFilter = null;
            selectedId = null;
            renderList();
            if (missed.length) {
                select(wanted);
            } else {
                detail.clear();
                applyFocus();
            }
        },
        select,
        // Activating a device on the map: filter to it and select its first
        // missed checkpoint. False when it has none, so the caller can fall
        // back to the device inspector.
        showDevice(hostname) {
            if (!report || !missedOnDevice(missed, hostname).length) return false;
            deviceFilter = hostname;
            renderList();
            select(null, { push: true });
            list.focus();
            return true;
        },
        clear() {
            report = null;
            missed = [];
            selectedId = null;
            deviceFilter = null;
            listHost.textContent = '';
            detail.clear();
        },
        applyFocus,
        setAskAvailable: available => detail.setAskAvailable(available),
        getSelectedId: () => selectedId,
        focusList: () => list.focus(),
    };
}
