'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync, spawnSync } = require('node:child_process');
const { slugify, parseHeadings, buildToc, injectToc, parseArgs } = require('./md-toc.js');

const CLI = path.join(__dirname, 'md-toc.js');

test('slugify matches GitHub rules', () => {
  assert.equal(slugify('Hello World'), 'hello-world');
  assert.equal(slugify('What is `npm ci`?'), 'what-is-npm-ci');
  assert.equal(slugify('C++ & Rust: a comparison'), 'c--rust-a-comparison');
  assert.equal(slugify('snake_case stays'), 'snake_case-stays');
  assert.equal(slugify('[Link](http://x.y) text'), 'link-text');
  assert.equal(slugify('Café Ünïcode'), 'café-ünïcode');
  assert.equal(slugify('**Bold** _it_'), 'bold-it');
});

test('parseHeadings handles ATX, closing hashes, setext and fenced code', () => {
  const md = [
    '# Title #',
    'Sub',
    '---',
    '```bash',
    '# not a heading',
    '```',
    '~~~',
    '## also not',
    '~~~',
    '#NoSpace',
    '   ### Indented ok',
    'Top',
    '===',
  ].join('\n');
  assert.deepEqual(
    parseHeadings(md).map((h) => [h.level, h.text]),
    [[1, 'Title'], [2, 'Sub'], [3, 'Indented ok'], [1, 'Top']],
  );
});

test('list item followed by --- is not a setext heading', () => {
  assert.deepEqual(parseHeadings('- item\n---\n'), []);
});

test('buildToc nests, dedupes slugs, and respects min/max', () => {
  const md = '# Doc\n## Usage\n### Notes\n## API\n### Notes\n#### Deep\n';
  assert.equal(
    buildToc(md),
    [
      '- [Doc](#doc)',
      '  - [Usage](#usage)',
      '    - [Notes](#notes)',
      '  - [API](#api)',
      '    - [Notes](#notes-1)',
      '      - [Deep](#deep)',
    ].join('\n'),
  );
  // Filtered output still keeps GitHub's global numbering for duplicates.
  assert.equal(
    buildToc(md, { min: 2, max: 3 }),
    '- [Usage](#usage)\n  - [Notes](#notes)\n- [API](#api)\n  - [Notes](#notes-1)',
  );
  assert.equal(buildToc('no headings'), '');
});

test('buildToc escapes brackets in labels', () => {
  assert.equal(buildToc('## Array [x]'), '- [Array \\[x\\]](#array-x)');
});

test('injectToc replaces stale content and is idempotent', () => {
  const md = '# A\n<!-- toc -->\nold junk\n<!-- tocstop -->\n## B\n';
  const once = injectToc(md, { min: 2 });
  assert.equal(once, '# A\n<!-- toc -->\n\n- [B](#b)\n\n<!-- tocstop -->\n## B\n');
  assert.equal(injectToc(once, { min: 2 }), once);
});

test('injectToc preserves CRLF line endings', () => {
  const md = '<!-- toc -->\r\n<!-- tocstop -->\r\n# A\r\n## B\r\n';
  const out = injectToc(md);
  assert.ok(out.includes('- [A](#a)\r\n  - [B](#b)\r\n'));
  assert.ok(!/[^\r]\n/.test(out));
});

test('injectToc throws without markers', () => {
  assert.throws(() => injectToc('# A'), /markers not found/);
});

test('parseArgs validates levels', () => {
  assert.throws(() => parseArgs(['--min', '0', 'f']), /1-6/);
  assert.throws(() => parseArgs(['--min', '4', '--max', '2', 'f']), /<=/);
  assert.throws(() => parseArgs(['--bogus']), /unknown option/);
  assert.deepEqual(parseArgs(['-w', '--max', '3', 'a.md']).files, ['a.md']);
});

test('CLI --write then --check', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'md-toc-'));
  const f = path.join(dir, 'doc.md');
  fs.writeFileSync(f, '# Doc\n<!-- toc -->\n<!-- tocstop -->\n## One\n## Two\n');

  let r = spawnSync(process.execPath, [CLI, '--check', '--min', '2', f], { encoding: 'utf8' });
  assert.equal(r.status, 1);
  assert.match(r.stderr, /out of date/);

  const out = execFileSync(process.execPath, [CLI, '-w', '--min', '2', f], { encoding: 'utf8' });
  assert.match(out, /updated/);
  assert.match(fs.readFileSync(f, 'utf8'), /- \[Two\]\(#two\)/);

  r = spawnSync(process.execPath, [CLI, '--check', '--min', '2', f], { encoding: 'utf8' });
  assert.equal(r.status, 0);
  assert.match(r.stdout, /OK/);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('CLI missing file exits 2', () => {
  const r = spawnSync(process.execPath, [CLI, 'does-not-exist.md'], { encoding: 'utf8' });
  assert.equal(r.status, 2);
  assert.match(r.stderr, /cannot read/);
});
