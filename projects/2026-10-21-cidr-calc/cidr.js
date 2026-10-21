#!/usr/bin/env node
'use strict';
// cidr-calc: IPv4 subnet calculator. Standard library only.

const MAX = 2 ** 32;

function parseIp(s) {
  const parts = String(s).trim().split('.');
  if (parts.length !== 4) throw new Error(`invalid IPv4 address: ${s}`);
  let n = 0;
  for (const p of parts) {
    if (!/^\d{1,3}$/.test(p) || (p.length > 1 && p[0] === '0')) throw new Error(`invalid IPv4 address: ${s}`);
    const v = Number(p);
    if (v > 255) throw new Error(`invalid IPv4 address: ${s}`);
    n = n * 256 + v;
  }
  return n;
}

function formatIp(n) {
  return [n >>> 24, (n >>> 16) & 255, (n >>> 8) & 255, n & 255].join('.');
}

function maskOf(prefix) {
  return prefix === 0 ? 0 : (MAX - 2 ** (32 - prefix));
}

// Parse "a.b.c.d/p" (or bare address = /32). strict=true rejects host bits set.
function parseCidr(s, strict = false) {
  const [ipPart, pPart, extra] = String(s).trim().split('/');
  if (extra !== undefined) throw new Error(`invalid CIDR: ${s}`);
  const ip = parseIp(ipPart);
  let prefix = 32;
  if (pPart !== undefined) {
    if (!/^\d{1,2}$/.test(pPart) || Number(pPart) > 32) throw new Error(`invalid prefix length: ${s}`);
    prefix = Number(pPart);
  }
  const size = 2 ** (32 - prefix);
  const network = ip - (ip % size);
  if (strict && network !== ip) throw new Error(`host bits set in ${s} (network is ${formatIp(network)}/${prefix})`);
  return { ip, prefix, network, broadcast: network + size - 1, size };
}

function classify(n) {
  const inR = (c) => { const r = parseCidr(c); return n >= r.network && n <= r.broadcast; };
  if (inR('10.0.0.0/8') || inR('172.16.0.0/12') || inR('192.168.0.0/16')) return 'private (RFC 1918)';
  if (inR('127.0.0.0/8')) return 'loopback';
  if (inR('169.254.0.0/16')) return 'link-local';
  if (inR('100.64.0.0/10')) return 'shared CGNAT (RFC 6598)';
  if (inR('224.0.0.0/4')) return 'multicast';
  if (inR('240.0.0.0/4')) return 'reserved';
  if (inR('0.0.0.0/8')) return 'this network';
  return 'public';
}

function info(s) {
  const c = parseCidr(s);
  let first = c.network, last = c.broadcast, usable = c.size;
  if (c.prefix <= 30) { first += 1; last -= 1; usable -= 2; } // /31 and /32: RFC 3021, no reserved addrs
  const mask = maskOf(c.prefix);
  return {
    cidr: `${formatIp(c.network)}/${c.prefix}`,
    address: formatIp(c.ip),
    netmask: formatIp(mask),
    wildcard: formatIp(MAX - 1 - mask),
    network: formatIp(c.network),
    broadcast: formatIp(c.broadcast),
    firstHost: formatIp(first),
    lastHost: formatIp(last),
    totalAddresses: c.size,
    usableHosts: usable,
    type: classify(c.network),
  };
}

function contains(cidr, target) {
  const outer = parseCidr(cidr);
  const inner = parseCidr(target);
  return inner.network >= outer.network && inner.broadcast <= outer.broadcast;
}

function split(cidr, newPrefix) {
  const c = parseCidr(cidr);
  if (!Number.isInteger(newPrefix) || newPrefix < c.prefix || newPrefix > 32) {
    throw new Error(`new prefix must be between ${c.prefix} and 32`);
  }
  const step = 2 ** (32 - newPrefix);
  const count = c.size / step;
  if (count > 65536) throw new Error(`refusing to list ${count} subnets (max 65536)`);
  const out = [];
  for (let n = c.network; n <= c.broadcast; n += step) out.push(`${formatIp(n)}/${newPrefix}`);
  return out;
}

// Minimal CIDR list exactly covering the inclusive range [start, end].
function rangeToCidrs(start, end) {
  if (start > end) throw new Error('range start is after end');
  const out = [];
  let cur = start;
  while (cur <= end) {
    let size = 1;
    // grow while aligned and still inside the range
    while (size < MAX && cur % (size * 2) === 0 && cur + size * 2 - 1 <= end) size *= 2;
    out.push(`${formatIp(cur)}/${32 - Math.log2(size)}`);
    cur += size;
  }
  return out;
}

// Merge overlapping/adjacent CIDRs or ranges ("a-b") into the minimal CIDR set.
function summarize(items) {
  const ranges = items.map((s) => {
    if (s.includes('-')) {
      const [a, b] = s.split('-');
      const lo = parseIp(a), hi = parseIp(b);
      if (lo > hi) throw new Error(`invalid range: ${s}`);
      return [lo, hi];
    }
    const c = parseCidr(s);
    return [c.network, c.broadcast];
  }).sort((x, y) => x[0] - y[0]);
  const merged = [];
  for (const r of ranges) {
    const last = merged[merged.length - 1];
    if (last && r[0] <= last[1] + 1) last[1] = Math.max(last[1], r[1]);
    else merged.push([r[0], r[1]]);
  }
  return merged.flatMap(([a, b]) => rangeToCidrs(a, b));
}

const USAGE = `usage:
  cidr.js info <cidr>               subnet details (bare IP = /32)
  cidr.js contains <cidr> <ip|cidr> exit 0 if inside, 1 if not
  cidr.js split <cidr> <newPrefix>  list subnets of the given size
  cidr.js summarize <cidr|a-b>...   merge into minimal CIDR list
  add --json for JSON output`;

function main(argv) {
  const json = argv.includes('--json');
  const args = argv.filter((a) => a !== '--json');
  const [cmd, ...rest] = args;
  const print = (v, text) => console.log(json ? JSON.stringify(v, null, 2) : text);
  try {
    if (cmd === 'info' && rest.length === 1) {
      const r = info(rest[0]);
      const w = Math.max(...Object.keys(r).map((k) => k.length));
      print(r, Object.entries(r).map(([k, v]) => `${k.padEnd(w)}  ${v}`).join('\n'));
      return 0;
    }
    if (cmd === 'contains' && rest.length === 2) {
      const yes = contains(rest[0], rest[1]);
      print({ contains: yes }, yes ? `yes: ${rest[1]} is in ${rest[0]}` : `no: ${rest[1]} is not in ${rest[0]}`);
      return yes ? 0 : 1;
    }
    if (cmd === 'split' && rest.length === 2) {
      const r = split(rest[0], Number(rest[1]));
      print(r, r.join('\n'));
      return 0;
    }
    if (cmd === 'summarize' && rest.length >= 1) {
      const r = summarize(rest);
      print(r, r.join('\n'));
      return 0;
    }
    console.error(USAGE);
    return 2;
  } catch (e) {
    console.error(`error: ${e.message}`);
    return 2;
  }
}

module.exports = { parseIp, formatIp, parseCidr, info, contains, split, rangeToCidrs, summarize, main };

if (require.main === module) process.exitCode = main(process.argv.slice(2));
