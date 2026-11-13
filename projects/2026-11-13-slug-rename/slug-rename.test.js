'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { slugify, planRenames, applyRenames, undoRenames, JOURNAL } = require('./slug-rename.js');

const CLI = path.join(__dirname, 'slug-rename.js');

function tmpDir(files) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'slug-rename-'));
  for (const f of files) fs.writeFileSync(path.join(dir, f), f);
  return dir;
}
const ls = (dir) => fs.readdirSync(dir).sort();

test('slugify lowercases, strips accents, keeps extension', () => {
  assert.equal(slugify('My Résumé (final).PDF'), 'my-resume-final.pdf');
  assert.equal(slugify('Hello   World.txt'), 'hello-world.txt');
  assert.equal(slugify('__weird__name__.md'), 'weird-name.md');
});

test('slugify handles names with no stem or no extension', () => {
  assert.equal(slugify('!!!.txt'), 'file.txt');
  assert.equal(slugify('Makefile'), 'makefile');
  assert.equal(slugify('archive.TAR.GZ'), 'archive-tar.gz');
  assert.equal(slugify('.hidden name'), 'hidden-name');
});

test('planRenames skips already-clean names and dotfiles', () => {
  const { renames, unchanged } = planRenames(['clean-name.txt', '.env', 'Dirty Name.txt']);
  assert.equal(unchanged, 1);
  assert.deepEqual(renames.map((r) => [r.from, r.to]), [['Dirty Name.txt', 'dirty-name.txt']]);
});

test('planRenames suffixes on collision with an existing file', () => {
  const { renames } = planRenames(['a-b.txt', 'A B.txt']);
  assert.equal(renames.length, 1);
  assert.equal(renames[0].to, 'a-b-2.txt');
  assert.equal(renames[0].suffixed, true);
});

test('planRenames avoids collisions between two renamed files', () => {
  const { renames } = planRenames(['x y.md', 'x_y.md', 'X-Y.md']);
  const targets = renames.map((r) => r.to.toLowerCase());
  assert.equal(new Set(targets).size, targets.length);
  assert.ok(targets.every((t) => t !== 'x-y.md' || !renames.some((r) => r.from === t)));
});

test('planRenames allows case-only changes', () => {
  const { renames } = planRenames(['Readme.md']);
  assert.deepEqual(renames.map((r) => [r.from, r.to, r.suffixed]), [['Readme.md', 'readme.md', false]]);
});

test('applyRenames renames files and writes a journal; undo restores them', () => {
  const dir = tmpDir(['Foo Bar.txt', 'baz qux.md']);
  const { renames } = planRenames(ls(dir));
  applyRenames(dir, renames);
  assert.deepEqual(ls(dir), [JOURNAL, 'baz-qux.md', 'foo-bar.txt'].sort());
  const { restored, blocked } = undoRenames(dir);
  assert.equal(restored.length, 2);
  assert.equal(blocked.length, 0);
  assert.deepEqual(ls(dir), ['Foo Bar.txt', 'baz qux.md']);
});

test('applyRenames refuses when a journal already exists', () => {
  const dir = tmpDir(['A B.txt']);
  fs.writeFileSync(path.join(dir, JOURNAL), '{}');
  assert.throws(() => applyRenames(dir, planRenames(ls(dir)).renames), /journal .* exists/);
});

test('undoRenames blocks a rename when the original name was re-used', () => {
  const dir = tmpDir(['A B.txt']);
  applyRenames(dir, planRenames(ls(dir)).renames);
  fs.writeFileSync(path.join(dir, 'A B.txt'), 'new file');
  const { restored, blocked } = undoRenames(dir);
  assert.equal(restored.length, 0);
  assert.equal(blocked[0].reason, 'original name taken');
  assert.ok(fs.existsSync(path.join(dir, JOURNAL)), 'journal kept for retry');
});

test('undoRenames throws without a journal', () => {
  const dir = tmpDir([]);
  assert.throws(() => undoRenames(dir), /nothing to undo/);
});

test('CLI dry run changes nothing and exits 0', () => {
  const dir = tmpDir(['My File.txt']);
  const out = execFileSync(process.execPath, [CLI, dir], { encoding: 'utf8' });
  assert.match(out, /My File\.txt -> my-file\.txt/);
  assert.match(out, /dry run: 1 to rename/);
  assert.deepEqual(ls(dir), ['My File.txt']);
});

test('CLI --apply then --undo round trip, JSON output', () => {
  const dir = tmpDir(['Hello World.md']);
  execFileSync(process.execPath, [CLI, '--apply', dir], { encoding: 'utf8' });
  assert.deepEqual(ls(dir), [JOURNAL, 'hello-world.md'].sort());
  const json = JSON.parse(execFileSync(process.execPath, [CLI, '--undo', '--json', dir], { encoding: 'utf8' }));
  assert.equal(json.restored.length, 1);
  assert.deepEqual(ls(dir), ['Hello World.md']);
});

test('CLI usage errors exit 2', () => {
  const run = (args) => {
    try { execFileSync(process.execPath, [CLI, ...args], { stdio: 'pipe' }); return 0; }
    catch (e) { return e.status; }
  };
  assert.equal(run(['--bogus']), 2);
  assert.equal(run(['--apply', '--undo']), 2);
  assert.equal(run([path.join(os.tmpdir(), 'does-not-exist-slug-rename')]), 2);
});
