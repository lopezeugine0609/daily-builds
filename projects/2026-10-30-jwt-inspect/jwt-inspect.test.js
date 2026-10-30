'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { decode, sign, verify, timeStatus, fmtDuration, run } = require('./jwt-inspect.js');

// Well-known example token from jwt.io (HS256, secret "your-256-bit-secret").
const JWTIO = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';

function cap(argv, stdin = '') {
  const out = [], err = [];
  const code = run(argv, { out: (s) => out.push(s), err: (s) => err.push(s), stdin: () => stdin });
  return { code, out: out.join('\n'), err: err.join('\n') };
}

test('decodes jwt.io example', () => {
  const d = decode(JWTIO);
  assert.deepStrictEqual(d.header, { alg: 'HS256', typ: 'JWT' });
  assert.strictEqual(d.payload.name, 'John Doe');
});

test('verifies jwt.io example with its known secret', () => {
  assert.strictEqual(verify(decode(JWTIO), 'your-256-bit-secret').ok, true);
  assert.strictEqual(verify(decode(JWTIO), 'wrong').ok, false);
});

test('strips Bearer prefix and whitespace', () => {
  assert.strictEqual(decode(`  Bearer ${JWTIO}\n`).payload.sub, '1234567890');
});

test('sign/verify roundtrip for all HMAC algs', () => {
  for (const alg of ['HS256', 'HS384', 'HS512']) {
    const t = sign({ alg }, { a: 1 }, 's3cret');
    const d = decode(t);
    assert.strictEqual(d.header.alg, alg);
    assert.ok(verify(d, 's3cret').ok);
  }
});

test('tampered payload fails verification', () => {
  const [h, , s] = sign({ alg: 'HS256' }, { admin: false }, 'k').split('.');
  const evil = Buffer.from('{"admin":true}').toString('base64url');
  assert.strictEqual(verify(decode(`${h}.${evil}.${s}`), 'k').ok, false);
});

test('alg none is refused', () => {
  const h = Buffer.from('{"alg":"none"}').toString('base64url');
  const p = Buffer.from('{}').toString('base64url');
  const r = verify(decode(`${h}.${p}.`), 'k');
  assert.strictEqual(r.ok, false);
  assert.match(r.reason, /none/);
});

test('malformed tokens throw clear errors', () => {
  assert.throws(() => decode('abc'), /3 dot-separated parts/);
  assert.throws(() => decode('a+b.c.d'), /header: segment is not base64url/);
  const notJson = Buffer.from('hello').toString('base64url');
  assert.throws(() => decode(`${notJson}.${notJson}.`), /header: not valid JSON/);
  const arr = Buffer.from('[1]').toString('base64url');
  assert.throws(() => decode(`${arr}.${arr}.`), /must be a JSON object/);
});

test('timeStatus: expired, not-yet-valid, valid, leeway', () => {
  assert.strictEqual(timeStatus({ exp: 100 }, 100).status, 'expired');
  assert.strictEqual(timeStatus({ exp: 100 }, 99).status, 'valid');
  assert.strictEqual(timeStatus({ exp: 100 }, 105, 10).status, 'valid');
  assert.strictEqual(timeStatus({ nbf: 200, exp: 300 }, 150).status, 'not-yet-valid');
  assert.match(timeStatus({}, 0).notes.join(), /no exp claim/);
});

test('fmtDuration', () => {
  assert.strictEqual(fmtDuration(0), '0s');
  assert.strictEqual(fmtDuration(90061), '1d 1h 1m 1s');
  assert.strictEqual(fmtDuration(-3600), '1h');
});

test('CLI exit codes', () => {
  assert.strictEqual(cap([JWTIO, '--now', '1516239100']).code, 0);
  assert.strictEqual(cap([JWTIO, '--secret', 'bad']).code, 1);
  const t = sign({ alg: 'HS256' }, { exp: 1000 }, 'k');
  assert.strictEqual(cap([t, '--now', '2000']).code, 1);
  assert.strictEqual(cap(['nope']).code, 2);
  assert.strictEqual(cap(['--secret']).code, 2);
});

test('CLI reads stdin and emits JSON', () => {
  const r = cap(['-', '--json', '--secret', 'your-256-bit-secret', '--now', '1516239100'], JWTIO + '\n');
  assert.strictEqual(r.code, 0);
  const j = JSON.parse(r.out);
  assert.strictEqual(j.signature, true);
  assert.strictEqual(j.time, 'valid');
});

test('CLI sign subcommand produces verifiable token', () => {
  const r = cap(['sign', '{"sub":"x"}', '--secret', 'k', '--alg', 'HS512']);
  assert.strictEqual(r.code, 0);
  const d = decode(r.out);
  assert.strictEqual(d.header.alg, 'HS512');
  assert.ok(verify(d, 'k').ok);
});
