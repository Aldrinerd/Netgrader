// static/js/report/checkpoints.js
// The linked report's data rules, free of the DOM so they are unit tested:
// which checkpoints were missed, how they group and order, what is selected,
// and what the map should show. Fields added by the server in PR 3 may be
// absent from a report stored by an older build; every rule tolerates that.

export function missedOf(report) {
    return ((report && report.results) || []).filter(r => !r.passed);
}

export function pointsLost(result) {
    return Math.max(0, (result.points_possible || 0) - (result.points_earned || 0));
}

// Groups in first-appearance order, so the list follows the rubric.
export function groupMissed(missed, by) {
    const groups = new Map();
    for (const r of missed) {
        const key = by === 'topic' ? (r.topic || 'Other') : r.target_device;
        if (!groups.has(key)) groups.set(key, { key, label: key, items: [] });
        groups.get(key).items.push(r);
    }
    return Array.from(groups.values());
}

// What arrow keys walk through: the groups' items, in display order.
export function displayOrder(groups) {
    return groups.reduce((all, g) => all.concat(g.items), []);
}

export function badgesFor(missed) {
    const badges = {};
    for (const r of missed) {
        if (r.matched_device) badges[r.matched_device] = (badges[r.matched_device] || 0) + 1;
    }
    return badges;
}

// The map focus for the selected checkpoint (see map/highlight.js). A device
// missing from the attempt has nothing to highlight.
export function focusFor(result, badges) {
    if (!result || !result.matched_device) return { badges, devices: [], link: null };
    if (result.peer_device) {
        return { badges, devices: [result.matched_device, result.peer_device], link: [result.matched_device, result.peer_device] };
    }
    return { badges, devices: [result.matched_device], link: null };
}

// The requested checkpoint if it is still in the list, else the first.
export function resolveSelection(order, requestedId) {
    if (!order.length) return null;
    return order.find(r => r.rule_id === requestedId) || order[0];
}

// Next or previous in display order; listbox arrows stop at the ends.
export function step(order, currentId, delta) {
    const i = order.findIndex(r => r.rule_id === currentId);
    if (i < 0) return order[0] || null;
    return order[Math.max(0, Math.min(order.length - 1, i + delta))];
}

// Missed checkpoints touching one of the student's devices, as either end.
export function missedOnDevice(missed, hostname) {
    return missed.filter(r => r.matched_device === hostname || r.peer_device === hostname);
}

// The points-lost bar: each study topic's share of the points lost. Shades
// 1-5 step down in strength; topics past the fifth share the last shade.
export function lossSegments(studyTopics) {
    const topics = (studyTopics || []).filter(t => t.points_lost > 0);
    const total = topics.reduce((sum, t) => sum + t.points_lost, 0);
    return topics.map((t, i) => ({
        topic: t.topic,
        points: t.points_lost,
        share: total ? t.points_lost / total : 0,
        shade: Math.min(i, 4) + 1,
    }));
}

export function lossLabel(segments) {
    if (!segments.length) return 'No points lost';
    return 'Points lost by topic: ' + segments.map(s => `${s.topic}, ${s.points} points`).join('; ');
}
