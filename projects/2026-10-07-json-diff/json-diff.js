#!/usr/bin/env node
'use strict';
// json-diff: structural diff of two JSON documents, reported as JSON paths.
// Standard library only.

const fs = require('node:fs');

function typeOf(v) {
  if (v === null) return 'null';
  if (Array.isArray(v)) return 'array';
  return typeof v;
}

const IDENT = /^[A-Za-z_$][A-Za-z0-9_$]*$/;

function joinPath(base, key) {
  if (typeof key === 'number') return `${base}[${key}]`;
  if (IDENT.test(key)) return `${base}.${key}`;
  return `${base}[${JSON.stringify(key)}]`;
}

/**
 * Compare two JSON values. Returns a list of changes:
 *   { op: 'add' | 'remove' | 'change', path, from?, to? }
 * Options:
 *   ignore: array of paths (exact match) to skip, including their subtrees
 *   epsilon: tolerance for number comparison (default 0)
 */
function diff(a, b, options = {}, path = '$', out = []) {
  const ignore = options.ignore || [];
  const epsilon = options.epsilon || 0;
  if (ignore.includes(path)) return out;

  const ta = typeOf(a);
  const tb = typeOf(b);
  if (ta !== tb) {
    out.push({ op: 'change', path, from: a, to: b });
    return out;
  }
  if (ta === 'object') {
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    for (const k of [...keys].sort()) {
      const p = joinPath(path, k);
      if (ignore.includes(p)) continue;
      const inA = Object.prototype.hasOwnProperty.call(a, k);
      const inB = Object.prototype.hasOwnProperty.call(b, k);
      if (inA && !inB) out.push({ op: 'remove', path: p, from: a[k] });
      else if (!inA && inB) out.push({ op: 'add', path: p, to: b[k] });
      else diff(a[k], b[k], options, p, out);
    }
    return out;
  }
  if (ta === 'array') {
    const n = Math.max(a.length, b.length);
    for (let i = 0; i < n; i++) {
      const p = joinPath(path, i);
      if (ignore.includes(p)) continue;
      if (i >= b.length) out.push({ op: 'remove', path: p, from: a[i] });
      else if (i >= a.length) out.push({ op: 'add', path: p, to: b[i] });
      else diff(a[i], b[i], options, p, out);
    }
    return out;
  }
  if (ta === 'number' && Math.abs(a - b) <= epsilon) return out;
  if (a !== b) out.push({ op: 'change', path, from: a, to: b });
  return out;
}

function fmt(v) {
  const s = JSON.stringify(v);
  return s.length > 60 ? s.slice(0, 57) + '...' : s;
}

function formatText(changes) {
  if (changes.length === 0) return 'No differences.';
  const lines = changes.map((c) => {
    if (c.op === 'add') return `+ ${c.path}: ${fmt(c.to)}`;
    if (c.op === 'remove') return `- ${c.path}: ${fmt(c.from)}`;
    return `~ ${c.path}: ${fmt(c.from)} -> ${fmt(c.to)}`;
  });
  const count = (op) => changes.filter((c) => c.op === op).length;
  lines.push('');
  lines.push(`${count('add')} added, ${count('remove')} removed, ${count('change')} changed`);
  return lines.join('\n');
}

const USAGE = `Usage: node json-diff.js <a.json> <b.json> [options]
Options:
  --json             output changes as a JSON array
  --ignore <path>    skip a path (repeatable), e.g. --ignore $.meta.updated
  --epsilon <n>      treat numbers within n as equal
  -h, --help         show this help
Exit codes: 0 = identical, 1 = differences, 2 = error`;

function parseArgs(argv) {
  const opts = { files: [], ignore: [], epsilon: 0, json: false, help: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--json') opts.json = true;
    else if (arg === '-h' || arg === '--help') opts.help = true;
    else if (arg === '--ignore') opts.ignore.push(argv[++i]);
    else if (arg === '--epsilon') {
      opts.epsilon = Number(argv[++i]);
      if (!Number.isFinite(opts.epsilon) || opts.epsilon < 0) {
        throw new Error('--epsilon needs a non-negative number');
      }
    } else if (arg.startsWith('--')) throw new Error(`unknown option ${arg}`);
    else opts.files.push(arg);
  }
  return opts;
}

function readJson(file) {
  const text = file === '-' ? fs.readFileSync(0, 'utf8') : fs.readFileSync(file, 'utf8');
  try {
    return JSON.parse(text);
  } catch (e) {
    throw new Error(`${file}: invalid JSON (${e.message})`);
  }
}

function main(argv, stdout = process.stdout, stderr = process.stderr) {
  let opts;
  try {
    opts = parseArgs(argv);
  } catch (e) {
    stderr.write(`json-diff: ${e.message}\n`);
    return 2;
  }
  if (opts.help) {
    stdout.write(USAGE + '\n');
    return 0;
  }
  if (opts.files.length !== 2) {
    stderr.write(USAGE + '\n');
    return 2;
  }
  try {
    const a = readJson(opts.files[0]);
    const b = readJson(opts.files[1]);
    const changes = diff(a, b, { ignore: opts.ignore, epsilon: opts.epsilon });
    stdout.write((opts.json ? JSON.stringify(changes, null, 2) : formatText(changes)) + '\n');
    return changes.length ? 1 : 0;
  } catch (e) {
    stderr.write(`json-diff: ${e.message}\n`);
    return 2;
  }
}

module.exports = { diff, formatText, parseArgs, main, joinPath };

if (require.main === module) {
  process.exitCode = main(process.argv.slice(2));
}
