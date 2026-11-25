'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const e = require('./epoch.js');

const NOW = 1764000000000000000n; // 2025-11-24T16:00:00Z in ns

test('detects epoch unit by magnitude', () => {
  assert.equal(e.parseTime('1700000000'), 1700000000000000000n);
  assert.equal(e.parseTime('1700000000123'), 1700000000123000000n);
  assert.equal(e.parseTime('1700000000123456'), 1700000000123456000n);
  assert.equal(e.parseTime('1700000000123456789'), 1700000000123456789n);
});

test('forced unit and fractional seconds', () => {
  assert.equal(e.parseTime('5', { unit: 'ms' }), 5000000n);
  assert.equal(e.parseTime('1700000000.5'), 1700000000500000000n);
  assert.equal(e.parseTime('-1.5', { unit: 's' }), -1500000000n);
});

test('parses ISO with offsets and fractions', () => {
  assert.equal(e.parseTime('1970-01-01T00:00:00Z'), 0n);
  assert.equal(e.parseTime('1970-01-01T08:00:00+08:00'), 0n);
  assert.equal(e.parseTime('1970-01-01T00:00:00.000000001Z'), 1n);
  assert.equal(e.parseTime('2000-01-01'), 946684800000000000n);
  assert.equal(e.parseTime('1969-12-31T19:00:00-0500'), 0n);
});

test('rejects invalid dates and garbage', () => {
  assert.throws(() => e.parseTime('2023-02-30'), /invalid date/);
  assert.throws(() => e.parseTime('2023-01-01T25:00'), /invalid date/);
  assert.throws(() => e.parseTime('yesterday'), /unrecognised/);
  assert.throws(() => e.parseDuration('3 hours'), /invalid duration/);
  assert.throws(() => e.parseOffset('+25:00'), /invalid offset/);
});

test('relative inputs', () => {
  assert.equal(e.parseTime('now', { now: NOW }), NOW);
  assert.equal(e.parseTime('now-1h30m', { now: NOW }), NOW - 5400000000000n);
  assert.equal(e.parseTime('+2d', { now: NOW }), NOW + 172800000000000n);
});

test('formatIso round-trips and handles offsets / negatives', () => {
  assert.equal(e.formatIso(0n), '1970-01-01T00:00:00Z');
  assert.equal(e.formatIso(1n), '1970-01-01T00:00:00.000000001Z');
  assert.equal(e.formatIso(-1n), '1969-12-31T23:59:59.999999999Z');
  assert.equal(e.formatIso(0n, 480), '1970-01-01T08:00:00+08:00');
  assert.equal(e.formatIso(0n, -330), '1969-12-31T18:30:00-05:30');
  const iso = '2026-11-25T09:15:30.123456789+08:00';
  assert.equal(e.formatIso(e.parseTime(iso), 480), iso);
});

test('durations and relative phrases', () => {
  assert.equal(e.formatDuration(0n), '0s');
  assert.equal(e.formatDuration(93784005000000n), '1d 2h 3m 4s 5ms');
  assert.equal(e.formatDuration(-60000000000n), '-1m');
  assert.equal(e.formatDuration(42n), '42ns');
  assert.equal(e.formatRelative(NOW - 3n * 3600000000000n, NOW), '3 hours ago');
  assert.equal(e.formatRelative(NOW + 86400000000000n, NOW), 'in 1 day');
  assert.equal(e.formatRelative(NOW, NOW), 'just now');
});

test('convert and diff', () => {
  const r = e.convert('0', { now: NOW, unit: 's', offset: 480 });
  assert.equal(r.utc, '1970-01-01T00:00:00Z');
  assert.equal(r.local, '1970-01-01T08:00:00+08:00');
  assert.equal(r.relative, '55 years ago');
  const d = e.diff('2026-01-01', '2026-03-01T12:00Z');
  assert.equal(d.human, '59d 12h');
  assert.equal(d.s, String(59 * 86400 + 43200));
});

test('CLI exit codes and JSON', () => {
  const lines = []; const errs = [];
  const out = (s) => lines.push(s); const err = (s) => errs.push(s);
  assert.equal(e.main(['--json', '0', '--unit', 's'], out, err), 0);
  assert.equal(JSON.parse(lines[0])[0].utc, '1970-01-01T00:00:00Z');
  assert.equal(e.main(['bogus'], out, err), 1);
  assert.equal(e.main(['--unit', 'yr', '1'], out, err), 2);
  assert.equal(e.main(['--diff', 'now'], out, err), 2);
});
