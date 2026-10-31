# nonogram-solver

Solver for nonogram puzzles (also called Picross or Griddlers). It reads row and column clues, prints the picture, and reports whether the solution is unique. Uses the Python standard library only.

## How it works

1. **Line solver (DP).** For one row or column, a memoized recursion `fits(i, j)` answers one question: can cells `i..` hold clue blocks `j..`, given the cells already known? A second pass visits only the reachable states. It records which cells can be filled and which can be empty across *every* valid placement. A cell with only one possible value gets fixed. Cost is O(n·k) states per line, not one per placement.
2. **Propagation.** Rows and columns are re-solved until nothing changes. Only lines touched by a change are re-queued.
3. **Search.** If unknown cells remain, the solver guesses one cell (filled first, then empty), copies the grid, and propagates again. It stops after `--limit` solutions (default 2). Two solutions are enough to prove the puzzle is not unique.

The tests check the line solver against a brute-force enumerator on 400 random lines. They also check that random grids solve back to clue-consistent pictures.

## Puzzle format

```
# comment
rows
2 2        <- one clue line per row, top to bottom
7
0          <- empty row (blank clue)
cols
2          <- one clue line per column, left to right
...
```

Commas are allowed (`1, 1`). The `rows:` and `columns` spellings also work.

## Usage

```
python nonogram.py PUZZLE [--json] [--limit N] [--fill CH] [--empty CH]
python nonogram.py -            # read from stdin
```

Exit codes: `0` unique solution, `1` no solution, `2` bad input, `3` multiple solutions (all found up to `--limit` are printed).

Solved by line logic alone (stdout, then stderr):

```
$ python nonogram.py examples/heart.txt --fill '█' --empty ' '
  █ █   █ █
█ █ █ █ █ █ █
█ █ █ █ █ █ █
  █ █ █ █ █
    █ █ █
      █
status: unique (7x6, 0 guesses)
```

Line logic stalls, so search is needed:

```
$ python nonogram.py examples/tricky.txt
. . . # . . # #
. . # . . . . .
# . . # # . . .
. # # . # . # .
. # # . . . # #
# # . . . . # .
. # . . # # . .
# . # # # . # .
status: unique (8x8, 34 guesses)
```

Ambiguous puzzle (exit 3):

```
$ python nonogram.py examples/ambiguous.txt
solution 1:
# .
. #
solution 2:
. #
# .
status: multiple (2x2, 2 guesses)
```

JSON output (`1` = filled, `0` = empty):

```
$ python nonogram.py examples/heart.txt --json
{"status": "unique", "width": 7, "height": 6, "guesses": 0, "solutions": [[[0, 1, 1, 0, 1, 1, 0], [1, 1, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1], [0, 1, 1, 1, 1, 1, 0], [0, 0, 1, 1, 1, 0, 0], [0, 0, 0, 1, 0, 0, 0]]]}
```

Bad input:

```
$ printf 'rows\n2\n0\ncols\n1\n0\n' | python nonogram.py -
error: row clues and column clues fill a different number of cells
```

## Tests

```
python -m unittest
```

```
Ran 13 tests in 0.066s

OK
```
