# truth-table

Boolean logic workbench in one Node file, no dependencies. It does five things:

- Parses boolean expressions. Supports `!`/`~`/`not`, `&`/`&&`/`and`/`*`, `^`/`xor`, `|`/`||`/`or`/`+`, `->`/`=>`/`implies`, `<->`/`<=>`/`iff`/`==` and the constants `0 1 true false`.
- Prints the full truth table. Variables are sorted, and the first variable is the most significant bit.
- Classifies the expression as a **tautology**, **contradiction** or **contingent**.
- Checks **equivalence** against a second expression. If they differ, it prints a counterexample.
- **Minimizes** the expression to a sum of products using Quine-McCluskey.

## How it works

- **Parser:** recursive descent with precedence climbing. Precedence, from loosest to tightest: `iff` < `imp` < `or` < `xor` < `and` < `not`. Implication is right-associative, so `a -> b -> c` means `a -> (b -> c)`.
- **Quine-McCluskey:** implicants are strings over `{0,1,-}`. The tool merges pairs that differ in exactly one fixed bit, and repeats until nothing merges. Any implicant that never merged is prime.
- **Cover:** essential prime implicants go in first. These are the only prime covering some minterm. For the rest, the tool searches covers of growing size and keeps the one with the fewest literals. This gives an exact minimum. It is exponential in the worst case, but fine at CLI sizes.

## Usage

```
node truth-table.js "<expr>" [--minimize] [--equiv "<expr2>"] [--quiet] [--json]
```

- `--quiet` hides the table.
- `--json` gives machine-readable output.
- Exit codes: `0` ok, `1` not equivalent (with `--equiv`), `2` parse or usage error.

```
$ node truth-table.js "a & b | a & !c" --minimize
a | b | c | out
--+---+---+----
0 | 0 | 0 |   0
0 | 0 | 1 |   0
0 | 1 | 0 |   0
0 | 1 | 1 |   0
1 | 0 | 0 |   1
1 | 0 | 1 |   0
1 | 1 | 0 |   1
1 | 1 | 1 |   1

class: contingent
minterms: m(4,6,7)
minimized: (a & b) | (a & !c)
```

```
$ node truth-table.js '!(p & q)' --equiv '!p & !q' --quiet; echo "exit $?"
class: contingent
minterms: m(0,1,2)
equivalent: no, counterexample p=0 q=1 gives 1 vs 0
exit 1
```

```
$ node truth-table.js '((p -> q) & (q -> r)) -> (p -> r)' --quiet --json
{
  "expression": "((p -> q) & (q -> r)) -> (p -> r)",
  "vars": [
    "p",
    "q",
    "r"
  ],
  "class": "tautology",
  "minterms": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7
  ]
}
```

```
$ node truth-table.js 'a & (b'; echo "exit $?"
parse error: missing ')' for '(' at 3
exit 2
```

## Library

```js
const { parse, truthTable, classify, equivalent, minimize, sop } = require('./truth-table.js');
```

## Tests

```
node --test
```

There are 12 tests. They cover:

- operator aliases, precedence and associativity
- parse errors
- table order and classification
- De Morgan equivalence and its counterexample
- prime implicants of a known function
- minimal SOP for fixed cases
- 40 random 4-variable functions, each checked to give back exactly the same minterms after minimizing
- CLI exit codes
