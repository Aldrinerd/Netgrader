// tests/js/svg-shapes.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { shortInterfaceName } from '../../static/js/map/svg-shapes.js';

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
