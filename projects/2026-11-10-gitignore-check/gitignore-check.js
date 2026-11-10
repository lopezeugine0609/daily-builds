#!/usr/bin/env node
'use strict';
// gitignore-check: evaluate .gitignore rules offline (library + CLI, no deps).

const fs = require('node:fs');
const path = require('node:path');

const USAGE = `usage: gitignore-check.js [--root DIR] [--file F] [--json] (--walk | PATH...)
  PATH...   check each path (relative to --root); trailing / or an existing dir = directory
            exit 0 = all kept, 1 = at least one ignored, 2 = usage/IO error
  --walk    list topmost ignored entries under root (never descends into them, skips .git)
            exit 0 on success
  --file F  ignore file, relative to root (default: .gitignore)
  --json    machine-readable output
`;

function stripTrailingSpaces(s) {
  let out = s;
  while (out.endsWith(' ') && !out.endsWith('\\ ')) out = out.slice(0, -1);
  return out;
}

function escapeRe(ch) {
  return ch.replace(/[.*+?^${}()|[\]\\/-]/g, '\\$&');
}

// Translate one gitignore glob (no leading/trailing slash handling here) to regex source.
function globToSource(glob) {
  let out = '';
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*' && glob[i + 1] === '*') {
      const segStart = i === 0 || glob[i - 1] === '/';
      const next = glob[i + 2];
      if (segStart && next === '/') { out += '(?:.*/)?'; i += 2; continue; } // "**/"
      if (segStart && next === undefined) { out += '.*'; i += 1; continue; }   // trailing "**"
    }
    if (c === '*') out += '[^/]*';
    else if (c === '?') out += '[^/]';
    else if (c === '[' && glob.indexOf(']', i + 2) !== -1) {
      const end = glob.indexOf(']', i + 2);
      let cls = glob.slice(i + 1, end);
      if (cls[0] === '!') cls = '^' + cls.slice(1);
      out += '[' + cls.replace(/\\/g, '\\\\') + ']';
      i = end;
    } else if (c === '\\' && i + 1 < glob.length) out += escapeRe(glob[++i]);
    else out += escapeRe(c);
  }
  return out;
}

function parseIgnoreFile(text, source = '.gitignore') {
  const rules = [];
  text.replace(/^\uFEFF/, '').split(/\r?\n/).forEach((raw, idx) => {
    const pattern = stripTrailingSpaces(raw);
    let body = pattern;
    if (body === '' || body.startsWith('#')) return;
    let negated = false;
    if (body.startsWith('!')) { negated = true; body = body.slice(1); }
    else if (body.startsWith('\\!') || body.startsWith('\\#')) body = body.slice(1);
    let dirOnly = false;
    if (body.endsWith('/')) { dirOnly = true; body = body.slice(0, -1); }
    const anchored = body.includes('/');
    if (body.startsWith('/')) body = body.slice(1);
    if (body === '') return;
    const src = globToSource(body);
    const regex = new RegExp(anchored ? '^' + src + '$' : '(?:^|/)' + src + '$');
    rules.push({ pattern, source, line: idx + 1, negated, dirOnly, regex });
  });
  return rules;
}

// Last matching rule wins.
function lastMatch(rules, p, isDir) {
  for (let i = rules.length - 1; i >= 0; i--) {
    const r = rules[i];
    if (r.dirOnly && !isDir) continue;
    if (r.regex.test(p)) return r;
  }
  return null;
}

// rel: posix path relative to root. Git rule: a file inside an ignored directory is ignored,
// and a negation cannot re-include it, so every ancestor is checked first.
function isIgnored(rules, rel, isDir) {
  const segs = rel.split('/').filter((s) => s && s !== '.');
  let last = null;
  for (let i = 1; i <= segs.length; i++) {
    const p = segs.slice(0, i).join('/');
    const dir = i < segs.length ? true : isDir;
    last = lastMatch(rules, p, dir);
    if (last && !last.negated) {
      return { ignored: true, rule: last, via: i < segs.length ? p : null };
    }
  }
  return { ignored: false, rule: last, via: null };
}

function walkIgnored(root, rules) {
  const out = [];
  (function visit(dirRel) {
    const abs = path.join(root, dirRel);
    for (const ent of fs.readdirSync(abs, { withFileTypes: true })) {
      if (ent.name === '.git') continue;
      const rel = dirRel ? dirRel + '/' + ent.name : ent.name;
      const isDir = ent.isDirectory();
      const r = isIgnored(rules, rel, isDir);
      if (r.ignored) out.push({ path: rel + (isDir ? '/' : ''), ignored: true, via: null, rule: r.rule });
      else if (isDir) visit(rel);
    }
  })('');
  return out;
}

function isDirectory(abs) {
  try { return fs.statSync(abs).isDirectory(); } catch { return false; }
}

function toEntry(rule) {
  return rule ? { source: rule.source, line: rule.line, pattern: rule.pattern } : null;
}

function formatLine(e) {
  let line = `${e.ignored ? 'IGNORED' : 'kept   '}  ${e.path}`;
  if (e.rule) {
    line += `  (${e.rule.source}:${e.rule.line} '${e.rule.pattern}'${e.via ? ` via ${e.via}/` : ''})`;
  }
  return line;
}

function parseArgs(argv) {
  const opts = { root: '.', file: null, json: false, walk: false, help: false, paths: [] };
  const need = (i) => {
    if (i >= argv.length) throw new Error(`missing value for ${argv[i - 1]}`);
    return argv[i];
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--root') opts.root = need(++i);
    else if (a === '--file') opts.file = need(++i);
    else if (a === '--json') opts.json = true;
    else if (a === '--walk') opts.walk = true;
    else if (a === '-h' || a === '--help') opts.help = true;
    else if (a.startsWith('-')) throw new Error(`unknown option: ${a}`);
    else opts.paths.push(a);
  }
  return opts;
}

function run(argv, out = process.stdout, err = process.stderr) {
  let opts;
  try { opts = parseArgs(argv); } catch (e) { err.write(`error: ${e.message}\n${USAGE}`); return 2; }
  if (opts.help) { out.write(USAGE); return 0; }

  const root = path.resolve(opts.root);
  const file = path.resolve(root, opts.file || '.gitignore');
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch (e) {
    err.write(`error: cannot read ${file}: ${e.code || e.message}\n`);
    return 2;
  }
  const rules = parseIgnoreFile(text, path.basename(file));

  let entries;
  if (opts.walk) {
    entries = walkIgnored(root, rules);
  } else {
    if (opts.paths.length === 0) { err.write(USAGE); return 2; }
    entries = [];
    for (const arg of opts.paths) {
      const abs = path.resolve(root, arg);
      const rel = path.relative(root, abs).split(path.sep).join('/');
      if (rel === '' || rel === '..' || rel.startsWith('../') || path.isAbsolute(rel)) {
        err.write(`error: outside root: ${arg}\n`);
        return 2;
      }
      const isDir = /[\\/]$/.test(arg) || isDirectory(abs);
      const r = isIgnored(rules, rel, isDir);
      entries.push({ path: rel + (isDir ? '/' : ''), ignored: r.ignored, via: r.via, rule: r.rule });
    }
  }

  if (opts.json) {
    const data = entries.map((e) => ({ path: e.path, ignored: e.ignored, via: e.via, rule: toEntry(e.rule) }));
    out.write(JSON.stringify(data, null, 2) + '\n');
  } else {
    if (entries.length === 0 && opts.walk) out.write('(nothing ignored)\n');
    for (const e of entries) out.write(formatLine(e) + '\n');
  }
  if (opts.walk) return 0;
  return entries.some((e) => e.ignored) ? 1 : 0;
}

module.exports = { parseIgnoreFile, isIgnored, walkIgnored, globToSource, run };

if (require.main === module) {
  process.exitCode = run(process.argv.slice(2));
}
