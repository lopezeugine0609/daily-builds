# countdown-solver

Solver for the *Countdown* numbers game: reach a target by combining some of the given
numbers with `+ - * /`. Each number is used at most once. Every intermediate result must be
a positive integer: no fractions, no zero, no negatives.

- Finds an exact answer with the **fewest operations**. If no exact answer exists, it finds the **closest** value.
- Prints the steps in evaluation order plus one fully parenthesised infix expression.
- `--all` lists every *distinct* exact solution, shortest first. Rearrangements such as
  `5 * 4 * (6 - 1)` and `(6 - 1) * 4 * 5` count as one solution.
- `--json` gives machine-readable output. Exit codes: `0` exact, `1` closest only, `2` usage error.

Plain Node.js (no dependencies). One file, `countdown.js`.

## How it works

Each value is an expression-tree node. The search picks an unordered pair `(a, b)` with
`a >= b`, replaces it with `a op b`, and recurses. It checks every value it creates against the target.

Pruning rules:

- `a >= b` only, so `+`/`*` are tried once per pair, and `-`/`/` never go negative.
- `x * 1` and `x / 1` are skipped: they use up a number and change nothing.
- `a - b == b` and `a / b == b` are skipped: the result is the same as keeping `b`.
- In best-answer mode, a memo stores visited states as sorted `value:opcount` pairs.
  The same state reached in another order is not explored again.

Ties on distance are broken by the operation count of the answer's own tree. Side
computations that the answer does not use are not counted. In `--all` mode, solutions are
deduplicated by a canonical key. The key flattens `+`/`-` chains and `*`/`/` chains into sorted
positive and negative term lists.

## Usage

```
node countdown.js [--all] [--limit N] [--json] <n1> <n2> ... -t <target>
node countdown.js 25 50 75 100 3 6 952      (last number is the target)
```

The classic "952" puzzle:

```
$ node countdown.js 25 50 75 100 3 6 952
exact: 952
  75 * 3 = 225
  100 + 6 = 106
  225 * 106 = 23850
  23850 - 50 = 23800
  23800 / 25 = 952
  => (75 * 3 * (100 + 6) - 50) / 25 = 952
```

All distinct solutions:

```
$ node countdown.js --all --limit 5 1 2 3 4 5 6 -t 100
exact: 100
  5 * 2 = 10
  6 + 4 = 10
  10 * 10 = 100
  => 5 * 2 * (6 + 4) = 100
105 distinct exact solution(s), showing 5 shortest:
  (6 * 3 + 2) * 5
  5 * 2 * (6 + 4)
  5 * 4 * (3 + 2)
  5 * 4 * (6 - 1)
  ((4 + 3) * 2 + 6) * 5
```

Unreachable target (exit code 1):

```
$ node countdown.js 1 2 3 1000
closest: 9 (off by 991)
  2 + 1 = 3
  3 * 3 = 9
  => 3 * (2 + 1) = 9
```

JSON:

```
$ node countdown.js --json 2 3 6
{
  "target": 6,
  "value": 6,
  "diff": 0,
  "expression": "3 * 2",
  "steps": [
    {
      "a": 3,
      "op": "*",
      "b": 2,
      "result": 6
    }
  ],
  "explored": 1
}
```

Six numbers solve in well under a second. Seven numbers can take a few seconds. More than 7 numbers is rejected.

Library use:

```js
const { solve } = require('./countdown.js');
solve([25, 50, 75, 100, 3, 6], 952).expression; // '(75 * 3 * (100 + 6) - 50) / 25'
```

## Tests

```
node --test
```

13 tests. They cover the arithmetic rules, the shortest-answer preference, closest fallback,
duplicate inputs, `--all` dedup and ordering, and CLI exit codes. Each returned expression is
checked with an independent infix evaluator. The tests also confirm that it only uses the given numbers.
