'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { parse, check, main } = require('./env-check.js');

const vals = (text) => Object.fromEntries(parse(text).entries.map((e) => [e.key, e.value]));

test('parses basic, export, comments and inline comments', () => {
  const v = vals('# comment\n\nA=1\nexport B=two words # note\nC=x#y\n');
  assert.deepEqual(v, { A: '1', B: 'two words', C: 'x#y' });
});

test('single quotes are literal, double quotes process escapes', () => {
  const v = vals(`S='a\\nb $X'\nD="line1\\nline2 \\"q\\""\n`);
  assert.equal(v.S, 'a\\nb $X');
  assert.equal(v.D, 'line1\nline2 "q"');
});

test('double-quoted values may span lines', () => {
  const r = parse('KEY="-----BEGIN\nabc\n-----END"\nNEXT=1\n');
  assert.equal(r.entries[0].value, '-----BEGIN\nabc\n-----END');
  assert.equal(r.entries[1].key, 'NEXT');
  assert.equal(r.entries[1].line, 4);
  assert.equal(r.issues.length, 0);
});

test('handles CRLF and BOM', () => {
  assert.deepEqual(vals('\uFEFFA=1\r\nB=2\r\n'), { A: '1', B: '2' });
});

test('reports syntax and key issues', () => {
  const kinds = parse('NOEQUALS\n1BAD=x\nU="open\nA = b\n').issues.map((i) => i.kind);
  assert.deepEqual(kinds, ['syntax', 'invalid-key', 'syntax', 'spacing', 'spacing']);
});

test('trailing text after quoted value is flagged', () => {
  const r = parse('A="x" junk\nB="y" # ok\n');
  assert.equal(r.issues.length, 1);
  assert.equal(r.issues[0].key, 'A');
});

test('check finds duplicates, empties, missing and extra keys', () => {
  const p = check('A=1\nA=2\nB=\nX=9\n', 'A=\nB=\nC=\n');
  assert.deepEqual(p.map((x) => `${x.kind}:${x.key}`), [
    'duplicate:A', 'empty:B', 'extra:X', 'missing:C',
  ]);
});

test('allowEmpty and allowExtra suppress those checks', () => {
  const p = check('A=1\nB=\nX=9\n', 'A=\nB=\n', { allowEmpty: true, allowExtra: true });
  assert.deepEqual(p, []);
});

test('main: exit codes and output', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'envcheck-'));
  const env = path.join(dir, '.env');
  const ex = path.join(dir, '.env.example');
  fs.writeFileSync(env, 'A=1\n');
  fs.writeFileSync(ex, 'A=\nB=\n');
  const sink = () => { let s = ''; return { write: (c) => { s += c; }, get text() { return s; } }; };

  let out = sink();
  assert.equal(main([env, '-e', ex], out, sink()), 1);
  assert.match(out.text, /\[missing\] missing key "B"/);

  out = sink();
  assert.equal(main([env, '--no-example', '--json'], out, sink()), 0);
  assert.deepEqual(JSON.parse(out.text), []);

  const err = sink();
  assert.equal(main([path.join(dir, 'nope')], sink(), err), 2);
  assert.equal(main(['--bogus'], sink(), sink()), 2);
  fs.rmSync(dir, { recursive: true });
});
