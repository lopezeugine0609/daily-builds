#!/usr/bin/env node
'use strict';
/**
 * interval-tree: augmented interval tree (treap-balanced) with a CLI.
 *
 * Each node stores a closed interval [lo, hi], keyed by (lo, hi, id), plus
 * `max` = largest `hi` in its subtree. That one augmentation lets a query
 * skip any subtree whose max < query.lo, giving O(log n + k) overlap search.
 * Balancing uses a treap: random priorities + rotations keep expected depth
 * O(log n) without the bookkeeping of red-black trees.
 */

const fs = require('node:fs');

class Node {
  constructor(lo, hi, label, id) {
    this.lo = lo; this.hi = hi; this.label = label; this.id = id;
    this.max = hi; this.prio = Math.random();
    this.left = null; this.right = null;
  }
}

function cmp(a, b) {
  return a.lo - b.lo || a.hi - b.hi || a.id - b.id;
}

function fix(n) {
  n.max = Math.max(n.hi, n.left ? n.left.max : -Infinity, n.right ? n.right.max : -Infinity);
  return n;
}

function rotRight(n) { const l = n.left; n.left = l.right; l.right = fix(n); return fix(l); }
function rotLeft(n) { const r = n.right; n.right = r.left; r.left = fix(n); return fix(r); }

class IntervalTree {
  constructor() { this.root = null; this.size = 0; this._id = 0; }

  insert(lo, hi, label = null) {
    if (!Number.isFinite(lo) || !Number.isFinite(hi)) throw new TypeError('bounds must be finite numbers');
    if (lo > hi) throw new RangeError(`invalid interval [${lo}, ${hi}]: lo > hi`);
    const node = new Node(lo, hi, label, this._id++);
    const ins = (n) => {
      if (!n) return node;
      if (cmp(node, n) < 0) {
        n.left = ins(n.left);
        if (n.left.prio > n.prio) return rotRight(n);
      } else {
        n.right = ins(n.right);
        if (n.right.prio > n.prio) return rotLeft(n);
      }
      return fix(n);
    };
    this.root = ins(this.root);
    this.size++;
    return node.id;
  }

  /** Remove first interval equal to [lo, hi] (and label, if given). Returns true if removed. */
  remove(lo, hi, label) {
    let removed = false;
    const del = (n) => {
      if (!n) return null;
      if (!removed && n.lo === lo && n.hi === hi && (label === undefined || n.label === label)) {
        removed = true;
        return merge(n.left, n.right);
      }
      if (lo < n.lo || (lo === n.lo && hi < n.hi)) n.left = del(n.left);
      else if (lo > n.lo || hi > n.hi) n.right = del(n.right);
      else { n.left = del(n.left); if (!removed) n.right = del(n.right); }
      return fix(n);
    };
    const merge = (a, b) => {
      if (!a) return b;
      if (!b) return a;
      if (a.prio > b.prio) { a.right = merge(a.right, b); return fix(a); }
      b.left = merge(a, b.left); return fix(b);
    };
    this.root = del(this.root);
    if (removed) this.size--;
    return removed;
  }

  /** All intervals overlapping closed range [lo, hi], sorted by (lo, hi). */
  overlapping(lo, hi = lo) {
    const out = [];
    const walk = (n) => {
      if (!n || n.max < lo) return;          // nothing in this subtree reaches lo
      walk(n.left);
      if (n.lo > hi) return;                  // this and everything right start after hi
      if (n.hi >= lo) out.push(view(n));
      walk(n.right);
    };
    walk(this.root);
    return out;
  }

  stab(point) { return this.overlapping(point, point); }

  *[Symbol.iterator]() {
    const stack = []; let n = this.root;
    while (stack.length || n) {
      while (n) { stack.push(n); n = n.left; }
      n = stack.pop(); yield view(n); n = n.right;
    }
  }

  toArray() { return [...this]; }

  height() {
    const h = (n) => (n ? 1 + Math.max(h(n.left), h(n.right)) : 0);
    return h(this.root);
  }
}

function view(n) { return n.label == null ? { lo: n.lo, hi: n.hi } : { lo: n.lo, hi: n.hi, label: n.label }; }

/** Merge overlapping (or touching, when adjacent=true for integers) intervals. Input need not be sorted. */
function mergeIntervals(list, { adjacent = false } = {}) {
  const s = list.map(({ lo, hi }) => ({ lo, hi })).sort((a, b) => a.lo - b.lo || a.hi - b.hi);
  const out = [];
  for (const iv of s) {
    const last = out[out.length - 1];
    if (last && iv.lo <= last.hi + (adjacent ? 1 : 0)) last.hi = Math.max(last.hi, iv.hi);
    else out.push({ ...iv });
  }
  return out;
}

/** Uncovered open gaps between merged intervals, optionally clipped to [from, to]. */
function gaps(list, from = -Infinity, to = Infinity) {
  const out = [];
  let cursor = from;
  for (const { lo, hi } of mergeIntervals(list)) {
    if (hi < from) continue;
    if (lo > to) break;
    if (lo > cursor) out.push({ lo: cursor, hi: lo });
    cursor = Math.max(cursor, hi);
  }
  if (cursor < to) out.push({ lo: cursor, hi: to });
  return out.filter((g) => Number.isFinite(g.lo) && Number.isFinite(g.hi));
}

/** Parse lines like "10 20", "10-20", "10..20 label text". '#' starts a comment. */
function parseIntervals(text) {
  const res = [];
  text.split(/\r?\n/).forEach((raw, i) => {
    const line = raw.replace(/#.*/, '').trim();
    if (!line) return;
    const m = line.match(/^(-?\d+(?:\.\d+)?)\s*(?:\.\.|-|,|\s)\s*(-?\d+(?:\.\d+)?)(?:\s+(.*))?$/);
    if (!m) throw new SyntaxError(`line ${i + 1}: cannot parse "${raw.trim()}"`);
    const lo = Number(m[1]), hi = Number(m[2]);
    if (lo > hi) throw new RangeError(`line ${i + 1}: lo > hi in "${raw.trim()}"`);
    res.push({ lo, hi, label: m[3] ? m[3].trim() : null });
  });
  return res;
}

function fmt(iv) { return `[${iv.lo}, ${iv.hi}]${iv.label ? '  ' + iv.label : ''}`; }

const USAGE = `usage: interval-tree.js <command> [args] [--file F] [--json]
  stab <point>           intervals containing point
  overlap <lo> <hi>      intervals overlapping [lo, hi]
  merge [--adjacent]     union of all intervals (--adjacent joins 1-5 and 6-9)
  gaps [<from> <to>]     uncovered ranges, optionally clipped
  stats                  count, span, tree height
Intervals are read from --file or stdin, one per line: "lo hi [label]",
"lo-hi", or "lo..hi". Exit: 0 = results, 1 = no results, 2 = usage/input error.`;

function main(argv, io = { stdin: () => fs.readFileSync(0, 'utf8'), out: console.log, err: console.error }) {
  const args = [...argv];
  const flag = (f) => { const i = args.indexOf(f); if (i < 0) return false; args.splice(i, 1); return true; };
  const opt = (f) => { const i = args.indexOf(f); if (i < 0) return null; const v = args[i + 1]; args.splice(i, 2); return v; };
  if (flag('-h') || flag('--help') || !args.length) { io.out(USAGE); return args.length ? 0 : 2; }
  const json = flag('--json'), adjacent = flag('--adjacent'), file = opt('--file');
  const [cmd, ...rest] = args;
  const nums = rest.map(Number);
  if (nums.some((x) => Number.isNaN(x))) { io.err(`error: non-numeric argument in "${rest.join(' ')}"`); return 2; }

  let items;
  try { items = parseIntervals(file ? fs.readFileSync(file, 'utf8') : io.stdin()); }
  catch (e) { io.err(`error: ${e.message}`); return 2; }
  const tree = new IntervalTree();
  for (const { lo, hi, label } of items) tree.insert(lo, hi, label);

  let result;
  switch (cmd) {
    case 'stab':
      if (nums.length !== 1) { io.err('error: stab needs <point>'); return 2; }
      result = tree.stab(nums[0]); break;
    case 'overlap':
      if (nums.length !== 2 || nums[0] > nums[1]) { io.err('error: overlap needs <lo> <hi> with lo <= hi'); return 2; }
      result = tree.overlapping(nums[0], nums[1]); break;
    case 'merge': result = mergeIntervals(items, { adjacent }); break;
    case 'gaps':
      if (nums.length !== 0 && nums.length !== 2) { io.err('error: gaps takes no args or <from> <to>'); return 2; }
      result = nums.length ? gaps(items, nums[0], nums[1]) : gaps(items); break;
    case 'stats': {
      const merged = mergeIntervals(items);
      const s = {
        count: tree.size,
        min: items.length ? Math.min(...items.map((i) => i.lo)) : null,
        max: items.length ? Math.max(...items.map((i) => i.hi)) : null,
        covered: merged.reduce((a, i) => a + (i.hi - i.lo), 0),
        mergedCount: merged.length,
        height: tree.height(),
      };
      if (json) io.out(JSON.stringify(s));
      else for (const [k, v] of Object.entries(s)) io.out(`${k.padEnd(12)}${v}`);
      return tree.size ? 0 : 1;
    }
    default: io.err(`error: unknown command "${cmd}"\n${USAGE}`); return 2;
  }
  if (json) io.out(JSON.stringify(result));
  else result.forEach((iv) => io.out(fmt(iv)));
  return result.length ? 0 : 1;
}

module.exports = { IntervalTree, mergeIntervals, gaps, parseIntervals, main };

if (require.main === module) process.exitCode = main(process.argv.slice(2));
