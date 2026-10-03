// static/js/report/checkpoint-list.js
// Missed checkpoints as one listbox (spec 5.1, 7.1). Focus stays on the
// listbox; aria-activedescendant names the selected row. Arrow keys, Home and
// End move the selection; Enter opens the detail. (?) is a pointer shortcut
// for the same thing and not a tab stop: a button inside an option is invalid.
import { el } from '../core/dom.js';
import { icon } from '../core/icons.js';
import { displayOrder, pointsLost, step } from './checkpoints.js';

function where(result) {
    return [result.target_device, result.target_interface].filter(Boolean).join(' ');
}

export function createCheckpointList(host, { onSelect, onOpen }) {
    const box = el('ul', {
        className: 'cp-list', role: 'listbox', tabindex: '0', 'aria-labelledby': 'lr-missed-heading',
    });
    host.appendChild(box);
    let order = [];
    let selectedId = null;

    box.addEventListener('keydown', (e) => {
        let next = null;
        if (e.key === 'ArrowDown') next = step(order, selectedId, 1);
        else if (e.key === 'ArrowUp') next = step(order, selectedId, -1);
        else if (e.key === 'Home') next = order[0];
        else if (e.key === 'End') next = order[order.length - 1];
        else if (e.key === 'Enter') { e.preventDefault(); onOpen(); return; }
        else return;
        e.preventDefault();
        if (next) onSelect(next.rule_id, { push: false });
    });

    function helpButton(result) {
        const help = el('span', { className: 'cp-help', 'aria-hidden': 'true', title: 'Explain this checkpoint' }, [icon('info')]);
        help.addEventListener('click', (e) => {
            e.stopPropagation();
            onSelect(result.rule_id, { push: true });
            onOpen();
        });
        return help;
    }

    function row(result, index) {
        const option = el('li', {
            className: 'cp-row', role: 'option', id: `cp-option-${index}`,
            'aria-selected': String(result.rule_id === selectedId),
        }, [
            el('span', { className: 'cp-loc', text: where(result) }),
            el('span', { className: 'cp-desc', text: result.description }),
            // null, not undefined: a report from an older build has no such field.
            result.matched_device === null ? el('span', { className: 'cp-missing', text: 'Not found in your file' }) : null,
            el('span', { className: 'cp-pts', text: `-${pointsLost(result).toFixed(1)}` }),
            helpButton(result),
        ]);
        option.addEventListener('click', () => onSelect(result.rule_id, { push: true }));
        return option;
    }

    return {
        render({ groups, selectedId: id }) {
            selectedId = id;
            order = displayOrder(groups);
            box.textContent = '';
            let index = 0;
            groups.forEach((group, g) => {
                const labelId = `cp-group-${g}`;
                const items = group.items.map(r => row(r, index++));
                box.appendChild(el('li', { role: 'presentation', className: 'cp-group' }, [
                    el('div', { className: 'cp-group-label', id: labelId, text: group.label }),
                    el('ul', { role: 'group', 'aria-labelledby': labelId }, items),
                ]));
            });
            const current = order.findIndex(r => r.rule_id === selectedId);
            if (current >= 0) {
                box.setAttribute('aria-activedescendant', `cp-option-${current}`);
                const node = box.querySelector(`#cp-option-${current}`);
                if (node && node.scrollIntoView) node.scrollIntoView({ block: 'nearest' });
            } else {
                box.removeAttribute('aria-activedescendant');
            }
        },
        focus() { box.focus(); },
    };
}
