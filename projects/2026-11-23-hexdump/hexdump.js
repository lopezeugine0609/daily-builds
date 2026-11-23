#!/usr/bin/env node
'use strict';
// hexdump: xxd-style hex dumper with reverse mode (hex -> bytes), plain/C-array output,
// skip/length windows, grouping, and squeezing of repeated lines. Standard library only.

const fs = require('node:fs');

function printable(b) {
  return b >= 0x20 && b <= 0x7e ? String.fromCharCode(b) : '.';
}

/**
 * Render a Buffer as xxd-style lines.
 * opts: cols (bytes per line), group (bytes per group), offset (display base offset),
 *       upper (uppercase hex), squeeze (collapse identical consecutive lines into '*').
 */
function dump(buf, opts = {}) {
  const cols = opts.cols ?? 16;
  const group = opts.group ?? 2;
  const base = opts.offset ?? 0;
  const upper = !!opts.upper;
  const squeeze = !!opts.squeeze;
  if (!Number.isInteger(cols) || cols < 1 || cols > 256) throw new RangeError('cols must be 1..256');
  if (!Number.isInteger(group) || group < 0) throw new RangeError('group must be >= 0');

  const hexWidth = cols * 2 + (group > 0 ? Math.ceil(cols / group) - 1 : 0);
  const lines = [];
  let prev = null;
  let starred = false;
  for (let i = 0; i < buf.length; i += cols) {
    const chunk = buf.subarray(i, i + cols);
    const full = chunk.length === cols;
    if (squeeze && full && prev && chunk.equals(prev) && i + cols < buf.length) {
      if (!starred) { lines.push('*'); starred = true; }
      continue;
    }
    starred = false;
    prev = full ? Buffer.from(chunk) : null;
    let hex = '';
    for (let j = 0; j < chunk.length; j++) {
      if (group > 0 && j > 0 && j % group === 0) hex += ' ';
      hex += chunk[j].toString(16).padStart(2, '0');
    }
    if (upper) hex = hex.toUpperCase();
    let off = (base + i).toString(16).padStart(8, '0');
    if (upper) off = off.toUpperCase();
    const ascii = Array.from(chunk, printable).join('');
    lines.push(`${off}: ${hex.padEnd(hexWidth)}  ${ascii}`);
  }
  return lines;
}

/** Plain hex: one continuous hex string wrapped at `cols` bytes per line (xxd -p). */
function plain(buf, cols = 30) {
  const hex = buf.toString('hex');
  const out = [];
  for (let i = 0; i < hex.length; i += cols * 2) out.push(hex.slice(i, i + cols * 2));
  return out;
}

/** C array include (xxd -i). */
function cArray(buf, name = 'data', cols = 12) {
  const ident = name.replace(/[^A-Za-z0-9_]/g, '_').replace(/^(\d)/, '_$1');
  const out = [`unsigned char ${ident}[] = {`];
  for (let i = 0; i < buf.length; i += cols) {
    const row = Array.from(buf.subarray(i, i + cols), (b) => '0x' + b.toString(16).padStart(2, '0'));
    out.push('  ' + row.join(', ') + (i + cols < buf.length ? ',' : ''));
  }
  out.push('};', `unsigned int ${ident}_len = ${buf.length};`);
  return out;
}

/**
 * Reverse a dump back into bytes. Accepts xxd-style lines ("off: hex  ascii") or plain hex.
 * In xxd-style input the offset is honored (gaps zero-filled); '*' lines repeat the previous line
 * until the next offset. Plain hex ignores whitespace.
 */
function reverse(text, { plainHex = false } = {}) {
  if (plainHex) {
    const hex = text.replace(/\s+/g, '');
    if (!/^[0-9a-fA-F]*$/.test(hex)) throw new SyntaxError('invalid hex character in plain input');
    if (hex.length % 2) throw new SyntaxError('odd number of hex digits');
    return Buffer.from(hex, 'hex');
  }
  const chunks = []; // {off, bytes}
  let pendingStar = false;
  const lines = text.split(/\r?\n/);
  for (let n = 0; n < lines.length; n++) {
    const line = lines[n];
    if (!line.trim()) continue;
    if (line.trim() === '*') { pendingStar = true; continue; }
    const m = /^\s*([0-9a-fA-F]+):\s?(.*)$/.exec(line);
    if (!m) throw new SyntaxError(`line ${n + 1}: expected "offset: hex"`);
    const off = parseInt(m[1], 16);
    // Hex field ends at the double-space before ASCII column (or end of line).
    const hexField = m[2].split('  ')[0];
    const tokens = hexField.trim() ? hexField.trim().split(/\s+/) : [];
    let hex = '';
    for (const t of tokens) {
      if (!/^[0-9a-fA-F]+$/.test(t) || t.length % 2) throw new SyntaxError(`line ${n + 1}: bad hex group "${t}"`);
      hex += t;
    }
    const bytes = Buffer.from(hex, 'hex');
    if (pendingStar && chunks.length) {
      const last = chunks[chunks.length - 1];
      let pos = last.off + last.bytes.length;
      while (pos + last.bytes.length <= off) {
        chunks.push({ off: pos, bytes: last.bytes });
        pos += last.bytes.length;
      }
    }
    pendingStar = false;
    chunks.push({ off, bytes });
  }
  if (!chunks.length) return Buffer.alloc(0);
  const start = Math.min(...chunks.map((c) => c.off));
  const end = Math.max(...chunks.map((c) => c.off + c.bytes.length));
  const out = Buffer.alloc(end - start);
  for (const c of chunks) c.bytes.copy(out, c.off - start);
  return out;
}

function parseNum(s, flag) {
  const v = /^0x/i.test(s) ? parseInt(s, 16) : Number(s);
  if (!Number.isInteger(v) || v < 0) throw new RangeError(`${flag}: expected non-negative integer, got "${s}"`);
  return v;
}

const USAGE = `usage: hexdump.js [options] [file|-]
  -c N       bytes per line (default 16; 30 with -p, 12 with -i)
  -g N       bytes per group (default 2; 0 = no spaces)
  -s N       skip N bytes from start (decimal or 0x hex)
  -l N       stop after N bytes
  -u         uppercase hex
  -a         squeeze identical lines into '*'
  -p         plain hex output
  -i         C array output (name from file or 'stdin')
  -r         reverse: hex dump -> binary on stdout (with -p: plain hex input)
  -h         help
exit codes: 0 ok, 1 input/parse error, 2 usage error`;

function main(argv, io = { stdout: process.stdout, stderr: process.stderr, readStdin: () => fs.readFileSync(0) }) {
  const o = { cols: null, group: 2, skip: 0, len: null, upper: false, squeeze: false, mode: 'dump', rev: false, file: '-' };
  try {
    for (let i = 0; i < argv.length; i++) {
      const a = argv[i];
      const next = () => { if (i + 1 >= argv.length) throw new RangeError(`${a} needs a value`); return argv[++i]; };
      switch (a) {
        case '-c': o.cols = parseNum(next(), a); break;
        case '-g': o.group = parseNum(next(), a); break;
        case '-s': o.skip = parseNum(next(), a); break;
        case '-l': o.len = parseNum(next(), a); break;
        case '-u': o.upper = true; break;
        case '-a': o.squeeze = true; break;
        case '-p': o.mode = 'plain'; break;
        case '-i': o.mode = 'c'; break;
        case '-r': o.rev = true; break;
        case '-h': case '--help': io.stdout.write(USAGE + '\n'); return 0;
        default:
          if (a.startsWith('-') && a !== '-') throw new RangeError(`unknown option ${a}`);
          o.file = a;
      }
    }
  } catch (e) {
    io.stderr.write(`hexdump: ${e.message}\n${USAGE}\n`);
    return 2;
  }
  try {
    let buf = o.file === '-' ? io.readStdin() : fs.readFileSync(o.file);
    if (o.rev) {
      io.stdout.write(reverse(buf.toString('utf8'), { plainHex: o.mode === 'plain' }));
      return 0;
    }
    buf = buf.subarray(o.skip, o.len == null ? undefined : o.skip + o.len);
    let lines;
    if (o.mode === 'plain') lines = plain(buf, o.cols ?? 30);
    else if (o.mode === 'c') {
      const name = o.file === '-' ? 'stdin' : require('node:path').basename(o.file);
      lines = cArray(buf, name, o.cols ?? 12);
    } else lines = dump(buf, { cols: o.cols ?? 16, group: o.group, offset: o.skip, upper: o.upper, squeeze: o.squeeze });
    if (lines.length) io.stdout.write(lines.join('\n') + '\n');
    return 0;
  } catch (e) {
    io.stderr.write(`hexdump: ${e.message}\n`);
    return 1;
  }
}

module.exports = { dump, plain, cArray, reverse, main };

if (require.main === module) process.exitCode = main(process.argv.slice(2));
