// tests/js/svg-shapes.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { shortInterfaceName, paint } from '../../static/js/map/svg-shapes.js';

test('shortens the interface families shown on the map', () => {
    assert.equal(shortInterfaceName('GigabitEthernet0/1'), 'Gi0/1');
    assert.equal(shortInterfaceName('FastEthernet0'), 'Fa0');
    assert.equal(shortInterfaceName('Serial0/0/0'), 'Se0/0/0');
    assert.equal(shortInterfaceName('Port-channel1'), 'Po1');
    assert.equal(shortInterfaceName('Vlan10'), 'Vl10');
});

test('hides unknown or unspecified ports', () => {
    assert.equal(shortInterfaceName(''), '');
    assert.equal(shortInterfaceName(null), '');
    assert.equal(shortInterfaceName('Unspecified'), '');
});

test('paint sets CSS properties so var() tokens work on SVG', () => {
    const calls = [];
    const el = { style: { setProperty: (k, v) => calls.push([k, v]) } };
    assert.equal(paint(el, { fill: 'var(--map-router)', strokeWidth: '2', fillOpacity: '0.15' }), el);
    assert.deepEqual(calls, [['fill', 'var(--map-router)'], ['stroke-width', '2'], ['fill-opacity', '0.15']]);
});
