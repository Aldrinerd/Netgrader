// tests/js/highlight.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { NO_FOCUS, linkJoins, nodeEmphasis, linkEmphasis, badgeCount } from '../../static/js/map/highlight.js';

const link = { source_device: 'R1', target_device: 'R2' };

test('a link joins its two devices in either direction', () => {
    assert.equal(linkJoins(link, 'R1', 'R2'), true);
    assert.equal(linkJoins(link, 'R2', 'R1'), true);
    assert.equal(linkJoins(link, 'R1', 'R3'), false);
});

test('with nothing selected, nothing is emphasised or dimmed', () => {
    assert.equal(nodeEmphasis('R1', NO_FOCUS), 'none');
    assert.equal(linkEmphasis(link, NO_FOCUS), 'none');
});

test('a device checkpoint focuses its device and dims the rest, links included', () => {
    const focus = { badges: {}, devices: ['R1'], link: null };
    assert.equal(nodeEmphasis('R1', focus), 'focus');
    assert.equal(nodeEmphasis('R2', focus), 'dim');
    assert.equal(linkEmphasis(link, focus), 'dim');
});

test('a link checkpoint focuses both ends and the link between them', () => {
    const focus = { badges: {}, devices: ['R2', 'R1'], link: ['R2', 'R1'] };
    assert.equal(nodeEmphasis('R1', focus), 'focus');
    assert.equal(nodeEmphasis('R2', focus), 'focus');
    assert.equal(linkEmphasis(link, focus), 'focus');
    assert.equal(linkEmphasis({ source_device: 'R2', target_device: 'R3' }, focus), 'dim');
});

test('badge counts are positive integers or zero', () => {
    const focus = { badges: { R1: 3, R2: 0, R3: 'x' }, devices: [], link: null };
    assert.equal(badgeCount('R1', focus), 3);
    assert.equal(badgeCount('R2', focus), 0);
    assert.equal(badgeCount('R3', focus), 0);
    assert.equal(badgeCount('R9', focus), 0);
});
