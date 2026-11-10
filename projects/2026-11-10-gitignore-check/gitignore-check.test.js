'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { parseIgnoreFile, isIgnored, walkIgnored, run } = require('./gitignore-check.js');

const R = (text) => parseIgnoreFile(text);
const ign = (text, p, isDir = false) => isIgnored(R(text), p, isDir).ignored;

function sink() {
  let s = '';
  return { write: (x) => { s += x; }, get text() { return s; } };
}

test('parsing skips blanks and comments, keeps line numbers', () => {
  const rules = R('# comment\n\n*.log\n  \n!keep.log\n');
  assert.equal(rules.length, 2);
  assert.equal(rules[0].line, 3);
  assert.equal(rules[1].line, 5);
  assert.equal(rules[1].negated, true);
});

test('escaped # and ! are literal, trailing spaces trimmed unless escaped', () => {
  assert.equal(ign('\\#notes', '#notes'), true);
  assert.equal(ign('\\!bang', '!bang'), true);
  assert.equal(ign('foo   ', 'foo'), true);
  assert.equal(ign('bar\\ ', 'bar '), true);
});

test('CRLF and BOM are handled', () => {
  assert.equal(ign('\uFEFF*.tmp\r\n', 'a.tmp'), true);
});

test('pattern without slash matches basename at any depth', () => {
  assert.equal(ign('*.log', 'a.log'), true);
  assert.equal(ign('*.log', 'x/y/z/a.log'), true);
  assert.equal(ign('*.log', 'a.txt'), false);
});

test('pattern with a middle slash is anchored to the root', () => {
  assert.equal(ign('/build', 'build'), true);
  assert.equal(ign('/build', 'src/build'), false);
  assert.equal(ign('doc/*.txt', 'doc/a.txt'), true);
  assert.equal(ign('doc/*.txt', 'doc/x/a.txt'), false);
});

test('* and ? never cross a slash', () => {
  assert.equal(ign('a?c', 'abc'), true);
  assert.equal(ign('a?c', 'a/c'), false);
  assert.equal(ign('a*d', 'a/b/d'), false);
});

test('leading **/ matches at any depth, trailing /** matches contents only', () => {
  assert.equal(ign('**/foo', 'foo'), true);
  assert.equal(ign('**/foo', 'a/b/foo'), true);
  assert.equal(ign('a/**', 'a/x'), true);
  assert.equal(ign('a/**', 'a/b/c'), true);
  assert.equal(ign('a/**', 'a'), false);
});

test('a/**/b matches zero or more directories in between', () => {
  assert.equal(ign('a/**/b', 'a/b'), true);
  assert.equal(ign('a/**/b', 'a/x/y/b'), true);
  assert.equal(ign('a/**/b', 'a/x/c'), false);
});

test('dir-only pattern (trailing slash) matches directories, not files', () => {
  assert.equal(ign('logs/', 'logs', true), true);
  assert.equal(ign('logs/', 'logs', false), false);
});

test('files inside an ignored directory are ignored, and report the via dir', () => {
  const r = isIgnored(R('node_modules/'), 'node_modules/left-pad/index.js', false);
  assert.equal(r.ignored, true);
  assert.equal(r.via, 'node_modules');
});

test('negation re-includes a file that an earlier rule ignored', () => {
  const text = '*.log\n!keep.log\n';
  assert.equal(ign(text, 'other.log'), true);
  assert.equal(ign(text, 'keep.log'), false);
});

test('last matching rule wins (order matters)', () => {
  assert.equal(ign('!a.log\na.log', 'a.log'), true);
  assert.equal(ign('a.log\n!a.log', 'a.log'), false);
});

test('cannot re-include a file when its parent directory is ignored', () => {
  assert.equal(ign('build/\n!build/keep.txt', 'build/keep.txt'), true);
});

test('negated directory re-includes its contents after a wildcard exclude', () => {
  const text = '/*\n!/src\n';
  assert.equal(ign(text, 'src/app.js'), false);
  assert.equal(ign(text, 'tmp/x.js'), true);
});

test('character classes and negated classes', () => {
  assert.equal(ign('file[0-9].txt', 'file7.txt'), true);
  assert.equal(ign('file[0-9].txt', 'filex.txt'), false);
  assert.equal(ign('[!a]x', 'bx'), true);
  assert.equal(ign('[!a]x', 'ax'), false);
});

test('walkIgnored lists topmost ignored entries and never descends into them', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gic-'));
  fs.mkdirSync(path.join(dir, 'node_modules', 'pkg'), { recursive: true });
  fs.mkdirSync(path.join(dir, 'src', 'build'), { recursive: true });
  fs.mkdirSync(path.join(dir, '.git'));
  fs.writeFileSync(path.join(dir, 'node_modules', 'pkg', 'i.js'), '');
  fs.writeFileSync(path.join(dir, 'src', 'app.log'), '');
  fs.writeFileSync(path.join(dir, 'src', 'app.js'), '');
  fs.writeFileSync(path.join(dir, 'src', 'build', 'o.js'), '');
  const found = walkIgnored(dir, R('node_modules/\n*.log\nbuild/\n'));
  assert.deepEqual(found.map((e) => e.path).sort(), ['node_modules/', 'src/app.log', 'src/build/']);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('CLI exit codes: 0 all kept, 1 some ignored, 2 usage error', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gic-cli-'));
  fs.writeFileSync(path.join(dir, '.gitignore'), '*.log\n');
  fs.writeFileSync(path.join(dir, 'a.txt'), '');
  fs.writeFileSync(path.join(dir, 'a.log'), '');
  const o1 = sink(); const e1 = sink();
  assert.equal(run(['--root', dir, 'a.txt'], o1, e1), 0);
  assert.match(o1.text, /^kept\s+a\.txt\n$/);
  const o2 = sink();
  assert.equal(run(['--root', dir, 'a.txt', 'a.log'], o2, e1), 1);
  assert.match(o2.text, /IGNORED {2}a\.log {2}\(\.gitignore:1 '\*\.log'\)/);
  assert.equal(run(['--root', dir, '--bogus', 'a.txt'], sink(), sink()), 2);
  assert.equal(run(['--root', dir], sink(), sink()), 2);
  assert.equal(run(['--root', dir, '../x'], sink(), sink()), 2);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('CLI --json output shape', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gic-json-'));
  fs.writeFileSync(path.join(dir, '.gitignore'), 'dist/\n');
  const o = sink();
  run(['--root', dir, '--json', 'dist/', 'src/a.js'], o, sink());
  const data = JSON.parse(o.text);
  assert.deepEqual(data[0], { path: 'dist/', ignored: true, via: null, rule: { source: '.gitignore', line: 1, pattern: 'dist/' } });
  assert.deepEqual(data[1], { path: 'src/a.js', ignored: false, via: null, rule: null });
  fs.rmSync(dir, { recursive: true, force: true });
});
