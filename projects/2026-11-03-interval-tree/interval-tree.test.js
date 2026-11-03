'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { IntervalTree, mergeIntervals, gaps, parseIntervals, main } = require('./interval-tree.js');

function brute(list, lo, hi) {
  return list.filter((i) => i.lo <= hi && i.hi >= lo)
    .map(({ lo, hi }) => ({ lo, hi }))
    .sort((a, b) => a.lo - b.lo || a.hi - b.hi);
}

function run(argv, input) {
  const out = [], err = [];
  const code = main(argv, { stdin: () => input, out: (s) => out.push(s), err: (s) => err.push(s) });
  return { code, out: out.join('\n'), err: err.join('\n') };
}

test('stab and overlap basics, closed endpoints', () => {
  const t = new IntervalTree();
  t.insert(1, 5); t.insert(4, 8); t.insert(10, 12);
  assert.deepEqual(t.stab(5), [{ lo: 1, hi: 5 }, { lo: 4, hi: 8 }]);
  assert.deepEqual(t.stab(9), []);
  assert.deepEqual(t.overlapping(8, 10), [{ lo: 4, hi: 8 }, { lo: 10, hi: 12 }]);
});

test('matches brute force on random data and stays shallow', () => {
  const t = new IntervalTree(), list = [];
  let seed = 42; const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
  for (let i = 0; i < 2000; i++) {
    const lo = Math.floor(rnd() * 10000), hi = lo + Math.floor(rnd() * 200);
    list.push({ lo, hi }); t.insert(lo, hi);
  }
  for (let q = 0; q < 200; q++) {
    const lo = Math.floor(rnd() * 10000), hi = lo + Math.floor(rnd() * 300);
    assert.deepEqual(t.overlapping(lo, hi), brute(list, lo, hi));
  }
  assert.equal(t.size, 2000);
  assert.ok(t.height() < 50, `height ${t.height()} too large`);
  // sorted insertion is the classic BST worst case; treap must still balance
  const s = new IntervalTree();
  for (let i = 0; i < 2000; i++) s.insert(i, i + 1);
  assert.ok(s.height() < 50);
});

test('remove keeps augmentation correct, handles duplicates', () => {
  const t = new IntervalTree();
  t.insert(0, 100); t.insert(5, 6); t.insert(5, 6); t.insert(20, 30);
  assert.equal(t.remove(0, 100), true);
  assert.deepEqual(t.stab(50), []);
  assert.equal(t.remove(5, 6), true);
  assert.deepEqual(t.stab(5), [{ lo: 5, hi: 6 }]);
  assert.equal(t.remove(7, 8), false);
  assert.equal(t.size, 2);
  assert.deepEqual(t.toArray(), [{ lo: 5, hi: 6 }, { lo: 20, hi: 30 }]);
});

test('labels are kept and removal can target a label', () => {
  const t = new IntervalTree();
  t.insert(1, 2, 'a'); t.insert(1, 2, 'b');
  assert.equal(t.remove(1, 2, 'b'), true);
  assert.deepEqual(t.toArray(), [{ lo: 1, hi: 2, label: 'a' }]);
});

test('insert rejects bad bounds', () => {
  const t = new IntervalTree();
  assert.throws(() => t.insert(5, 1), RangeError);
  assert.throws(() => t.insert(NaN, 1), TypeError);
});

test('mergeIntervals and adjacency', () => {
  const l = [{ lo: 6, hi: 9 }, { lo: 1, hi: 3 }, { lo: 2, hi: 5 }];
  assert.deepEqual(mergeIntervals(l), [{ lo: 1, hi: 5 }, { lo: 6, hi: 9 }]);
  assert.deepEqual(mergeIntervals(l, { adjacent: true }), [{ lo: 1, hi: 9 }]);
  assert.deepEqual(mergeIntervals([]), []);
});

test('gaps with and without clipping', () => {
  const l = [{ lo: 2, hi: 4 }, { lo: 6, hi: 8 }, { lo: 7, hi: 10 }];
  assert.deepEqual(gaps(l), [{ lo: 4, hi: 6 }]);
  assert.deepEqual(gaps(l, 0, 12), [{ lo: 0, hi: 2 }, { lo: 4, hi: 6 }, { lo: 10, hi: 12 }]);
  assert.deepEqual(gaps(l, 3, 7), [{ lo: 4, hi: 6 }]);
  assert.deepEqual(gaps([], 0, 5), [{ lo: 0, hi: 5 }]);
});

test('parseIntervals formats and errors', () => {
  assert.deepEqual(parseIntervals('1 2\n3-4 x y\n# c\n-5..-1  neg # tail\n'), [
    { lo: 1, hi: 2, label: null }, { lo: 3, hi: 4, label: 'x y' }, { lo: -5, hi: -1, label: 'neg' },
  ]);
  assert.throws(() => parseIntervals('a b'), /line 1/);
  assert.throws(() => parseIntervals('1 2\n9 3'), /line 2: lo > hi/);
});

test('CLI commands and exit codes', () => {
  const data = '9 12 standup\n13 14 lunch\n10 11 review\n';
  let r = run(['stab', '10.5'], data);
  assert.equal(r.code, 0);
  assert.equal(r.out, '[9, 12]  standup\n[10, 11]  review');
  assert.equal(run(['stab', '20'], data).code, 1);
  r = run(['gaps', '8', '18', '--json'], data);
  assert.deepEqual(JSON.parse(r.out), [{ lo: 8, hi: 9 }, { lo: 12, hi: 13 }, { lo: 14, hi: 18 }]);
  r = run(['stats', '--json'], data);
  assert.deepEqual(JSON.parse(r.out).covered, 4);
  assert.equal(run(['overlap', '5'], data).code, 2);
  assert.equal(run(['nope'], data).code, 2);
  assert.equal(run(['stab', '1'], 'garbage').code, 2);
  assert.equal(run([], '').code, 2);
});
