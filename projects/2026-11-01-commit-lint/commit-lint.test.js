'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { parse, lint, main } = require('./commit-lint.js');

const rules = (r) => r.errors.map((e) => e.rule);
const warns = (r) => r.warnings.map((e) => e.rule);

function capture(argv, stdinText = '', cwd = process.cwd()) {
  let out = '', err = '';
  const code = main(argv, {
    stdout: { write: (s) => { out += s; } },
    stderr: { write: (s) => { err += s; } },
    stdin: () => stdinText,
    cwd,
  });
  return { code, out, err };
}

test('parses full header, body and footers', () => {
  const p = parse('feat(api)!: drop v1 routes\n\nLong body here.\n\nBREAKING CHANGE: v1 is gone\nRefs: #12');
  assert.equal(p.type, 'feat');
  assert.equal(p.scope, 'api');
  assert.equal(p.bang, true);
  assert.equal(p.subject, 'drop v1 routes');
  assert.equal(p.body, 'Long body here.');
  assert.deepEqual(p.footers.map((f) => f.token), ['BREAKING CHANGE', 'Refs']);
  assert.equal(p.breaking, true);
});

test('valid simple message', () => {
  const r = lint('fix: handle null user');
  assert.equal(r.valid, true);
  assert.deepEqual(r.errors, []);
  assert.deepEqual(r.warnings, []);
});

test('git comment lines are ignored', () => {
  assert.equal(lint('docs: update readme\n# Please enter the commit message\n').valid, true);
});

test('bad format', () => {
  assert.deepEqual(rules(lint('updated stuff')), ['header-format']);
});

test('type enum and case', () => {
  assert.deepEqual(rules(lint('feature: add x')), ['type-enum']);
  assert.deepEqual(rules(lint('Feat: add x')), ['type-case']);
  assert.equal(lint('wip: x', { types: ['wip'] }).valid, true);
});

test('separator, empty subject, full stop', () => {
  assert.ok(rules(lint('feat:add x')).includes('header-separator'));
  assert.ok(rules(lint('feat:  add x')).includes('header-separator'));
  assert.ok(rules(lint('feat: ')).includes('subject-empty'));
  assert.deepEqual(rules(lint('feat: add x.')), ['subject-full-stop']);
});

test('scope rules', () => {
  assert.deepEqual(rules(lint('feat(): add x')), ['scope-empty']);
  assert.deepEqual(rules(lint('feat(db): add x', { scopes: ['api'] })), ['scope-enum']);
  assert.deepEqual(rules(lint('feat: add x', { requireScope: true })), ['scope-required']);
});

test('header max length', () => {
  const r = lint('feat: ' + 'a'.repeat(80));
  assert.deepEqual(rules(r), ['header-max-length']);
  assert.equal(lint('feat: ' + 'a'.repeat(80), { headerMax: 100 }).valid, true);
});

test('body needs leading blank line', () => {
  assert.deepEqual(rules(lint('feat: add x\nbody text')), ['body-leading-blank']);
});

test('breaking footer case', () => {
  assert.deepEqual(rules(lint('feat: add x\n\nbreaking change: oops')), ['footer-breaking-case']);
});

test('warnings: subject case, mood, bang without explanation', () => {
  assert.deepEqual(warns(lint('feat: Add x')), ['subject-case']);
  assert.deepEqual(warns(lint('fix: fixed crash')), ['subject-mood']);
  assert.deepEqual(warns(lint('feat!: drop x')), ['breaking-description']);
  assert.equal(lint('feat!: drop x').valid, true);
});

test('empty message', () => {
  assert.deepEqual(rules(lint('\n# only comment\n')), ['header-empty']);
});

test('CLI: arg, stdin, strict, json, exit codes', () => {
  assert.equal(capture(['feat: add x']).code, 0);
  assert.equal(capture([], 'nope').code, 1);
  assert.equal(capture(['feat: Add x']).code, 0);
  assert.equal(capture(['--strict', 'feat: Add x']).code, 1);
  const j = capture(['--json', 'feat(api): add x']);
  const data = JSON.parse(j.out);
  assert.equal(data.checked, 1);
  assert.equal(data.failed, 0);
  assert.equal(capture(['--bogus']).code, 2);
  assert.equal(capture(['--max', 'abc', 'x']).code, 2);
});

test('CLI: --file and --git range', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cl-'));
  const f = path.join(dir, 'MSG');
  fs.writeFileSync(f, 'chore: bump deps\n');
  assert.equal(capture(['-f', f]).code, 0);
  assert.equal(capture(['-f', path.join(dir, 'missing')]).code, 2);

  const git = (...a) => execFileSync('git', a, { cwd: dir, encoding: 'utf8' });
  git('init', '-q');
  git('config', 'user.email', 't@t');
  git('config', 'user.name', 't');
  git('commit', '-q', '--allow-empty', '-m', 'feat: first');
  git('commit', '-q', '--allow-empty', '-m', 'bad message');
  git('commit', '-q', '--allow-empty', '-m', 'fix(core): second');
  const r = capture(['--json', '--git', 'HEAD'], '', dir);
  const data = JSON.parse(r.out);
  assert.equal(r.code, 1);
  assert.equal(data.checked, 3);
  assert.equal(data.failed, 1);
  assert.equal(data.results.find((x) => !x.valid).header, 'bad message');
  fs.rmSync(dir, { recursive: true, force: true });
});
