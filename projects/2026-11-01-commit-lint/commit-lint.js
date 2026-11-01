#!/usr/bin/env node
'use strict';
// commit-lint: zero-dependency Conventional Commits 1.0.0 linter.
// Lints a message from args, a file, stdin, or every commit in a git range.

const fs = require('node:fs');
const { execFileSync } = require('node:child_process');

const DEFAULT_TYPES = ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test',
  'build', 'ci', 'chore', 'revert'];

const DEFAULTS = { types: DEFAULT_TYPES, headerMax: 72, bodyLineMax: 100, scopes: null, requireScope: false };

// type(scope)!: subject
const HEADER_RE = /^(?<type>[A-Za-z]+)(?:\((?<scope>[^()\r\n]*)\))?(?<bang>!)?(?<sep>:\s*)(?<subject>.*)$/;
const FOOTER_RE = /^(?<token>breaking[ -]change|[a-z][a-z-]*)(?<sep>: | #)(?<value>.+)$/i;

function stripComments(text) {
  return text.replace(/\r\n/g, '\n').split('\n').filter((l) => !l.startsWith('#')).join('\n').trim();
}

function parse(message) {
  const lines = stripComments(message).split('\n');
  const header = lines[0] || '';
  const m = HEADER_RE.exec(header);
  const rest = lines.slice(1);
  // Footers: trailing block of lines after the last blank line that all look like footers.
  let footerStart = rest.length;
  const lastBlank = rest.lastIndexOf('');
  if (lastBlank >= 0) {
    const tail = rest.slice(lastBlank + 1);
    if (tail.length && FOOTER_RE.test(tail[0])) footerStart = lastBlank + 1;
  }
  const footers = [];
  for (const line of rest.slice(footerStart)) {
    const f = FOOTER_RE.exec(line);
    if (f) footers.push({ token: f.groups.token, value: f.groups.value });
    else if (footers.length) footers[footers.length - 1].value += '\n' + line; // continuation
  }
  const body = rest.slice(0, footerStart).join('\n').trim();
  return {
    header,
    type: m ? m.groups.type : null,
    scope: m && m.groups.scope !== undefined ? m.groups.scope : null,
    bang: !!(m && m.groups.bang),
    sep: m ? m.groups.sep : null,
    subject: m ? m.groups.subject : null,
    body,
    footers,
    rawRest: rest,
    breaking: !!(m && m.groups.bang) || footers.some((f) => /^BREAKING[ -]CHANGE$/.test(f.token)),
  };
}

function lint(message, opts = {}) {
  const o = { ...DEFAULTS, ...opts };
  const p = parse(message);
  const errors = [];
  const warnings = [];
  const err = (rule, msg) => errors.push({ rule, message: msg });
  const warn = (rule, msg) => warnings.push({ rule, message: msg });

  if (!p.header.trim()) {
    err('header-empty', 'commit message is empty');
    return { valid: false, errors, warnings, parsed: p };
  }
  if (p.type === null) {
    err('header-format', 'header must match "type(scope)!: subject"');
  } else {
    if (p.type !== p.type.toLowerCase()) err('type-case', `type "${p.type}" must be lower-case`);
    if (!o.types.includes(p.type.toLowerCase())) err('type-enum', `type "${p.type}" not in [${o.types.join(', ')}]`);
    if (p.scope !== null) {
      if (!p.scope.trim()) err('scope-empty', 'scope parentheses are empty');
      else if (o.scopes && !o.scopes.includes(p.scope)) err('scope-enum', `scope "${p.scope}" not in [${o.scopes.join(', ')}]`);
    } else if (o.requireScope) err('scope-required', 'scope is required');
    if (p.sep !== ': ') err('header-separator', 'type must be followed by ": " (colon + one space)');
    const subj = p.subject.trim();
    if (!subj) err('subject-empty', 'subject is empty');
    else {
      if (/\.$/.test(subj)) err('subject-full-stop', 'subject must not end with "."');
      if (/^[A-Z][a-z]/.test(subj)) warn('subject-case', 'subject should start lower-case');
      if (/^(added|adds|fixed|fixes|updated|updates|removed|removes)\b/i.test(subj))
        warn('subject-mood', 'use imperative mood ("add", not "added"/"adds")');
    }
  }
  if (p.header.length > o.headerMax) err('header-max-length', `header is ${p.header.length} chars (max ${o.headerMax})`);
  if (p.rawRest.length && p.rawRest[0] !== '') err('body-leading-blank', 'blank line required between header and body');
  p.rawRest.forEach((line, i) => {
    if (line.length > o.bodyLineMax && !/https?:\/\//.test(line))
      warn('body-max-line-length', `line ${i + 2} is ${line.length} chars (max ${o.bodyLineMax})`);
  });
  for (const f of p.footers) {
    if (/^breaking[ -]change$/i.test(f.token) && !/^BREAKING[ -]CHANGE$/.test(f.token))
      err('footer-breaking-case', 'BREAKING CHANGE token must be upper-case');
  }
  if (p.bang && !p.footers.some((f) => /^BREAKING[ -]CHANGE$/.test(f.token)) && !p.body)
    warn('breaking-description', '"!" used without a BREAKING CHANGE footer or body explaining it');
  return { valid: errors.length === 0, errors, warnings, parsed: p };
}

function gitCommits(range, cwd) {
  const out = execFileSync('git', ['log', '--format=%H%x1f%B%x1e', range], { cwd, encoding: 'utf8' });
  return out.split('\x1e').map((s) => s.replace(/^\n/, '')).filter((s) => s.trim()).map((s) => {
    const [sha, msg] = s.split('\x1f');
    return { id: sha.slice(0, 7), message: msg };
  }).filter((c) => !/^(Merge |Revert ")/.test(c.message)); // skip auto-generated
}

const USAGE = `usage: commit-lint [options] [message]
  message            commit message text (else --file, --git, or stdin)
  -f, --file PATH    read message from file (e.g. .git/COMMIT_EDITMSG)
  -g, --git RANGE    lint every commit in git range (e.g. origin/main..HEAD)
  --types a,b,c      allowed types (default: ${DEFAULT_TYPES.join(',')})
  --scopes a,b       allowed scopes (default: any)
  --require-scope    scope is mandatory
  --max N            header max length (default 72)
  --strict           treat warnings as errors
  --json             JSON output
exit: 0 ok, 1 lint errors, 2 usage/IO error`;

function parseArgs(argv) {
  const a = { opts: {}, text: [], json: false, strict: false };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const val = () => { if (i + 1 >= argv.length) throw new Error(`${k} needs a value`); return argv[++i]; };
    if (k === '-h' || k === '--help') a.help = true;
    else if (k === '-f' || k === '--file') a.file = val();
    else if (k === '-g' || k === '--git') a.git = val();
    else if (k === '--types') a.opts.types = val().split(',').map((s) => s.trim()).filter(Boolean);
    else if (k === '--scopes') a.opts.scopes = val().split(',').map((s) => s.trim()).filter(Boolean);
    else if (k === '--require-scope') a.opts.requireScope = true;
    else if (k === '--max') { a.opts.headerMax = Number(val()); if (!Number.isInteger(a.opts.headerMax) || a.opts.headerMax < 1) throw new Error('--max must be a positive integer'); }
    else if (k === '--strict') a.strict = true;
    else if (k === '--json') a.json = true;
    else if (k.startsWith('-') && k !== '-') throw new Error(`unknown option ${k}`);
    else a.text.push(k);
  }
  return a;
}

function main(argv, io = { stdout: process.stdout, stderr: process.stderr, stdin: () => fs.readFileSync(0, 'utf8'), cwd: process.cwd() }) {
  let a;
  try { a = parseArgs(argv); } catch (e) { io.stderr.write(`commit-lint: ${e.message}\n${USAGE}\n`); return 2; }
  if (a.help) { io.stdout.write(USAGE + '\n'); return 0; }
  let commits;
  try {
    if (a.git) commits = gitCommits(a.git, io.cwd);
    else if (a.file) commits = [{ id: a.file, message: fs.readFileSync(a.file, 'utf8') }];
    else if (a.text.length) commits = [{ id: 'arg', message: a.text.join(' ').replace(/\\n/g, '\n') }];
    else commits = [{ id: 'stdin', message: io.stdin() }];
  } catch (e) { io.stderr.write(`commit-lint: ${e.message.split('\n')[0]}\n`); return 2; }

  const results = commits.map((c) => {
    const r = lint(c.message, a.opts);
    if (a.strict && r.warnings.length) { r.errors.push(...r.warnings); r.warnings = []; r.valid = false; }
    return { id: c.id, header: r.parsed.header, valid: r.valid, breaking: r.parsed.breaking, errors: r.errors, warnings: r.warnings };
  });
  const bad = results.filter((r) => !r.valid).length;
  if (a.json) io.stdout.write(JSON.stringify({ checked: results.length, failed: bad, results }, null, 2) + '\n');
  else {
    for (const r of results) {
      io.stdout.write(`${r.valid ? 'ok  ' : 'FAIL'} ${r.id}  ${r.header}${r.breaking ? '  [BREAKING]' : ''}\n`);
      for (const e of r.errors) io.stdout.write(`     error  ${e.rule}: ${e.message}\n`);
      for (const w of r.warnings) io.stdout.write(`     warn   ${w.rule}: ${w.message}\n`);
    }
    io.stdout.write(`${results.length} checked, ${bad} failed\n`);
  }
  return bad ? 1 : 0;
}

module.exports = { parse, lint, main, DEFAULT_TYPES };

if (require.main === module) process.exitCode = main(process.argv.slice(2));
