#!/usr/bin/env node
'use strict';
// env-check: lint a .env file and compare it against a .env.example template.
// Standard library only.

const fs = require('node:fs');

const KEY_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
const ESCAPES = { n: '\n', r: '\r', t: '\t', '"': '"', '\\': '\\', $: '$' };

/**
 * Parse dotenv text.
 * Returns { entries: [{key, value, line}], issues: [{line, kind, message}] }.
 * Supports: comments, blank lines, `export ` prefix, single quotes (literal),
 * double quotes (escapes, may span lines), unquoted values with inline ` #` comments.
 */
function parse(text) {
  const lines = text.replace(/^\uFEFF/, '').split(/\r?\n/);
  const entries = [];
  const issues = [];
  for (let i = 0; i < lines.length; i++) {
    const lineNo = i + 1;
    let raw = lines[i];
    const trimmed = raw.trim();
    if (trimmed === '' || trimmed.startsWith('#')) continue;

    let body = trimmed.replace(/^export\s+/, '');
    const eq = body.indexOf('=');
    if (eq === -1) {
      issues.push({ line: lineNo, kind: 'syntax', message: `missing '=' in "${trimmed}"` });
      continue;
    }
    const keyPart = body.slice(0, eq);
    const key = keyPart.trim();
    if (keyPart !== key) {
      issues.push({ line: lineNo, kind: 'spacing', key, message: `whitespace around key "${key}"` });
    }
    if (!KEY_RE.test(key)) {
      issues.push({ line: lineNo, kind: 'invalid-key', key, message: `invalid key name "${key}"` });
      continue;
    }
    let rest = body.slice(eq + 1);
    if (/^\s/.test(rest) && rest.trim() !== '') {
      issues.push({ line: lineNo, kind: 'spacing', key, message: `whitespace after '=' for "${key}"` });
    }
    rest = rest.trimStart();

    let value;
    const q = rest[0];
    if (q === '"' || q === "'") {
      // Find closing quote, possibly on later lines (double quotes only).
      let buf = rest.slice(1);
      let close = findClose(buf, q);
      while (close === -1 && q === '"' && i + 1 < lines.length) {
        i++;
        buf += '\n' + lines[i];
        close = findClose(buf, q);
      }
      if (close === -1) {
        i = lineNo - 1; // don't swallow following lines
        issues.push({ line: lineNo, kind: 'syntax', key, message: `unterminated ${q} quote for "${key}"` });
        continue;
      }
      const inner = buf.slice(0, close);
      const after = buf.slice(close + 1).trim();
      if (after !== '' && !after.startsWith('#')) {
        issues.push({ line: lineNo, kind: 'syntax', key, message: `trailing text after quoted value for "${key}"` });
      }
      value = q === '"' ? inner.replace(/\\(.)/g, (m, c) => (c in ESCAPES ? ESCAPES[c] : m)) : inner;
    } else {
      const hash = rest.search(/\s#/);
      value = (hash === -1 ? rest : rest.slice(0, hash)).trim();
    }
    entries.push({ key, value, line: lineNo });
  }
  return { entries, issues };
}

function findClose(s, q) {
  for (let j = 0; j < s.length; j++) {
    if (q === '"' && s[j] === '\\') { j++; continue; }
    if (s[j] === q) return j;
  }
  return -1;
}

/**
 * Check an env file (and optional example). Returns sorted list of problems.
 * opts: { allowEmpty: bool, allowExtra: bool }
 */
function check(envText, exampleText, opts = {}) {
  const env = parse(envText);
  const problems = env.issues.map((p) => ({ file: 'env', ...p }));

  const seen = new Map();
  for (const e of env.entries) {
    if (seen.has(e.key)) {
      problems.push({ file: 'env', line: e.line, kind: 'duplicate', key: e.key,
        message: `duplicate key "${e.key}" (first defined on line ${seen.get(e.key)})` });
    } else {
      seen.set(e.key, e.line);
    }
    if (e.value === '' && !opts.allowEmpty) {
      problems.push({ file: 'env', line: e.line, kind: 'empty', key: e.key, message: `empty value for "${e.key}"` });
    }
  }

  if (exampleText != null) {
    const ex = parse(exampleText);
    for (const p of ex.issues) problems.push({ file: 'example', ...p });
    const exKeys = new Map();
    for (const e of ex.entries) if (!exKeys.has(e.key)) exKeys.set(e.key, e.line);
    for (const [key, line] of exKeys) {
      if (!seen.has(key)) {
        problems.push({ file: 'example', line, kind: 'missing', key, message: `missing key "${key}" (declared in example)` });
      }
    }
    if (!opts.allowExtra) {
      for (const [key, line] of seen) {
        if (!exKeys.has(key)) {
          problems.push({ file: 'env', line, kind: 'extra', key, message: `extra key "${key}" not in example` });
        }
      }
    }
  }
  const order = { env: 0, example: 1 };
  problems.sort((a, b) => order[a.file] - order[b.file] || a.line - b.line);
  return problems;
}

const USAGE = `Usage: env-check [options] [ENV_FILE]

Lint a dotenv file and compare it against an example template.

Options:
  -e, --example FILE   template file (default: .env.example if it exists)
  --no-example         skip template comparison
  --allow-empty        do not flag empty values
  --allow-extra        do not flag keys missing from the example
  --json               print problems as JSON
  -h, --help           show this help

ENV_FILE defaults to .env. Exit code: 0 clean, 1 problems, 2 usage/IO error.`;

function main(argv, out = process.stdout, err = process.stderr) {
  const opts = { allowEmpty: false, allowExtra: false };
  let envPath = null;
  let examplePath;
  let json = false;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '-h' || a === '--help') { out.write(USAGE + '\n'); return 0; }
    else if (a === '-e' || a === '--example') {
      if (i + 1 >= argv.length) { err.write(`env-check: ${a} needs a file\n`); return 2; }
      examplePath = argv[++i];
    }
    else if (a === '--no-example') examplePath = null;
    else if (a === '--allow-empty') opts.allowEmpty = true;
    else if (a === '--allow-extra') opts.allowExtra = true;
    else if (a === '--json') json = true;
    else if (a.startsWith('-')) { err.write(`env-check: unknown option ${a}\n${USAGE}\n`); return 2; }
    else if (envPath === null) envPath = a;
    else { err.write('env-check: only one ENV_FILE allowed\n'); return 2; }
  }
  envPath = envPath || '.env';
  if (examplePath === undefined) examplePath = fs.existsSync('.env.example') ? '.env.example' : null;

  let envText, exText = null;
  try {
    envText = fs.readFileSync(envPath, 'utf8');
    if (examplePath) exText = fs.readFileSync(examplePath, 'utf8');
  } catch (e) {
    err.write(`env-check: ${e.message}\n`);
    return 2;
  }

  const problems = check(envText, exText, opts);
  if (json) {
    out.write(JSON.stringify(problems, null, 2) + '\n');
  } else if (problems.length === 0) {
    out.write(`${envPath}: OK${examplePath ? ` (matches ${examplePath})` : ''}\n`);
  } else {
    for (const p of problems) {
      const file = p.file === 'env' ? envPath : examplePath;
      out.write(`${file}:${p.line}: [${p.kind}] ${p.message}\n`);
    }
    out.write(`${problems.length} problem${problems.length === 1 ? '' : 's'}\n`);
  }
  return problems.length ? 1 : 0;
}

module.exports = { parse, check, main };

if (require.main === module) process.exitCode = main(process.argv.slice(2));
