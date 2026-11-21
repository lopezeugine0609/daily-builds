# skip-list

A skip list ordered map in pure Python (standard library only), with
**indexable** forward pointers so rank and position lookups are O(log n)
expected, not O(n).

## How it works

- Level 0 is a sorted singly linked list of every key.
- Each new node gets a random height: it is promoted to level i+1 with
  probability `p` (default 0.5). Higher levels act as express lanes.
- Search starts at the head's top level, moves right while the next key is
  smaller than the target, and drops one level when it would overshoot.
  Expected cost: O(log n) for search, insert and delete.
- Every forward pointer also stores a **width**: how many level-0 nodes it
  jumps over. Summing widths along the search path gives a key's rank, and
  walking by widths finds the k-th element. Inserts split a width in two;
  deletes merge two widths back into one.
- `check()` re-derives every width from scratch and asserts the invariants.

## API

```python
from skiplist import SkipList

sl = SkipList(seed=1)          # seed makes tower heights reproducible
sl[10] = "a"; sl[30] = "c"; sl[20] = "b"
sl[20]                         # 'b'
20 in sl, len(sl)              # True, 3
list(sl)                       # [10, 20, 30]
sl.rank(25)                    # 2   (keys < 25)
sl.at(-1)                      # (30, 'c')
list(sl.range(15, 30))         # [(20, 'b')]   lo <= key < hi
sl.floor(25), sl.ceiling(25)   # 20, 30
sl.pop(10); del sl[30]
sl.check()                     # True or AssertionError
```

Also: `get`, `items`, `levels()` (ASCII picture of the towers). Constructor
accepts a dict or an iterable of `(key, value)` pairs, plus `max_level`, `p`,
`seed`.

## CLI demo

Counts the keys, draws the towers, and prints the median via `at()`.
Keys that all look like integers are compared as integers.

```
$ python skiplist.py --seed 7 42 7 19 7 88 3 56 23 61 11
9 unique keys, 6 levels
L5: -- -- -- -- -- -- -- -- 88
L4: -- -- -- -- -- -- -- -- 88
L3: -- -- -- -- -- -- -- -- 88
L2:  3 -- -- 19 -- 42 -- -- 88
L1:  3  7 11 19 -- 42 -- 61 88
L0:  3  7 11 19 23 42 56 61 88
counts: 3=1, 7=2, 11=1, 19=1, 23=1, 42=1, 56=1, 61=1, 88=1
median: 23

$ python skiplist.py --seed 3 pear apple fig kiwi apple date
5 unique keys, 3 levels
L2: -----  date -----  kiwi -----
L1: apple  date -----  kiwi  pear
L0: apple  date   fig  kiwi  pear
counts: apple=2, date=1, fig=1, kiwi=1, pear=1
median: fig
```

## Tests

```
$ python -m unittest -v
...
Ran 8 tests in 0.007s

OK
```

The tests include a 3000-step randomized insert/delete run checked against a
`dict`. It verifies `check()` invariants, `at()` and `rank()` for every key.
