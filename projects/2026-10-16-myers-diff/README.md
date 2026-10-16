# myers-diff

A from-scratch implementation of **Eugene Myers' O(ND) diff algorithm** (1986) with
`diff -u`-style unified output. Python standard library only. It does not use `difflib`.
The tests use `difflib` only as an independent reference.

## How the algorithm works

Diffing `a` (length N) against `b` (length M) is treated as finding a shortest path
on an edit graph:

- Moving **right** (x+1) deletes `a[x]`.
- Moving **down** (y+1) inserts `b[y]`.
- Moving **diagonally** is free when `a[x] == b[y]`. A run of these is called a *snake*.

Every point lies on a diagonal `k = x - y`. For each edit distance `d = 0, 1, 2, ...`
the algorithm keeps `V[k]`, the furthest-reaching `x` on diagonal `k` using exactly
`d` edits. To extend to diagonal `k`, it steps from whichever neighbour (`k-1` or `k+1`)
reached further. Then it follows the snake as far as possible. The first `d` that
reaches `(N, M)` is the minimum edit distance D. The total cost is O((N+M)·D), so it is
very fast when the files are similar.

A snapshot of `V` is saved for each `d`. Backtracking through these snapshots rebuilds
the actual edit script. The edits are then grouped into hunks that have `-U` lines of
context.

## Usage

```
python myers_diff.py [-U N] [--stat] [--color] OLD NEW     # "-" reads stdin
```

Exit code: `0` = identical, `1` = differences found (same as `diff`).

Example files (`old.txt`, `new.txt` are included):

```
$ python myers_diff.py old.txt new.txt
--- old.txt
+++ new.txt
@@ -1,6 +1,6 @@
 apple
-banana
+blueberry
 cherry
 date
-elderberry
 fig
+grape
```

```
$ python myers_diff.py -U 0 old.txt new.txt
--- old.txt
+++ new.txt
@@ -2 +2 @@
-banana
+blueberry
@@ -5 +4,0 @@
-elderberry
@@ -6,0 +6 @@
+grape
```

```
$ python myers_diff.py --stat old.txt new.txt
2 insertion(s)(+), 2 deletion(s)(-), edit distance 4
```

As a library:

```python
from myers_diff import diff, edit_distance, unified
diff("ABCABBA", "CBABAC")          # [('-', 'A'), ('-', 'B'), (' ', 'C'), ...]
edit_distance("ABCABBA", "CBABAC") # 5  (the example from Myers' paper)
```

## Tests

```
python -m unittest -v
```

The 9 tests cover the following:
- The example from the paper.
- Empty and identical inputs.
- 300 random pairs. Each one checks that the script rebuilds both inputs and that its
  length equals `N + M - 2·LCS`, which proves it is minimal.
- Hunk headers compared against `difflib` at context 0, 1 and 3.
- The CLI's exit codes and `--stat` output.
