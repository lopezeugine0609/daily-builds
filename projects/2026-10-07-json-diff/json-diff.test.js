'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { diff, formatText, parseArgs, main, joinPath } = require('./json-diff.js');

test('identical values produce no changes', () => {
  assert.deepEqual(diff({ a: [1, { b: null }] }, { a: [1, { b: null }] }), []);
});

test('detects added, removed and changed keys', () => {
  const changes = diff({ a: 1, b: 2 }, { b: 3, c: 4 });
  assert.deepEqual(changes, [
    { op: 'remove', path: '$.a', from: 1 },
    { op: 'change', path: '$.b', from: 2, to: 3 },
    { op: 'add', path: '$.c', to: 4 },
  ]);
});

test('nested arrays and objects', () => {
  const changes = diff({ x: [1, 2, 3] }, { x: [1, 5] });
  assert.deepEqual(changes, [
    { op: 'change', path: '$.x[1]', from: 2, to: 5 },
    { op: 'remove', path: '$.x[2]', from: 3 },
  ]);
});

test('type change is reported once, not recursed', () => {
  const changes = diff({ a: { b: 1 } }, { a: [1] });
  assert.deepEqual(changes, [{ op: 'change', path: '$.a', from: { b: 1 }, to: [1] }]);
});

test('null vs object is a type change', () => {
  assert.equal(diff(null, {}).length, 1);
});

test('ignore skips subtrees', () => {
  const a = { meta: { t: 1 }, v: 1 };
  const b = { meta: { t: 2 }, v: 1 };
  assert.deepEqual(diff(a, b, { ignore: ['$.meta'] }), []);
});

test('epsilon tolerates small numeric differences', () => {
  assert.deepEqual(diff({ p: 1.0 }, { p: 1.0004 }, { epsilon: 0.001 }), []);
  assert.equal(diff({ p: 1.0 }, { p: 1.01 }, { epsilon: 0.001 }).length, 1);
});

test('joinPath quotes non-identifier keys', () => {
  assert.equal(joinPath('$', 'ok_key'), '$.ok_key');
  assert.equal(joinPath('$', 'has space'), '$["has space"]');
  assert.equal(joinPath('$', 3), '$[3]');
});

test('formatText summary', () => {
  const out = formatText(diff({ a: 1 }, { a: 2, b: true }));
  assert.match(out, /~ \$\.a: 1 -> 2/);
  assert.match(out, /\+ \$\.b: true/);
  assert.match(out, /1 added, 0 removed, 1 changed/);
  assert.equal(formatText([]), 'No differences.');
});

test('parseArgs rejects bad options', () => {
  assert.throws(() => parseArgs(['--epsilon', 'x']));
  assert.throws(() => parseArgs(['--nope']));
  const o = parseArgs(['a', 'b', '--ignore', '$.x', '--json']);
  assert.deepEqual(o.files, ['a', 'b']);
  assert.deepEqual(o.ignore, ['$.x']);
  assert.equal(o.json, true);
});

function sink() {
  const s = { data: '', write(x) { s.data += x; } };
  return s;
}

test('main exit codes and file handling', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'jd-'));
  const f1 = path.join(dir, 'a.json');
  const f2 = path.join(dir, 'b.json');
  const bad = path.join(dir, 'bad.json');
  fs.writeFileSync(f1, '{"a":1}');
  fs.writeFileSync(f2, '{"a":2}');
  fs.writeFileSync(bad, '{oops');

  assert.equal(main([f1, f1], sink(), sink()), 0);
  const out = sink();
  assert.equal(main([f1, f2, '--json'], out, sink()), 1);
  assert.deepEqual(JSON.parse(out.data), [{ op: 'change', path: '$.a', from: 1, to: 2 }]);
  const err = sink();
  assert.equal(main([f1, bad], sink(), err), 2);
  assert.match(err.data, /invalid JSON/);
  assert.equal(main([f1], sink(), sink()), 2);
  fs.rmSync(dir, { recursive: true, force: true });
});
