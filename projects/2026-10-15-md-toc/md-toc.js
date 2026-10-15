#!/usr/bin/env node
'use strict';
/**
 * md-toc: generate a Markdown table of contents with GitHub-compatible
 * anchor slugs, and optionally inject it between marker comments.
 *
 *   <!-- toc -->
 *   ...generated list...
 *   <!-- tocstop -->
 */
const fs = require('node:fs');

const START = '<!-- toc -->';
const STOP = '<!-- tocstop -->';

/** Strip inline Markdown so the visible heading text remains. */
function plainText(s) {
  return s
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1') // images
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // links
    .replace(/<[^>]+>/g, '') // html tags
    .replace(/`([^`]*)`/g, '$1') // inline code
    .replace(/(\*\*|__)(.+?)\1/g, '$2') // bold
    .replace(/(\*|_)(.+?)\1/g, '$2') // italic
    .replace(/~~(.+?)~~/g, '$1') // strike
    .trim();
}

/** GitHub-style slug: lowercase, drop punctuation, spaces -> hyphens. */
function slugify(text) {
  return plainText(text)
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\p{M}\s_-]/gu, '')
    .replace(/ /g, '-');
}

/** Extract ATX (#) and setext (=== / ---) headings, ignoring fenced code. */
function parseHeadings(md) {
  const lines = md.split(/\r?\n/);
  const out = [];
  let fence = null;
  let inToc = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const f = line.match(/^ {0,3}(`{3,}|~{3,})/);
    if (f) {
      if (!fence) fence = f[1];
      else if (f[1][0] === fence[0] && f[1].length >= fence.length) fence = null;
      continue;
    }
    if (fence) continue;
    if (line.trim() === START) { inToc = true; continue; }
    if (line.trim() === STOP) { inToc = false; continue; }
    if (inToc) continue;

    const atx = line.match(/^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$/);
    if (atx) {
      out.push({ level: atx[1].length, text: atx[2].trim(), line: i + 1 });
      continue;
    }
    const next = lines[i + 1];
    if (next !== undefined && line.trim() !== '' && !/^\s*[-*+>|]/.test(line)) {
      if (/^ {0,3}=+\s*$/.test(next)) {
        out.push({ level: 1, text: line.trim(), line: i + 1 });
        i++;
      } else if (/^ {0,3}-+\s*$/.test(next)) {
        out.push({ level: 2, text: line.trim(), line: i + 1 });
        i++;
      }
    }
  }
  return out;
}

/** Build the TOC list. Slugs are deduplicated across ALL headings, like GitHub. */
function buildToc(md, opts = {}) {
  const min = opts.min ?? 1;
  const max = opts.max ?? 6;
  const bullet = opts.bullet ?? '-';
  const indent = opts.indent ?? 2;
  const seen = new Map();
  const items = [];
  for (const h of parseHeadings(md)) {
    const base = slugify(h.text);
    const n = seen.get(base) ?? 0;
    seen.set(base, n + 1);
    const slug = n === 0 ? base : `${base}-${n}`;
    if (h.level < min || h.level > max) continue;
    items.push({ ...h, slug });
  }
  if (items.length === 0) return '';
  const top = Math.min(...items.map((h) => h.level));
  return items
    .map((h) => {
      const pad = ' '.repeat((h.level - top) * indent);
      const label = plainText(h.text).replace(/([[\]])/g, '\\$1');
      return `${pad}${bullet} [${label}](#${h.slug})`;
    })
    .join('\n');
}

/** Replace content between markers. Throws if markers are missing. */
function injectToc(md, opts = {}) {
  const eol = md.includes('\r\n') ? '\r\n' : '\n';
  const s = md.indexOf(START);
  const e = md.indexOf(STOP);
  if (s === -1 || e === -1 || e < s) {
    throw new Error(`markers not found: add "${START}" and "${STOP}" lines`);
  }
  const toc = buildToc(md, opts).replace(/\n/g, eol);
  const middle = toc ? `${eol}${eol}${toc}${eol}${eol}` : eol;
  return md.slice(0, s + START.length) + middle + md.slice(e);
}

function parseArgs(argv) {
  const a = { files: [], min: 1, max: 6, write: false, check: false };
  for (let i = 0; i < argv.length; i++) {
    const x = argv[i];
    if (x === '--min') a.min = Number(argv[++i]);
    else if (x === '--max') a.max = Number(argv[++i]);
    else if (x === '-w' || x === '--write') a.write = true;
    else if (x === '--check') a.check = true;
    else if (x === '-h' || x === '--help') a.help = true;
    else if (x.startsWith('-')) throw new Error(`unknown option: ${x}`);
    else a.files.push(x);
  }
  for (const k of ['min', 'max']) {
    if (!Number.isInteger(a[k]) || a[k] < 1 || a[k] > 6) throw new Error(`--${k} must be 1-6`);
  }
  if (a.min > a.max) throw new Error('--min must be <= --max');
  return a;
}

const USAGE = `usage: md-toc [options] <file.md ...>
  (no flag)     print the TOC to stdout
  -w, --write   inject TOC between ${START} and ${STOP} in place
  --check       exit 1 if a file's TOC is missing or stale (for CI)
  --min N       smallest heading level to include (default 1)
  --max N       largest heading level to include (default 6)`;

function main(argv) {
  let a;
  try { a = parseArgs(argv); } catch (err) {
    console.error(`md-toc: ${err.message}\n${USAGE}`);
    return 2;
  }
  if (a.help || a.files.length === 0) {
    console.log(USAGE);
    return a.help ? 0 : 2;
  }
  let code = 0;
  for (const file of a.files) {
    let md;
    try { md = fs.readFileSync(file, 'utf8'); } catch (err) {
      console.error(`md-toc: cannot read ${file}: ${err.code}`);
      code = 2;
      continue;
    }
    if (!a.write && !a.check) {
      console.log(buildToc(md, a));
      continue;
    }
    let updated;
    try { updated = injectToc(md, a); } catch (err) {
      console.error(`md-toc: ${file}: ${err.message}`);
      code = Math.max(code, a.check ? 1 : 2);
      continue;
    }
    if (a.check) {
      if (updated !== md) { console.error(`${file}: TOC is out of date`); code = Math.max(code, 1); }
      else console.log(`${file}: OK`);
    } else if (updated !== md) {
      fs.writeFileSync(file, updated);
      console.log(`${file}: updated`);
    } else {
      console.log(`${file}: unchanged`);
    }
  }
  return code;
}

module.exports = { slugify, plainText, parseHeadings, buildToc, injectToc, parseArgs, main };

if (require.main === module) process.exitCode = main(process.argv.slice(2));
