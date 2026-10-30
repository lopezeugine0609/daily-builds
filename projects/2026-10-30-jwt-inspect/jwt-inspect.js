#!/usr/bin/env node
'use strict';
// jwt-inspect: decode a JWT, report time claims, optionally verify HMAC signatures.
// Standard library only. Never sends the token anywhere.

const crypto = require('node:crypto');
const fs = require('node:fs');

const HMAC = { HS256: 'sha256', HS384: 'sha384', HS512: 'sha512' };

function b64urlDecode(seg) {
  if (!/^[A-Za-z0-9_-]*$/.test(seg)) throw new Error('segment is not base64url');
  if (seg.length % 4 === 1) throw new Error('segment has invalid base64url length');
  return Buffer.from(seg, 'base64url');
}

function b64urlEncode(buf) {
  return Buffer.from(buf).toString('base64url');
}

function parseJsonSegment(seg, name) {
  let text;
  try { text = b64urlDecode(seg).toString('utf8'); }
  catch (e) { throw new Error(`${name}: ${e.message}`); }
  let obj;
  try { obj = JSON.parse(text); }
  catch { throw new Error(`${name}: not valid JSON`); }
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
    throw new Error(`${name}: must be a JSON object`);
  }
  return obj;
}

function decode(token) {
  const t = String(token).trim().replace(/^Bearer\s+/i, '');
  const parts = t.split('.');
  if (parts.length !== 3) throw new Error(`expected 3 dot-separated parts, got ${parts.length}`);
  const header = parseJsonSegment(parts[0], 'header');
  const payload = parseJsonSegment(parts[1], 'payload');
  const signature = b64urlDecode(parts[2]);
  return { header, payload, signature, signingInput: `${parts[0]}.${parts[1]}`, raw: t };
}

function sign(header, payload, secret) {
  const alg = header.alg || 'HS256';
  if (!HMAC[alg]) throw new Error(`sign supports only ${Object.keys(HMAC).join(', ')}`);
  const h = b64urlEncode(JSON.stringify({ ...header, alg }));
  const p = b64urlEncode(JSON.stringify(payload));
  const sig = crypto.createHmac(HMAC[alg], secret).update(`${h}.${p}`).digest();
  return `${h}.${p}.${b64urlEncode(sig)}`;
}

function verify(decoded, secret) {
  const alg = decoded.header.alg;
  if (alg === 'none') return { ok: false, reason: 'alg "none" is unsigned; refusing' };
  if (!HMAC[alg]) return { ok: false, reason: `cannot verify alg ${alg} (only HMAC supported)` };
  const expected = crypto.createHmac(HMAC[alg], secret).update(decoded.signingInput).digest();
  const ok = expected.length === decoded.signature.length &&
    crypto.timingSafeEqual(expected, decoded.signature);
  return { ok, reason: ok ? 'signature valid' : 'signature mismatch' };
}

function fmtDuration(sec) {
  const s = Math.abs(Math.round(sec));
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60), r = s % 60;
  const out = [];
  if (d) out.push(`${d}d`);
  if (h) out.push(`${h}h`);
  if (m) out.push(`${m}m`);
  if (r || !out.length) out.push(`${r}s`);
  return out.join(' ');
}

// Returns { status: 'valid'|'expired'|'not-yet-valid', notes: [...] }
function timeStatus(payload, nowSec, leeway = 0) {
  const notes = [];
  let status = 'valid';
  for (const k of ['iat', 'nbf', 'exp']) {
    if (payload[k] === undefined) continue;
    if (typeof payload[k] !== 'number') { notes.push(`${k}: not a number`); continue; }
    const iso = new Date(payload[k] * 1000).toISOString();
    const diff = payload[k] - nowSec;
    const rel = diff >= 0 ? `in ${fmtDuration(diff)}` : `${fmtDuration(diff)} ago`;
    notes.push(`${k}: ${iso} (${rel})`);
  }
  if (typeof payload.nbf === 'number' && nowSec + leeway < payload.nbf) status = 'not-yet-valid';
  if (typeof payload.exp === 'number' && nowSec - leeway >= payload.exp) status = 'expired';
  if (typeof payload.exp !== 'number') notes.push('warning: no exp claim, token never expires');
  return { status, notes };
}

const USAGE = `usage: jwt-inspect [token|-] [--secret S] [--json] [--now UNIX] [--leeway SEC]
       jwt-inspect sign '<payload-json>' --secret S [--alg HS256|HS384|HS512]
token defaults to stdin when omitted or "-".
exit: 0 ok, 1 expired/not-yet-valid/bad signature, 2 malformed or usage error`;

function parseArgs(argv) {
  const opts = { positional: [], json: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--json') opts.json = true;
    else if (a === '-h' || a === '--help') opts.help = true;
    else if (['--secret', '--now', '--leeway', '--alg'].includes(a)) {
      if (i + 1 >= argv.length) throw new Error(`${a} needs a value`);
      opts[a.slice(2)] = argv[++i];
    } else opts.positional.push(a);
  }
  return opts;
}

function run(argv, io) {
  let opts;
  try { opts = parseArgs(argv); } catch (e) { io.err(e.message + '\n' + USAGE); return 2; }
  if (opts.help) { io.out(USAGE); return 0; }

  if (opts.positional[0] === 'sign') {
    if (!opts.secret || !opts.positional[1]) { io.err(USAGE); return 2; }
    try {
      const payload = JSON.parse(opts.positional[1]);
      io.out(sign({ alg: opts.alg || 'HS256', typ: 'JWT' }, payload, opts.secret));
      return 0;
    } catch (e) { io.err(`error: ${e.message}`); return 2; }
  }

  let token = opts.positional[0];
  if (token === undefined || token === '-') token = io.stdin();
  let d;
  try { d = decode(token); } catch (e) { io.err(`malformed token: ${e.message}`); return 2; }

  const now = opts.now !== undefined ? Number(opts.now) : Math.floor(Date.now() / 1000);
  const leeway = opts.leeway !== undefined ? Number(opts.leeway) : 0;
  if (!Number.isFinite(now) || !Number.isFinite(leeway)) { io.err('--now/--leeway must be numbers'); return 2; }

  const time = timeStatus(d.payload, now, leeway);
  const sig = opts.secret !== undefined ? verify(d, opts.secret) : null;
  if (d.header.alg === 'none') time.notes.push('warning: alg "none" means the token is unsigned');
  const code = time.status !== 'valid' || (sig && !sig.ok) ? 1 : 0;

  if (opts.json) {
    io.out(JSON.stringify({ header: d.header, payload: d.payload, time: time.status,
      signature: sig ? sig.ok : null, notes: time.notes }, null, 2));
    return code;
  }
  io.out('Header:\n' + JSON.stringify(d.header, null, 2));
  io.out('Payload:\n' + JSON.stringify(d.payload, null, 2));
  io.out('Claims:');
  for (const n of time.notes) io.out('  ' + n);
  io.out(`Time status: ${time.status}`);
  io.out(`Signature: ${sig ? sig.reason : 'not checked (pass --secret to verify HMAC)'}`);
  return code;
}

module.exports = { decode, sign, verify, timeStatus, fmtDuration, run };

if (require.main === module) {
  const code = run(process.argv.slice(2), {
    out: (s) => console.log(s),
    err: (s) => console.error(s),
    stdin: () => fs.readFileSync(0, 'utf8'),
  });
  process.exitCode = code;
}
