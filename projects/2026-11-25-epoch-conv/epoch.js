#!/usr/bin/env node
'use strict';
// epoch-conv: convert between Unix epoch (s/ms/us/ns), ISO 8601 and relative
// times. Internal representation is BigInt nanoseconds since 1970-01-01Z, so
// nanosecond inputs round-trip without float loss.

const NS = { ns: 1n, us: 1000n, ms: 1000000n, s: 1000000000n };
const UNIT_NS = {
  ns: 1n, us: 1000n, ms: 1000000n, s: 1000000000n,
  m: 60000000000n, h: 3600000000000n, d: 86400000000000n, w: 604800000000000n,
};

// Guess the unit of a bare integer epoch by magnitude (works for 1973..5138).
function detectUnit(abs) {
  if (abs < 100000000000n) return 's';          // < 1e11
  if (abs < 100000000000000n) return 'ms';      // < 1e14
  if (abs < 100000000000000000n) return 'us';   // < 1e17
  return 'ns';
}

// "1h30m", "-2d", "45s" -> BigInt ns
function parseDuration(text) {
  const t = text.trim();
  const m = /^([+-]?)((?:\d+(?:ns|us|ms|s|m|h|d|w))+)$/.exec(t);
  if (!m) throw new Error(`invalid duration: ${text}`);
  let total = 0n;
  for (const [, n, u] of m[2].matchAll(/(\d+)(ns|us|ms|s|m|h|d|w)/g)) {
    total += BigInt(n) * UNIT_NS[u];
  }
  return m[1] === '-' ? -total : total;
}

const ISO_RE = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,9}))?)?)?\s*(Z|[+-]\d{2}:?\d{2})?$/i;

function parseIso(text) {
  const m = ISO_RE.exec(text.trim());
  if (!m) return null;
  const [, Y, Mo, D, h = '0', mi = '0', s = '0', frac = '', tz] = m;
  const ms = Date.UTC(+Y, +Mo - 1, +D, +h, +mi, +s);
  const check = new Date(ms);
  if (check.getUTCMonth() !== +Mo - 1 || check.getUTCDate() !== +D || +h > 23 || +mi > 59 || +s > 59) {
    throw new Error(`invalid date: ${text}`);
  }
  let ns = BigInt(ms) * NS.ms + BigInt((frac + '000000000').slice(0, 9));
  if (tz && tz.toUpperCase() !== 'Z') ns -= BigInt(parseOffset(tz)) * UNIT_NS.m;
  return ns;
}

// "+08:00" / "-0530" / "Z" -> minutes
function parseOffset(text) {
  if (text === 'Z' || text === 'z' || text === 'UTC') return 0;
  const m = /^([+-])(\d{2}):?(\d{2})$/.exec(text);
  if (!m || +m[2] > 23 || +m[3] > 59) throw new Error(`invalid offset: ${text}`);
  return (m[1] === '-' ? -1 : 1) * (+m[2] * 60 + +m[3]);
}

// Parse any supported input. opts: { now: BigInt ns, unit: forced unit }
function parseTime(input, opts = {}) {
  const now = opts.now ?? BigInt(Date.now()) * NS.ms;
  const t = String(input).trim();
  const rel = /^now\s*(?:([+-])\s*(.+))?$/i.exec(t);
  if (rel) return rel[1] ? now + (rel[1] === '-' ? -1n : 1n) * parseDuration(rel[2]) : now;
  if (/^[+-]\d/.test(t) && /[a-z]$/i.test(t)) return now + parseDuration(t);
  const num = /^(-?\d+)(?:\.(\d+))?$/.exec(t);
  if (num) {
    const whole = BigInt(num[1]);
    const unit = opts.unit || detectUnit(whole < 0n ? -whole : whole);
    if (!NS[unit]) throw new Error(`invalid unit: ${unit}`);
    let ns = whole * NS[unit];
    if (num[2]) {
      const digits = NS[unit].toString().length - 1;
      const frac = BigInt((num[2] + '0'.repeat(digits)).slice(0, digits) || '0');
      ns += (whole < 0n || num[1].startsWith('-') ? -frac : frac);
    }
    return ns;
  }
  const iso = parseIso(t);
  if (iso !== null) return iso;
  throw new Error(`unrecognised time: ${input}`);
}

const floorDiv = (a, b) => (a % b === 0n || a >= 0n ? a / b : a / b - 1n);
const pad = (n, w = 2) => String(n).padStart(w, '0');

// ns -> ISO 8601 at a given offset (minutes); trims trailing fractional zeros.
function formatIso(ns, offsetMin = 0) {
  const shifted = ns + BigInt(offsetMin) * UNIT_NS.m;
  const ms = floorDiv(shifted, NS.ms);
  const subNs = shifted - floorDiv(shifted, NS.s) * NS.s;
  const d = new Date(Number(ms));
  if (Number.isNaN(d.getTime())) throw new Error('time out of range');
  let out = `${pad(d.getUTCFullYear(), 4)}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}` +
    `T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`;
  if (subNs !== 0n) out += '.' + pad(subNs, 9).replace(/0+$/, '');
  if (offsetMin === 0) return out + 'Z';
  const a = Math.abs(offsetMin);
  return out + (offsetMin < 0 ? '-' : '+') + pad(Math.floor(a / 60)) + ':' + pad(a % 60);
}

// ns duration -> "1d 2h 3m 4s" (largest units first, sub-second shown as ms)
function formatDuration(ns) {
  if (ns === 0n) return '0s';
  let rest = ns < 0n ? -ns : ns;
  const parts = [];
  for (const u of ['d', 'h', 'm', 's', 'ms']) {
    const q = rest / UNIT_NS[u];
    if (q > 0n) { parts.push(`${q}${u}`); rest -= q * UNIT_NS[u]; }
  }
  if (!parts.length) parts.push(`${rest}ns`);
  return (ns < 0n ? '-' : '') + parts.join(' ');
}

// Human relative phrase using the single largest unit, e.g. "3 hours ago".
function formatRelative(ns, now) {
  const diff = ns - now;
  const abs = diff < 0n ? -diff : diff;
  if (abs < NS.s) return 'just now';
  const steps = [['year', 365n * UNIT_NS.d], ['month', 30n * UNIT_NS.d], ['week', UNIT_NS.w],
    ['day', UNIT_NS.d], ['hour', UNIT_NS.h], ['minute', UNIT_NS.m], ['second', NS.s]];
  const [name, size] = steps.find(([, sz]) => abs >= sz);
  const n = abs / size;
  const phrase = `${n} ${name}${n === 1n ? '' : 's'}`;
  return diff < 0n ? `${phrase} ago` : `in ${phrase}`;
}

function convert(input, opts = {}) {
  const now = opts.now ?? BigInt(Date.now()) * NS.ms;
  const ns = parseTime(input, { ...opts, now });
  const res = {
    input: String(input),
    s: floorDiv(ns, NS.s).toString(),
    ms: floorDiv(ns, NS.ms).toString(),
    us: floorDiv(ns, NS.us).toString(),
    ns: ns.toString(),
    utc: formatIso(ns, 0),
    relative: formatRelative(ns, now),
  };
  if (opts.offset !== undefined && opts.offset !== 0) res.local = formatIso(ns, opts.offset);
  return res;
}

function diff(a, b, opts = {}) {
  const now = opts.now ?? BigInt(Date.now()) * NS.ms;
  const d = parseTime(b, { ...opts, now }) - parseTime(a, { ...opts, now });
  return { from: String(a), to: String(b), ns: d.toString(), s: floorDiv(d, NS.s).toString(), human: formatDuration(d) };
}

const HELP = `usage: epoch.js [options] <time> [time ...]
       epoch.js --diff <from> <to>
time: epoch integer (unit auto-detected), ISO 8601, now, now-3h, +1d12h
options:
  --unit s|ms|us|ns   force unit for bare numbers
  --tz +08:00         also show time at this UTC offset
  --diff              print duration between two times
  --json              JSON output
exit codes: 0 ok, 1 parse error, 2 usage error`;

function main(argv, out = console.log, err = console.error) {
  const opts = {}; const args = []; let json = false; let isDiff = false;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '-h' || a === '--help') { out(HELP); return 0; }
    else if (a === '--json') json = true;
    else if (a === '--diff') isDiff = true;
    else if (a === '--unit' || a === '--tz') {
      const v = argv[++i];
      if (v === undefined) { err(`${a} needs a value`); return 2; }
      try {
        if (a === '--unit') { if (!NS[v]) throw new Error(`invalid unit: ${v}`); opts.unit = v; }
        else opts.offset = parseOffset(v);
      } catch (e) { err(e.message); return 2; }
    } else args.push(a);
  }
  if (!args.length) args.push('now');
  if (isDiff && args.length !== 2) { err('--diff needs exactly two times'); return 2; }
  try {
    const results = isDiff ? [diff(args[0], args[1], opts)] : args.map((a) => convert(a, opts));
    if (json) { out(JSON.stringify(isDiff ? results[0] : results, null, 2)); return 0; }
    for (const r of results) {
      if (isDiff) { out(`${r.human}  (${r.s} s, ${r.ns} ns)`); continue; }
      out(`${r.input}`);
      for (const k of ['utc', 'local', 's', 'ms', 'ns', 'relative']) {
        if (r[k] !== undefined) out(`  ${k.padEnd(8)} ${r[k]}`);
      }
    }
    return 0;
  } catch (e) { err(`error: ${e.message}`); return 1; }
}

module.exports = { parseTime, parseDuration, parseOffset, parseIso, formatIso, formatDuration, formatRelative, detectUnit, convert, diff, main };

if (require.main === module) process.exitCode = main(process.argv.slice(2));
