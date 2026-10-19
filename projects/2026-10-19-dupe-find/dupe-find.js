#!/usr/bin/env node
'use strict';
// dupe-find: find duplicate files by content.
// Pipeline: group by size -> group by hash of first 4 KiB -> group by full SHA-256.
// Each stage only hashes files that still collide, so unique sizes cost zero reads.

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const PARTIAL_BYTES = 4096;
const DEFAULT_IGNORE = ['.git', 'node_modules'];

function walk(roots, { ignore = DEFAULT_IGNORE, minSize = 1 } = {}) {
  const files = [];
  const seen = new Set(); // dev:ino, so the same file reached twice is counted once
  const stack = [...roots];
  while (stack.length) {
    const p = stack.pop();
    let st;
    try { st = fs.lstatSync(p); } catch { continue; }
    if (st.isSymbolicLink()) continue;
    if (st.isDirectory()) {
      let entries;
      try { entries = fs.readdirSync(p); } catch { continue; }
      for (const name of entries.sort().reverse()) {
        if (!ignore.includes(name)) stack.push(path.join(p, name));
      }
    } else if (st.isFile() && st.size >= minSize) {
      const key = `${st.dev}:${st.ino}`;
      if (st.ino && seen.has(key)) continue;
      seen.add(key);
      files.push({ path: p, size: st.size });
    }
  }
  return files;
}

function hashFile(file, limit) {
  const h = crypto.createHash('sha256');
  const fd = fs.openSync(file, 'r');
  try {
    const buf = Buffer.alloc(64 * 1024);
    let total = 0;
    for (;;) {
      const want = limit ? Math.min(buf.length, limit - total) : buf.length;
      if (want <= 0) break;
      const n = fs.readSync(fd, buf, 0, want, null);
      if (n === 0) break;
      h.update(buf.subarray(0, n));
      total += n;
    }
  } finally {
    fs.closeSync(fd);
  }
  return h.digest('hex');
}

function groupBy(items, keyFn) {
  const m = new Map();
  for (const it of items) {
    let k;
    try { k = keyFn(it); } catch { continue; } // unreadable file: drop it
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(it);
  }
  return [...m.values()].filter((g) => g.length > 1);
}

function findDuplicates(roots, opts = {}) {
  const files = walk(roots, opts);
  const stats = { scanned: files.length, partialHashed: 0, fullHashed: 0 };
  const groups = [];
  for (const sameSize of groupBy(files, (f) => f.size)) {
    let candidates = [sameSize];
    if (sameSize[0].size > PARTIAL_BYTES) {
      stats.partialHashed += sameSize.length;
      candidates = groupBy(sameSize, (f) => hashFile(f.path, PARTIAL_BYTES));
    }
    for (const c of candidates) {
      stats.fullHashed += c.length;
      for (const g of groupBy(c, (f) => hashFile(f.path))) {
        groups.push({
          size: g[0].size,
          hash: hashFile(g[0].path),
          paths: g.map((f) => f.path).sort(),
        });
      }
    }
  }
  groups.sort((a, b) => b.size * (b.paths.length - 1) - a.size * (a.paths.length - 1)
    || a.paths[0].localeCompare(b.paths[0]));
  const wasted = groups.reduce((s, g) => s + g.size * (g.paths.length - 1), 0);
  return { groups, wasted, stats };
}

function humanSize(n) {
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return i === 0 ? `${n} B` : `${n.toFixed(1)} ${units[i]}`;
}

function parseSize(s) {
  const m = /^(\d+(?:\.\d+)?)\s*([kmg]?)i?b?$/i.exec(String(s).trim());
  if (!m) throw new Error(`invalid size: ${s}`);
  const mult = { '': 1, k: 1024, m: 1024 ** 2, g: 1024 ** 3 }[m[2].toLowerCase()];
  return Math.floor(parseFloat(m[1]) * mult);
}

function parseArgs(argv) {
  const o = { roots: [], minSize: 1, json: false, ignore: [...DEFAULT_IGNORE], help: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '-h' || a === '--help') o.help = true;
    else if (a === '--json') o.json = true;
    else if (a === '--min-size') o.minSize = parseSize(argv[++i]);
    else if (a === '--ignore') o.ignore.push(argv[++i]);
    else if (a === '--no-default-ignore') o.ignore = o.ignore.filter((x) => !DEFAULT_IGNORE.includes(x));
    else if (a.startsWith('-')) throw new Error(`unknown option: ${a}`);
    else o.roots.push(a);
  }
  if (!o.roots.length) o.roots.push('.');
  return o;
}

const USAGE = `usage: dupe-find [dir...] [--min-size N[k|m|g]] [--ignore NAME] [--no-default-ignore] [--json]
Find files with identical content. Exit code 1 if duplicates found, 0 if none, 2 on error.`;

function main(argv, out = process.stdout) {
  let o;
  try { o = parseArgs(argv); } catch (e) { out.write(`error: ${e.message}\n${USAGE}\n`); return 2; }
  if (o.help) { out.write(USAGE + '\n'); return 0; }
  for (const r of o.roots) {
    if (!fs.existsSync(r)) { out.write(`error: no such path: ${r}\n`); return 2; }
  }
  const res = findDuplicates(o.roots, o);
  if (o.json) {
    out.write(JSON.stringify(res, null, 2) + '\n');
  } else {
    for (const g of res.groups) {
      out.write(`${humanSize(g.size)} x ${g.paths.length}  sha256:${g.hash.slice(0, 12)}\n`);
      for (const p of g.paths) out.write(`  ${p}\n`);
    }
    const dupFiles = res.groups.reduce((s, g) => s + g.paths.length - 1, 0);
    out.write(`${res.stats.scanned} files scanned, ${res.groups.length} duplicate groups, `
      + `${dupFiles} redundant files, ${humanSize(res.wasted)} reclaimable\n`);
  }
  return res.groups.length ? 1 : 0;
}

module.exports = { walk, hashFile, findDuplicates, humanSize, parseSize, parseArgs, main };

if (require.main === module) process.exitCode = main(process.argv.slice(2));
