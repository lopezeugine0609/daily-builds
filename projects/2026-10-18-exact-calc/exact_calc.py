#!/usr/bin/env python
"""exact-calc: an exact-arithmetic expression calculator.

Tokenizes an infix expression, converts it to Reverse Polish Notation with
Dijkstra's shunting-yard algorithm, then evaluates the RPN using
fractions.Fraction so 0.1 + 0.2 is exactly 3/10.

Supported:
  numbers      42, 3.14, 1e-3, .5
  operators    + - * / // % ^ (right-assoc power), unary + and -
  grouping     ( )
  functions    abs, min, max, gcd, lcm, floor, ceil, round, sqrt (exact only)
  variables    `x = 3/4` assigns; `_` holds the last result
"""
import argparse
import math
import re
import sys
from fractions import Fraction

TOKEN_RE = re.compile(
    r"\s*(?:(?P<num>(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
    r"|(?P<name>[A-Za-z_]\w*)"
    r"|(?P<op>//|\*\*|[-+*/%^(),=]))"
)

# precedence, right-associative?
BINARY = {
    "+": (1, False), "-": (1, False),
    "*": (2, False), "/": (2, False), "//": (2, False), "%": (2, False),
    "^": (4, True),
}
UNARY_PREC = 3  # binds tighter than * but looser than ^, so -2^2 == -4


class CalcError(Exception):
    pass


def _exact_sqrt(x):
    if x < 0:
        raise CalcError("sqrt of negative number")
    n, d = x.numerator, x.denominator
    rn, rd = math.isqrt(n), math.isqrt(d)
    if rn * rn != n or rd * rd != d:
        raise CalcError(f"sqrt({x}) is irrational")
    return Fraction(rn, rd)


def _int_arg(name, x):
    if x.denominator != 1:
        raise CalcError(f"{name} needs integers, got {x}")
    return x.numerator


FUNCS = {
    "abs": (1, lambda a: abs(a)),
    "floor": (1, lambda a: Fraction(math.floor(a))),
    "ceil": (1, lambda a: Fraction(math.ceil(a))),
    "round": (1, lambda a: Fraction(round(a))),
    "sqrt": (1, _exact_sqrt),
    "min": (None, lambda *a: min(a)),
    "max": (None, lambda *a: max(a)),
    "gcd": (None, lambda *a: Fraction(math.gcd(*(_int_arg("gcd", x) for x in a)))),
    "lcm": (None, lambda *a: Fraction(math.lcm(*(_int_arg("lcm", x) for x in a)))),
}


def tokenize(text):
    tokens, pos = [], 0
    text = text.rstrip()
    while pos < len(text):
        m = TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise CalcError(f"unexpected character {text[pos:].lstrip()[0]!r} at {pos}")
        kind = m.lastgroup or "op"
        val = m.group(kind)
        if val == "**":
            val = "^"
        tokens.append((kind, val))
        pos = m.end()
    return tokens


def to_rpn(tokens):
    """Shunting-yard. Output items: ('num', Fraction) ('var', name)
    ('op', sym) ('neg',) ('call', name, argc)."""
    out, stack = [], []
    argc = []          # arg counters for open function calls
    prev = None        # previous token kind, to detect unary minus
    for kind, val in tokens:
        if kind == "num":
            out.append(("num", Fraction(val)))
            prev = "operand"
        elif kind == "name":
            out_kind = "func" if val in FUNCS else "var"
            if out_kind == "func":
                stack.append(("func", val))
                prev = "func"
            else:
                out.append(("var", val))
                prev = "operand"
        elif val == "(":
            if prev == "func":
                argc.append(1)
                stack.append(("fparen", None))
            else:
                stack.append(("paren", None))
            prev = "open"
        elif val == ",":
            while stack and stack[-1][0] not in ("fparen", "paren"):
                out.append(_pop_op(stack))
            if not stack or stack[-1][0] != "fparen":
                raise CalcError("comma outside function call")
            argc[-1] += 1
            prev = "open"
        elif val == ")":
            while stack and stack[-1][0] not in ("fparen", "paren"):
                out.append(_pop_op(stack))
            if not stack:
                raise CalcError("unbalanced ')'")
            kind_open, _ = stack.pop()
            if kind_open == "fparen":
                if prev == "open":
                    raise CalcError("empty function argument")
                _, name = stack.pop()
                out.append(("call", name, argc.pop()))
            elif prev == "open":
                raise CalcError("empty parentheses")
            prev = "operand"
        elif val == "=":
            raise CalcError("'=' only allowed as 'name = expr'")
        else:  # operator
            if prev in (None, "open", "op"):
                if val in "+-":
                    if val == "-":
                        stack.append(("neg", None))
                    prev = "op"
                    continue
                raise CalcError(f"operator {val!r} missing left operand")
            if prev == "func":
                raise CalcError("function name must be followed by '('")
            prec, right = BINARY[val]
            while stack:
                top = stack[-1]
                if top[0] == "neg":
                    top_prec = UNARY_PREC
                elif top[0] == "op":
                    top_prec = BINARY[top[1]][0]
                else:
                    break
                if top_prec > prec or (top_prec == prec and not right):
                    out.append(_pop_op(stack))
                else:
                    break
            stack.append(("op", val))
            prev = "op"
    if prev in ("op", "open", "func", None):
        raise CalcError("incomplete expression")
    while stack:
        if stack[-1][0] in ("paren", "fparen"):
            raise CalcError("unbalanced '('")
        out.append(_pop_op(stack))
    return out


def _pop_op(stack):
    kind, val = stack.pop()
    return ("neg",) if kind == "neg" else ("op", val)


def _apply(op, a, b):
    if op == "+": return a + b
    if op == "-": return a - b
    if op == "*": return a * b
    if op in ("/", "//", "%") and b == 0:
        raise CalcError("division by zero")
    if op == "/": return a / b
    if op == "//": return Fraction(a // b)
    if op == "%": return a % b
    if op == "^":
        if b.denominator != 1:
            root = _exact_sqrt(a) if b.denominator == 2 else None
            if root is None:
                raise CalcError(f"non-integer exponent {b} not supported exactly")
            return root ** b.numerator
        if a == 0 and b < 0:
            raise CalcError("division by zero")
        return a ** b.numerator
    raise CalcError(f"unknown operator {op}")


def eval_rpn(rpn, env):
    st = []
    for item in rpn:
        tag = item[0]
        if tag == "num":
            st.append(item[1])
        elif tag == "var":
            if item[1] not in env:
                raise CalcError(f"unknown variable {item[1]!r}")
            st.append(env[item[1]])
        elif tag == "neg":
            st.append(-st.pop())
        elif tag == "op":
            b, a = st.pop(), st.pop()
            st.append(_apply(item[1], a, b))
        elif tag == "call":
            _, name, n = item
            arity, fn = FUNCS[name]
            if arity is not None and n != arity:
                raise CalcError(f"{name}() takes {arity} argument(s), got {n}")
            args = st[-n:]
            del st[-n:]
            st.append(Fraction(fn(*args)))
    if len(st) != 1:
        raise CalcError("malformed expression")
    return st[0]


class Calculator:
    def __init__(self):
        self.env = {}

    def run(self, line):
        tokens = tokenize(line)
        target = None
        if len(tokens) >= 2 and tokens[0][0] == "name" and tokens[1] == ("op", "="):
            target = tokens[0][1]
            if target in FUNCS:
                raise CalcError(f"cannot assign to function {target!r}")
            tokens = tokens[2:]
        value = eval_rpn(to_rpn(tokens), self.env)
        self.env["_"] = value
        if target:
            self.env[target] = value
        return value


def evaluate(expr, env=None):
    return eval_rpn(to_rpn(tokenize(expr)), env or {})


def fmt(value, decimals=None):
    if decimals is not None:
        return _fixed(value, decimals)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator} ≈ {float(value):.12g}"


def _fixed(value, places):
    scaled = round(value * 10 ** places)
    sign = "-" if scaled < 0 else ""
    s = str(abs(scaled)).rjust(places + 1, "0")
    return f"{sign}{s[:-places]}.{s[-places:]}" if places else f"{sign}{s}"


def main(argv=None):
    p = argparse.ArgumentParser(description="Exact rational calculator (shunting-yard + Fraction).")
    p.add_argument("expr", nargs="*", help="expression(s); omit to read lines from stdin")
    p.add_argument("-d", "--decimals", type=int, help="print as fixed decimal with N places")
    p.add_argument("--rpn", action="store_true", help="also print the RPN form")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    calc = Calculator()
    lines = args.expr if args.expr else (l for l in sys.stdin)
    status = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            if args.rpn:
                rpn = to_rpn(tokenize(line.split("=", 1)[-1] if "=" in line else line))
                print("rpn:", " ".join(_rpn_str(t) for t in rpn))
            print(fmt(calc.run(line), args.decimals))
        except (CalcError, IndexError) as e:
            print(f"error: {e or 'malformed expression'}", file=sys.stderr)
            status = 1
    return status


def _rpn_str(t):
    if t[0] == "num": return str(t[1])
    if t[0] == "var": return t[1]
    if t[0] == "neg": return "neg"
    if t[0] == "op": return t[1]
    return f"{t[1]}/{t[2]}"


if __name__ == "__main__":
    sys.exit(main())
