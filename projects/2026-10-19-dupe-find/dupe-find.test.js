'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { findDuplicates, humanSize, parseSize, parseArgs, main, hashFile } = require('./dupe-find.js');

function fixture(files) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dupe-find-'));
  for (const [rel, content] of Object.entries(files)) {
    const p = path.join(dir, rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content);
  }
  return dir;
}

function sink() {
  const s = { data: '', write(x) { s.data += x; } };
  return s;
}

test('finds duplicate groups across subdirectories', () => {
  const d = fixture({ 'a.txt': 'hello', 'sub/b.txt': 'hello', 'c.txt': 'world', 'd.txt': 'hellp' });
  const r = findDuplicates([d]);
  assert.equal(r.groups.length, 1);
  assert.deepEqual(r.groups[0].paths.map((p) => path.relative(d, p)).sort(), ['a.txt', path.join('sub', 'b.txt')]);
  assert.equal(r.wasted, 5);
  assert.equal(r.stats.scanned, 4);
});

test('same size and same first 4 KiB but different tail are not duplicates', () => {
  const head = 'x'.repeat(5000);
  const d = fixture({ 'a': head + 'A', 'b': head + 'B', 'c': head + 'A' });
  const r = findDuplicates([d]);
  assert.equal(r.groups.length, 1);
  assert.equal(r.groups[0].paths.length, 2);
  assert.equal(r.stats.partialHashed, 3);
});

test('partial hash prunes files that differ early', () => {
  const d = fixture({ 'a': 'A' + 'x'.repeat(5000), 'b': 'B' + 'x'.repeat(5000) });
  const r = findDuplicates([d]);
  assert.equal(r.groups.length, 0);
  assert.equal(r.stats.partialHashed, 2);
  assert.equal(r.stats.fullHashed, 0);
});

test('empty files skipped by default, included with minSize 0', () => {
  const d = fixture({ 'e1': '', 'e2': '' });
  assert.equal(findDuplicates([d]).groups.length, 0);
  assert.equal(findDuplicates([d], { minSize: 0 }).groups.length, 1);
});

test('ignores .git and node_modules by default', () => {
  const d = fixture({ 'a': 'same', '.git/x': 'same', 'node_modules/y': 'same' });
  assert.equal(findDuplicates([d]).groups.length, 0);
  assert.equal(findDuplicates([d], { ignore: [] }).groups.length, 1);
});

test('groups sorted by reclaimable bytes, descending', () => {
  const d = fixture({ 's1': 'ab', 's2': 'ab', 'b1': 'bigger', 'b2': 'bigger' });
  const r = findDuplicates([d]);
  assert.deepEqual(r.groups.map((g) => g.size), [6, 2]);
  assert.equal(r.wasted, 8);
});

test('hashFile with limit hashes only the prefix', () => {
  const d = fixture({ 'a': 'abcdef', 'b': 'abcxyz' });
  assert.equal(hashFile(path.join(d, 'a'), 3), hashFile(path.join(d, 'b'), 3));
  assert.notEqual(hashFile(path.join(d, 'a')), hashFile(path.join(d, 'b')));
});

test('humanSize and parseSize', () => {
  assert.equal(humanSize(512), '512 B');
  assert.equal(humanSize(1536), '1.5 KiB');
  assert.equal(humanSize(3 * 1024 ** 2), '3.0 MiB');
  assert.equal(parseSize('10'), 10);
  assert.equal(parseSize('2k'), 2048);
  assert.equal(parseSize('1.5M'), 1572864);
  assert.equal(parseSize('1GiB'), 1024 ** 3);
  assert.throws(() => parseSize('abc'), /invalid size/);
});

test('parseArgs', () => {
  const o = parseArgs(['dir', '--min-size', '1k', '--ignore', 'dist', '--json']);
  assert.deepEqual(o.roots, ['dir']);
  assert.equal(o.minSize, 1024);
  assert.ok(o.ignore.includes('dist'));
  assert.equal(o.json, true);
  assert.deepEqual(parseArgs([]).roots, ['.']);
  assert.throws(() => parseArgs(['--bogus']), /unknown option/);
});

test('main exit codes and output', () => {
  const dup = fixture({ 'a': 'q', 'b': 'q' });
  const uniq = fixture({ 'a': 'q', 'b': 'r' });
  let s = sink();
  assert.equal(main([dup], s), 1);
  assert.match(s.data, /1 duplicate groups, 1 redundant files, 1 B reclaimable/);
  s = sink();
  assert.equal(main([uniq], s), 0);
  s = sink();
  assert.equal(main([dup, '--json'], s), 1);
  assert.equal(JSON.parse(s.data).groups.length, 1);
  s = sink();
  assert.equal(main([path.join(uniq, 'nope')], s), 2);
  assert.equal(main(['--bad'], sink()), 2);
});
