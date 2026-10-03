// tests/js/checkpoints.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
    missedOf, pointsLost, groupMissed, displayOrder, badgesFor, focusFor,
    resolveSelection, step, missedOnDevice, lossSegments, lossLabel,
} from '../../static/js/report/checkpoints.js';

const r = (id, over = {}) => ({
    rule_id: id, passed: false, points_possible: 10, points_earned: 0,
    target_device: 'R1', target_interface: null, topic: 'Cabling',
    matched_device: 'R1', peer_device: null, ...over,
});

const report = {
    results: [
        r('a'),
        r('b', { passed: true, points_earned: 10 }),
        r('c', { target_device: 'R2', matched_device: 'R2', topic: 'Routing' }),
        r('d', { topic: 'Routing', points_earned: 4 }),
        r('e', { target_device: 'R3', matched_device: null }),
    ],
};

test('missed checkpoints are the failed ones, in rubric order', () => {
    assert.deepEqual(missedOf(report).map(x => x.rule_id), ['a', 'c', 'd', 'e']);
    assert.deepEqual(missedOf({}), []);
});

test('points lost never goes negative', () => {
    assert.equal(pointsLost(r('x', { points_earned: 4 })), 6);
    assert.equal(pointsLost(r('x', { points_earned: 12 })), 0);
});

test('grouping by device keeps first-appearance order', () => {
    const groups = groupMissed(missedOf(report), 'device');
    assert.deepEqual(groups.map(g => g.label), ['R1', 'R2', 'R3']);
    assert.deepEqual(displayOrder(groups).map(x => x.rule_id), ['a', 'd', 'c', 'e']);
});

test('grouping by topic uses the server label, with a fallback', () => {
    const missed = [...missedOf(report), r('f', { topic: null })];
    const groups = groupMissed(missed, 'topic');
    assert.deepEqual(groups.map(g => g.label), ['Cabling', 'Routing', 'Other']);
});

test('badges count missed checkpoints on devices that exist', () => {
    assert.deepEqual(badgesFor(missedOf(report)), { R1: 2, R2: 1 });
});

test('focus: device check, link check, missing device, nothing selected', () => {
    const badges = { R1: 1 };
    assert.deepEqual(focusFor(r('a'), badges), { badges, devices: ['R1'], link: null });
    assert.deepEqual(focusFor(r('l', { peer_device: 'R2' }), badges), { badges, devices: ['R1', 'R2'], link: ['R1', 'R2'] });
    assert.deepEqual(focusFor(r('m', { matched_device: null }), badges), { badges, devices: [], link: null });
    assert.deepEqual(focusFor(null, badges), { badges, devices: [], link: null });
});

test('a report without the new fields renders with no focus and no badges', () => {
    const old = { rule_id: 'x', passed: false, points_possible: 5, points_earned: 0, target_device: 'R1' };
    assert.deepEqual(badgesFor([old]), {});
    assert.deepEqual(focusFor(old, {}), { badges: {}, devices: [], link: null });
    assert.deepEqual(groupMissed([old], 'topic').map(g => g.label), ['Other']);
});

test('selection falls back to the first missed checkpoint', () => {
    const order = displayOrder(groupMissed(missedOf(report), 'device'));
    assert.equal(resolveSelection(order, 'c').rule_id, 'c');
    assert.equal(resolveSelection(order, 'b').rule_id, 'a');        // passed after Grade again
    assert.equal(resolveSelection(order, null).rule_id, 'a');
    assert.equal(resolveSelection([], 'a'), null);
});

test('arrow steps clamp at both ends', () => {
    const order = displayOrder(groupMissed(missedOf(report), 'device'));
    assert.equal(step(order, 'a', -1).rule_id, 'a');
    assert.equal(step(order, 'a', 1).rule_id, 'd');
    assert.equal(step(order, 'e', 1).rule_id, 'e');
    assert.equal(step(order, 'zzz', 1).rule_id, 'a');
});

test('missed on a device includes checks where it is the peer', () => {
    const missed = [r('a'), r('l', { matched_device: 'R2', peer_device: 'R1' }), r('c', { matched_device: 'R2' })];
    assert.deepEqual(missedOnDevice(missed, 'R1').map(x => x.rule_id), ['a', 'l']);
    assert.deepEqual(missedOnDevice(missed, 'R9'), []);
});

test('loss segments share the total and cap the shade at 5', () => {
    const topics = [
        { topic: 'A', points_lost: 6 }, { topic: 'B', points_lost: 2 }, { topic: 'Z', points_lost: 0 },
        { topic: 'C', points_lost: 1 }, { topic: 'D', points_lost: 0.5 }, { topic: 'E', points_lost: 0.25 }, { topic: 'F', points_lost: 0.25 },
    ];
    const segs = lossSegments(topics);
    assert.deepEqual(segs.map(s => s.topic), ['A', 'B', 'C', 'D', 'E', 'F']);
    assert.equal(segs[0].share, 0.6);
    assert.deepEqual(segs.map(s => s.shade), [1, 2, 3, 4, 5, 5]);
    assert.equal(lossLabel(segs.slice(0, 2)), 'Points lost by topic: A, 6 points; B, 2 points');
    assert.deepEqual(lossSegments(undefined), []);
    assert.equal(lossLabel([]), 'No points lost');
});
