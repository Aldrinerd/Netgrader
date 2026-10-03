// static/js/map/highlight.js
// What the map emphasises for the linked report: a count badge on each device
// with missed checkpoints, and for the selected checkpoint its device -- or,
// for a link-scoped check, the link and both ends -- while the rest dims.
// Pure functions over plain data, so they are tested without a browser.
//
// focus = { badges: { [hostname]: count }, devices: [hostname], link: [a, b] | null }

export const NO_FOCUS = Object.freeze({ badges: Object.freeze({}), devices: Object.freeze([]), link: null });

export function linkJoins(link, a, b) {
    return (link.source_device === a && link.target_device === b)
        || (link.source_device === b && link.target_device === a);
}

// 'focus' = part of the selection, 'dim' = something else is selected,
// 'none' = nothing is selected.
export function nodeEmphasis(hostname, focus) {
    if (!focus.devices.length) return 'none';
    return focus.devices.indexOf(hostname) >= 0 ? 'focus' : 'dim';
}

export function linkEmphasis(link, focus) {
    if (!focus.devices.length) return 'none';
    if (focus.link && linkJoins(link, focus.link[0], focus.link[1])) return 'focus';
    return 'dim';
}

export function badgeCount(hostname, focus) {
    const n = focus.badges[hostname];
    return Number.isInteger(n) && n > 0 ? n : 0;
}
