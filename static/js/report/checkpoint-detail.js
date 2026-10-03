// static/js/report/checkpoint-detail.js
// The selected checkpoint (spec 5.3): Expected, Found, Points lost, Why it
// matters, Check with, and Ask about this when the local model is available.
// Every value is set as text. Esc hands focus back to the list.
import { el } from '../core/dom.js';
import { icon } from '../core/icons.js';
import { pointsLost } from './checkpoints.js';

export function createCheckpointDetail(host, { onAsk, onBack }) {
    let current = null;
    let askAvailable = false;

    host.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') { e.preventDefault(); onBack(); }
    });

    function field(label, value, className) {
        if (value == null || value === '') return [];
        return [el('dt', { text: label }), el('dd', { className: className || null, text: value })];
    }

    function render() {
        host.textContent = '';
        if (!current) { host.hidden = true; return; }
        host.hidden = false;
        const r = current;
        const where = [r.target_device, r.target_interface].filter(Boolean).join(' ');
        const peer = r.peer_device ? [r.peer_device, r.peer_interface].filter(Boolean).join(' ') : '';
        const found = r.matched_device === null
            ? r.target_device + ' was not found in your file'
            : r.actual_value;

        host.appendChild(el('h2', { className: 'cpd-title', text: r.description }));
        host.appendChild(el('p', { className: 'cpd-where', text: peer ? where + ' to ' + peer : where }));
        host.appendChild(el('dl', { className: 'cpd-fields' }, [
            ...field('Expected', r.expected_text),
            ...field('Found', found, 'cpd-found'),
            ...field('Points lost', `${pointsLost(r).toFixed(1)} of ${Number(r.points_possible).toFixed(1)}`),
            ...field('Why it matters', r.guidance),
        ]));

        const commands = r.verify_commands || [];
        if (commands.length) {
            host.appendChild(el('div', { className: 'cpd-commands' }, [
                el('span', { className: 'cpd-label', text: 'Check with' }),
                ...commands.map(c => el('code', { className: 'cmd-chip', text: c })),
            ]));
        }
        if (askAvailable) {
            const ask = el('button', { type: 'button', className: 'btn btn-sm btn-outline cpd-ask' }, [icon('ai'), ' Ask about this']);
            ask.addEventListener('click', () => onAsk(r));
            host.appendChild(ask);
        }
    }

    return {
        show(result) { current = result; render(); },
        clear() { current = null; render(); },
        // The AI status is re-checked every minute; rebuilding the panel when
        // nothing changed would throw keyboard focus out of it.
        setAskAvailable(available) {
            if (askAvailable === !!available) return;
            askAvailable = !!available;
            render();
        },
        focus() { if (!host.hidden) host.focus(); },
    };
}
