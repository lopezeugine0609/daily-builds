#!/usr/bin/env node
'use strict';
// slug-rename: batch-rename files in one directory to lowercase ASCII slugs.
// Dry-run by default. Collision-safe. Every --apply writes a journal so --undo can revert it.

const fs = require('node:fs');
const path = require('node:path');

const JOURNAL = '.slug-rename-journal.json';

// Lowercase ASCII slug: strip accents, non [a-z0-9] runs become '-'.
function toSlug(s) {
  return s
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// Slug a file name, keeping its extension (lowercased, alnum only).
// "My Résumé (final).PDF" -> "my-resume-final.pdf". Empty stem -> "file".
function slugify(name) {
  const ext = path.extname(name);
  const hasExt = ext.length > 1 && ext.length < name.length;
  const stem = hasExt ? name.slice(0, -ext.length) : name;
  const base = toSlug(stem) || 'file';
  const cleanExt = hasExt ? '.' + ext.slice(1).toLowerCase().replace(/[^a-z0-9]/g, '') : '';
  return base + (cleanExt.length > 1 ? cleanExt : '');
}

// Decide new names for the file names of one directory.
// Targets never equal an existing name (case-insensitive, like Windows/macOS),
// so no rename can overwrite a file or chain into another rename.
// Case-only changes ("Readme.md" -> "readme.md") are allowed.
function planRenames(names) {
  const key = (n) => n.toLowerCase();
  const taken = new Set(names.map(key));
  const renames = [];
  let unchanged = 0;
  for (const from of [...names].sort()) {
    if (from.startsWith('.')) continue; // dotfiles and the journal are never touched
    const desired = slugify(from);
    if (desired === from) { unchanged++; continue; }
    const ext = path.extname(desired);
    const stem = ext ? desired.slice(0, -ext.length) : desired;
    let to = desired;
    let n = 1;
    while (key(to) !== key(from) && taken.has(key(to))) {
      n++;
      to = `${stem}-${n}${ext}`;
    }
    taken.add(key(to));
    renames.push({ from, to, suffixed: to !== desired });
  }
  return { renames, unchanged };
}

function listFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true })
    .filter((d) => d.isFile())
    .map((d) => d.name);
}

// Rename files in dir and write the journal. Refuses to run over an old journal.
function applyRenames(dir, renames) {
  const jp = path.join(dir, JOURNAL);
  if (fs.existsSync(jp)) throw new Error(`journal ${JOURNAL} exists; run --undo first`);
  const done = [];
  try {
    for (const r of renames) {
      fs.renameSync(path.join(dir, r.from), path.join(dir, r.to));
      done.push({ from: r.from, to: r.to });
    }
  } finally {
    if (done.length) {
      fs.writeFileSync(jp, JSON.stringify({ version: 1, created: new Date().toISOString(), renames: done }, null, 2) + '\n');
    }
  }
  return done;
}

// Reverse the journal's renames, newest first. Anything blocked stays in the journal.
function undoRenames(dir) {
  const jp = path.join(dir, JOURNAL);
  if (!fs.existsSync(jp)) throw new Error(`no ${JOURNAL} in ${dir}; nothing to undo`);
  const data = JSON.parse(fs.readFileSync(jp, 'utf8'));
  const restored = [];
  const blocked = [];
  for (const r of [...data.renames].reverse()) {
    const src = path.join(dir, r.to);
    const dst = path.join(dir, r.from);
    const caseOnly = r.from.toLowerCase() === r.to.toLowerCase();
    if (!fs.existsSync(src)) { blocked.push({ ...r, reason: 'missing' }); continue; }
    if (!caseOnly && fs.existsSync(dst)) { blocked.push({ ...r, reason: 'original name taken' }); continue; }
    fs.renameSync(src, dst);
    restored.push(r);
  }
  if (blocked.length) {
    fs.writeFileSync(jp, JSON.stringify({ ...data, renames: blocked.map(({ reason, ...rest }) => rest) }, null, 2) + '\n');
  } else {
    fs.unlinkSync(jp);
  }
  return { restored, blocked };
}

function usage(out) {
  out.write([
    'usage: slug-rename.js [--apply] [--json] [DIR]',
    '       slug-rename.js --undo [DIR]',
    '  DIR       directory to process (default: .), files only, not recursive',
    '  --apply   rename for real (default is a dry run that only prints the plan)',
    '  --undo    revert the last --apply using ' + JOURNAL,
    '  --json    machine-readable output',
    '  exit 0 = ok, 2 = usage or IO error',
    '',
  ].join('\n'));
}

function main(argv) {
  const opts = { apply: false, undo: false, json: false, dir: null };
  for (const a of argv) {
    if (a === '--apply') opts.apply = true;
    else if (a === '--undo') opts.undo = true;
    else if (a === '--json') opts.json = true;
    else if (a === '-h' || a === '--help') { usage(process.stdout); return 0; }
    else if (a.startsWith('-')) { process.stderr.write(`unknown option: ${a}\n`); usage(process.stderr); return 2; }
    else if (opts.dir === null) opts.dir = a;
    else { process.stderr.write('only one DIR allowed\n'); return 2; }
  }
  if (opts.apply && opts.undo) { process.stderr.write('--apply and --undo are exclusive\n'); return 2; }
  const dir = path.resolve(opts.dir ?? '.');

  try {
    if (!fs.statSync(dir).isDirectory()) throw new Error(`not a directory: ${dir}`);

    if (opts.undo) {
      const { restored, blocked } = undoRenames(dir);
      if (opts.json) process.stdout.write(JSON.stringify({ dir, restored, blocked }, null, 2) + '\n');
      else {
        for (const r of restored) process.stdout.write(`restored ${r.to} -> ${r.from}\n`);
        for (const b of blocked) process.stdout.write(`blocked  ${b.to} -> ${b.from} (${b.reason})\n`);
        process.stdout.write(`${restored.length} restored, ${blocked.length} blocked\n`);
      }
      return blocked.length ? 1 : 0;
    }

    const { renames, unchanged } = planRenames(listFiles(dir));
    let applied = null;
    if (opts.apply) applied = applyRenames(dir, renames);

    if (opts.json) {
      process.stdout.write(JSON.stringify({ dir, dryRun: !opts.apply, renames, unchanged, applied }, null, 2) + '\n');
    } else {
      for (const r of renames) {
        process.stdout.write(`${r.from} -> ${r.to}${r.suffixed ? '  (collision: suffixed)' : ''}\n`);
      }
      if (opts.apply) {
        process.stdout.write(`renamed ${applied.length} file(s); undo with --undo. journal: ${JOURNAL}\n`);
      } else {
        process.stdout.write(`dry run: ${renames.length} to rename, ${unchanged} unchanged (add --apply to rename)\n`);
      }
    }
    return 0;
  } catch (err) {
    process.stderr.write(`error: ${err.message}\n`);
    return 2;
  }
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));

module.exports = { slugify, toSlug, planRenames, applyRenames, undoRenames, JOURNAL };
