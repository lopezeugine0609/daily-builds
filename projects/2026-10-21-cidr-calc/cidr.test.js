'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const c = require('./cidr.js');

test('parseIp / formatIp round trip and validation', () => {
  assert.equal(c.parseIp('192.168.1.10'), 3232235786);
  assert.equal(c.formatIp(c.parseIp('255.255.255.255')), '255.255.255.255');
  assert.equal(c.formatIp(0), '0.0.0.0');
  for (const bad of ['256.1.1.1', '1.2.3', '1.2.3.4.5', '01.2.3.4', 'a.b.c.d', '']) {
    assert.throws(() => c.parseIp(bad), /invalid IPv4/);
  }
});

test('parseCidr normalizes and strict mode rejects host bits', () => {
  const r = c.parseCidr('10.1.2.3/8');
  assert.equal(c.formatIp(r.network), '10.0.0.0');
  assert.equal(c.formatIp(r.broadcast), '10.255.255.255');
  assert.throws(() => c.parseCidr('10.1.2.3/8', true), /host bits/);
  assert.throws(() => c.parseCidr('10.0.0.0/33'), /prefix/);
  assert.equal(c.parseCidr('1.2.3.4').prefix, 32);
});

test('info for a /24', () => {
  const r = c.info('192.168.1.77/24');
  assert.equal(r.cidr, '192.168.1.0/24');
  assert.equal(r.netmask, '255.255.255.0');
  assert.equal(r.wildcard, '0.0.0.255');
  assert.equal(r.firstHost, '192.168.1.1');
  assert.equal(r.lastHost, '192.168.1.254');
  assert.equal(r.usableHosts, 254);
  assert.equal(r.type, 'private (RFC 1918)');
});

test('info edge prefixes /0, /31, /32', () => {
  const all = c.info('0.0.0.0/0');
  assert.equal(all.netmask, '0.0.0.0');
  assert.equal(all.totalAddresses, 4294967296);
  const p2p = c.info('10.0.0.0/31');
  assert.equal(p2p.usableHosts, 2);
  assert.equal(p2p.firstHost, '10.0.0.0');
  const host = c.info('8.8.8.8/32');
  assert.equal(host.usableHosts, 1);
  assert.equal(host.netmask, '255.255.255.255');
  assert.equal(host.type, 'public');
});

test('contains', () => {
  assert.equal(c.contains('10.0.0.0/8', '10.20.30.40'), true);
  assert.equal(c.contains('10.0.0.0/8', '11.0.0.1'), false);
  assert.equal(c.contains('10.0.0.0/8', '10.1.0.0/16'), true);
  assert.equal(c.contains('10.1.0.0/16', '10.0.0.0/8'), false);
});

test('split', () => {
  assert.deepEqual(c.split('192.168.0.0/24', 26), [
    '192.168.0.0/26', '192.168.0.64/26', '192.168.0.128/26', '192.168.0.192/26',
  ]);
  assert.throws(() => c.split('10.0.0.0/24', 16), /between/);
  assert.throws(() => c.split('10.0.0.0/8', 32), /refusing/);
});

test('rangeToCidrs produces minimal aligned blocks', () => {
  assert.deepEqual(c.rangeToCidrs(c.parseIp('10.0.0.1'), c.parseIp('10.0.0.6')),
    ['10.0.0.1/32', '10.0.0.2/31', '10.0.0.4/31', '10.0.0.6/32']);
  assert.deepEqual(c.rangeToCidrs(0, 2 ** 32 - 1), ['0.0.0.0/0']);
});

test('summarize merges adjacent and overlapping input', () => {
  assert.deepEqual(c.summarize(['10.0.0.0/25', '10.0.0.128/25']), ['10.0.0.0/24']);
  assert.deepEqual(c.summarize(['10.0.1.0/24', '10.0.0.0/24', '10.0.0.5']), ['10.0.0.0/23']);
  assert.deepEqual(c.summarize(['192.168.0.0-192.168.0.255', '192.168.2.0/24']),
    ['192.168.0.0/24', '192.168.2.0/24']);
});

test('main exit codes', () => {
  const log = console.log, err = console.error;
  console.log = () => {}; console.error = () => {};
  try {
    assert.equal(c.main(['contains', '10.0.0.0/8', '10.1.1.1']), 0);
    assert.equal(c.main(['contains', '10.0.0.0/8', '11.1.1.1']), 1);
    assert.equal(c.main(['info', 'nope']), 2);
    assert.equal(c.main([]), 2);
  } finally { console.log = log; console.error = err; }
});
