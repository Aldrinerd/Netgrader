// tests/js/report-components.test.mjs
// The linked report's DOM components, on the fake DOM in fake-dom.mjs.
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { installFakeDocument } from './fake-dom.mjs';
import { createCheckpointDetail } from '../../static/js/report/checkpoint-detail.js';
import { createLinkedReport } from '../../static/js/report/linked-report.js';

let doc;
beforeEach(() => { doc = installFakeDocument(); });
afterEach(() => { delete globalThis.document; });

const missed = (id, over = {}) => ({
    rule_id: id, passed: false, points_possible: 10, points_earned: 0, description: `check ${id}`,
    target_device: 'R1', target_interface: 'G0/0', topic: 'Cabling', matched_device: 'R1',
    peer_device: null, verify_commands: ['show cdp neighbors'], ...over,
});

test('the AI status poll does not rebuild the detail, so keyboard focus stays put', () => {
    const host = doc.createElement('section');
    const detail = createCheckpointDetail(host, { onAsk() {}, onBack() {} });
    detail.setAskAvailable(true);
    detail.show(missed('a'));
    const ask = host.querySelector('.cpd-ask');
    ask.focus();

    detail.setAskAvailable(true);        // the 60-second refresh, nothing changed

    assert.equal(host.querySelector('.cpd-ask'), ask);
    assert.equal(ask.parentNode, host);
    assert.equal(doc.activeElement, ask);
});

test('Ask about this still appears and disappears with the model', () => {
    const host = doc.createElement('section');
    const detail = createCheckpointDetail(host, { onAsk() {}, onBack() {} });
    detail.show(missed('a'));
    assert.equal(host.querySelector('.cpd-ask'), null);
    detail.setAskAvailable(true);
    assert.ok(host.querySelector('.cpd-ask'));
    detail.setAskAvailable(false);
    assert.equal(host.querySelector('.cpd-ask'), null);
});

test('the group toggle keeps keyboard focus on the pressed button', () => {
    const listHost = doc.createElement('div');
    const detailHost = doc.createElement('section');
    const report = createLinkedReport({ listHost, detailHost, map: { setFocus() {} } });
    report.show({
        percentage: 80, total_score: 80, max_score: 100, grade_letter: 'B', lab_title: 'Lab',
        study_topics: [], results: [missed('a'), missed('b', { target_device: 'R2', matched_device: 'R2', topic: 'Routing' })],
    });

    listHost.querySelector('.lr-group-toggle [aria-pressed="false"]').click();

    const pressed = listHost.querySelector('.lr-group-toggle [aria-pressed="true"]');
    assert.equal(pressed.textContent, 'Topic');
    assert.equal(doc.activeElement, pressed);
});
