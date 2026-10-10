# sudoku-solver

A fast 9x9 Sudoku solver written in JavaScript. It has no dependencies.

How it works:

- **Bitmask candidates.** Each cell stores its possible digits as a 9-bit mask.
- **Constraint propagation.** Two rules run until neither changes anything:
  - *Naked single*: a cell has only one candidate left, so that digit is removed from its 20 peers.
  - *Hidden single*: a digit fits in only one place in a row, column or box, so it is placed there.
- **MRV backtracking.** If propagation stalls, the solver branches on the cell with the fewest candidates. It searches depth-first on copies of the candidate array.
- **Solution counting.** The solver stops after `limit` solutions, so it can check whether a puzzle has a unique solution.

Easy puzzles solve by propagation alone (0 guesses). Puzzles marketed as the "world's hardest" take a few milliseconds.

## Usage

```
node sudoku.js [--line] [--count] <81-char puzzle | file | ->
```

Empty cells can be `.`, `0` or `_`. Whitespace and the `| - +` separators are ignored, so the solver also reads back its own pretty-printed output. A file containing one 81-character puzzle per line is solved line by line.

```
$ node sudoku.js '8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..'
8 1 2 | 7 5 3 | 6 4 9
9 4 3 | 6 8 2 | 1 7 5
6 7 5 | 4 9 1 | 2 8 3
------+-------+------
1 5 4 | 2 3 7 | 8 9 6
3 6 9 | 8 4 5 | 7 2 1
2 8 7 | 1 6 9 | 5 3 4
------+-------+------
5 2 1 | 9 7 4 | 3 6 8
4 3 8 | 5 2 6 | 9 1 7
7 9 6 | 3 1 8 | 4 5 2
(172 guesses, 4.6 ms)

$ node sudoku.js --line puzzles.txt
483921657967345821251876493548132976729564138136798245372689514814253769695417382
123456789456789123789123456231674895875912364694538217317265948542897631968341572

$ node sudoku.js --count .................................................................................
multiple solutions

$ node sudoku.js '11...............................................................................'
no solution            # exit code 1
```

## As a library

```js
const { solve, countSolutions, isValid, parse, format } = require('./sudoku');
const { solution, guesses } = solve('003020600900305001...');
countSolutions(puzzle);   // 0, 1, or 2 (2 = "more than one")
```

## Tests

```
node --test
```

There are 9 tests. They cover units and peers, parsing, validation, easy and hard puzzles, the empty grid, contradictions and uniqueness counting.
