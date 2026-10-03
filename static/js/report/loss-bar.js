// static/js/report/loss-bar.js
// Points lost by topic (spec 5.1): one bar, one segment per study topic, and a
// legend. The bar's accessible name lists every topic and its points.
import { el } from '../core/dom.js';
import { lossSegments, lossLabel } from './checkpoints.js';

export function buildLossBar(studyTopics) {
    const segments = lossSegments(studyTopics);
    if (!segments.length) return null;

    const bar = el('div', { className: 'loss-bar', role: 'img', 'aria-label': lossLabel(segments) });
    segments.forEach(s => {
        const seg = el('span', { className: `loss-seg loss-shade-${s.shade}` });
        seg.style.width = `${(s.share * 100).toFixed(2)}%`;
        bar.appendChild(seg);
    });

    const legend = el('ul', { className: 'loss-legend', 'aria-hidden': 'true' }, segments.map(s =>
        el('li', {}, [
            el('span', { className: `loss-swatch loss-shade-${s.shade}` }),
            el('span', { className: 'loss-topic', text: s.topic }),
            el('span', { className: 'loss-points', text: `-${s.points}` }),
        ])));

    return el('section', { className: 'loss-section' }, [
        el('h3', { className: 'report-subhead', text: 'Points lost by topic' }), bar, legend,
    ]);
}
