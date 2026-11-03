# interval-tree

Augmented interval tree in plain Node.js (no dependencies), plus a CLI for everyday range questions: what's happening at time X, what overlaps a window, the union of all ranges, and the uncovered gaps.

## How it works

- Each node holds a closed interval `[lo, hi]`, ordered by `(lo, hi, insertion id)` so duplicates are allowed.
- **Augmentation:** each node also stores `max`, the largest `hi` anywhere in its subtree. An overlap query for `[qlo, qhi]` skips a whole subtree when `max < qlo`. It also stops going right once a node's `lo > qhi`, because everything to the right starts later. Result: `O(log n + k)` for `k` matches.
- **Balancing:** treap. Each node gets a random priority; rotations after insert keep heap order on priority, so expected depth is `O(log n)` even for sorted input. Each rotation recomputes `max` for the two nodes it moves.
- **Delete:** find the node, replace it with the priority-merge of its two children, and refresh `max` on the way back up.
- `merge` and `gaps` sort, then sweep in one pass (`O(n log n)`).

## Library

```js
const { IntervalTree, mergeIntervals, gaps } = require('./interval-tree.js');
const t = new IntervalTree();
t.insert(1, 5, 'a'); t.insert(4, 8); t.insert(10, 12);
t.stab(5);            // [{lo:1,hi:5,label:'a'}, {lo:4,hi:8}]
t.overlapping(8, 10); // [{lo:4,hi:8}, {lo:10,hi:12}]
t.remove(4, 8);       // true
[...t];               // in-order iteration
```

## CLI

```
usage: interval-tree.js <command> [args] [--file F] [--json]
  stab <point>           intervals containing point
  overlap <lo> <hi>      intervals overlapping [lo, hi]
  merge [--adjacent]     union of all intervals (--adjacent joins 1-5 and 6-9)
  gaps [<from> <to>]     uncovered ranges, optionally clipped
  stats                  count, span, tree height
```

The CLI reads intervals from `--file` or stdin, one per line: `lo hi [label]`, `lo-hi`, or `lo..hi`. A `#` starts a comment. Exit codes: 0 = results, 1 = no results, 2 = usage or input error.

`meetings.txt` (included):

```
# meetings (24h, decimal hours)
9 10.5 standup
10 12 design review
13 14 lunch
13.5 15 1:1 with Ana
16-17 deploy window
```

Real output:

```
$ node interval-tree.js stab 10.25 --file meetings.txt
[9, 10.5]  standup
[10, 12]  design review
(exit 0)
$ node interval-tree.js overlap 12 13.75 --file meetings.txt
[10, 12]  design review
[13, 14]  lunch
[13.5, 15]  1:1 with Ana
(exit 0)
$ node interval-tree.js merge --file meetings.txt
[9, 12]
[13, 15]
[16, 17]
(exit 0)
$ node interval-tree.js gaps 8 18 --file meetings.txt
[8, 9]
[12, 13]
[15, 16]
[17, 18]
(exit 0)
$ node interval-tree.js stats --file meetings.txt
count       5
min         9
max         17
covered     6
mergedCount 3
height      4
(exit 0)
$ node interval-tree.js stab 20 --file meetings.txt
(exit 1)
$ node interval-tree.js gaps 8 18 --json --file meetings.txt
[{"lo":8,"hi":9},{"lo":12,"hi":13},{"lo":15,"hi":16},{"lo":17,"hi":18}]
```

`height` depends on the random priorities, so it can vary between runs.

## Tests

```
node --test
```

There are 9 tests. They cover closed-endpoint semantics, 200 random queries checked against brute force on 2000 intervals, treap depth on sorted input, removal with duplicates and labels, merge/adjacency, clipped gaps, the parser, and CLI exit codes.
