# exact-calc

Exact-arithmetic command-line calculator. It tokenizes an infix expression, turns it into Reverse Polish Notation with Dijkstra's **shunting-yard** algorithm, and evaluates the RPN with `fractions.Fraction`. Nothing is rounded during evaluation, so `0.1 + 0.2` gives exactly `3/10`. Standard library only.

## Features

- Numbers: `42`, `3.14`, `.5`, `1e-3` (all parsed as exact rationals)
- Operators: `+ - * / // %`, `^` or `**` (power, right-associative), unary `+`/`-`
- Precedence: unary minus binds looser than `^`, so `-2 ^ 2 = -4` (as in math)
- Functions: `abs floor ceil round sqrt min max gcd lcm` (`min`/`max`/`gcd`/`lcm` take any number of arguments)
- `sqrt` and `x ^ (n/2)` return a result only when it is exactly rational. They raise an error instead of approximating.
- Variables: `x = 3/4` assigns; `_` holds the last result
- Output: `num/den ≈ decimal`, or fixed decimals with `-d N`
- Reads expressions from arguments, or one per line from stdin (`#` comments allowed)
- Clear error messages (unbalanced parens, division by zero, unknown variable, wrong arity). Exit code is 1 if any line fails.

## Usage

```
$ python exact_calc.py "0.1 + 0.2" "2 ^ 3 ^ 2" "-2 ^ 2" "max(1, 7/2, 3)" "sqrt(9/16) + gcd(12, 18)"
3/10 ≈ 0.3
512
-4
7/2 ≈ 3.5
27/4 ≈ 6.75
```

Show the RPN produced by shunting-yard:

```
$ python exact_calc.py --rpn "3 + 4 * (2 - 1) ^ 2"
rpn: 3 4 2 1 - 2 ^ * +
7
```

Fixed decimals:

```
$ python exact_calc.py -d 5 "1/7"
0.14286
```

Session from stdin with variables and `_`:

```
$ printf 'rate = 0.075\nprice = 19.99\nprice * (1 + rate)\n_ * 3\n1/0\n' | python exact_calc.py
3/40 ≈ 0.075
1999/100 ≈ 19.99
85957/4000 ≈ 21.48925
257871/4000 ≈ 64.46775
error: division by zero
$ echo $?
1
```

Exactness is enforced:

```
$ python exact_calc.py "sqrt(2)"
error: sqrt(2) is irrational
```

## How it works

1. **Tokenize**: a regex splits the input into numbers, names, and operators.
2. **Shunting-yard**: operands go straight to the output queue. Operators wait on a stack. Before an operator is pushed, every stacked operator with higher precedence is popped to the output. Operators with equal precedence are popped too, unless the new operator is right-associative (`^`). A `-` is unary when it comes at the start, after `(`, after `,`, or after another operator. Function calls keep an argument counter that each `,` increments, so the output stores `("call", name, argc)`.
3. **Evaluate RPN**: a single stack pass. Every intermediate value is a `Fraction`.

Use it as a library:

```python
from exact_calc import evaluate, Calculator
evaluate("1/3 + 1/6")      # Fraction(1, 2)
c = Calculator(); c.run("x = 2"); c.run("x ^ 10")   # Fraction(1024, 1)
```

## Tests

```
python -m unittest -v
```

13 tests (with sub-tests) cover precedence, associativity, unary minus, fractions, functions, variables, formatting, error cases, and the CLI exit codes.
