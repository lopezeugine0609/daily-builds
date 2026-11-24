#!/usr/bin/env python
"""dice-prob: exact probability distributions for dice notation.

Supports expressions like:
    3d6          sum of three six-sided dice
    2d20kh1      advantage (keep highest 1 of 2d20)
    4d6dl1       drop lowest 1 (D&D stat roll)
    d%           percentile die (1..100)
    1d8+1d6+3    sums, differences and constants
    2dF          Fudge dice (-1, 0, +1)

All math uses fractions.Fraction, so results are exact.
"""
import argparse
import json
import re
import sys
from fractions import Fraction
from functools import lru_cache
from itertools import product

MAX_ENUM = 2_000_000  # max outcomes enumerated for keep/drop terms

TERM_RE = re.compile(
    r"(?P<n>\d*)d(?P<sides>\d+|%|F)"
    r"(?:(?P<kd>kh|kl|dh|dl|k|d)(?P<m>\d+))?"
    r"|(?P<const>\d+)",
    re.IGNORECASE,
)


class DiceError(ValueError):
    pass


def die_faces(sides):
    if sides == "%":
        return list(range(1, 101))
    if sides.upper() == "F":
        return [-1, 0, 1]
    s = int(sides)
    if s < 1:
        raise DiceError("die must have at least 1 side")
    return list(range(1, s + 1))


def convolve(a, b):
    out = {}
    for x, px in a.items():
        for y, py in b.items():
            out[x + y] = out.get(x + y, 0) + px * py
    return out


def negate(dist):
    return {-k: v for k, v in dist.items()}


def sum_dist(n, faces):
    base = {f: Fraction(1, len(faces)) for f in faces}
    result = {0: Fraction(1)}
    # exponentiation by squaring
    while n:
        if n & 1:
            result = convolve(result, base)
        n >>= 1
        if n:
            base = convolve(base, base)
    return result


def keep_dist(n, faces, mode, m):
    """Distribution of the sum after keeping/dropping m dice."""
    if mode in ("k", "kh"):
        keep, high = m, True
    elif mode == "kl":
        keep, high = m, False
    elif mode in ("d", "dl"):
        keep, high = n - m, True
    elif mode == "dh":
        keep, high = n - m, False
    else:
        raise DiceError(f"unknown modifier {mode}")
    if not 0 <= keep <= n:
        raise DiceError(f"cannot keep {keep} of {n} dice")
    if keep == n:
        return sum_dist(n, faces)
    if keep == 0:
        return {0: Fraction(1)}
    if len(faces) ** n > MAX_ENUM:
        return _keep_dp(n, tuple(sorted(faces)), keep, high)
    out = {}
    p = Fraction(1, len(faces) ** n)
    for roll in product(faces, repeat=n):
        s = sorted(roll, reverse=high)
        t = sum(s[:keep])
        out[t] = out.get(t, 0) + p
    return out


def _keep_dp(n, faces, keep, high):
    """Order-statistic DP: process face values from best to worst.

    State: (dice remaining to assign, dice still to keep) -> sum distribution.
    For each face value choose how many of the remaining dice show it
    (multinomial weight), keeping as many as still needed.
    """
    order = list(faces[::-1] if high else faces)
    k = len(faces)
    from math import comb

    @lru_cache(maxsize=None)
    def go(i, left, need):
        if left == 0:
            return ((0, 1),)
        if i == len(order) - 1:
            take = min(left, need)
            return ((order[i] * take, 1),)
        acc = {}
        v = order[i]
        for c in range(left + 1):
            w = comb(left, c)
            take = min(c, need)
            for s, ways in go(i + 1, left - c, need - take):
                key = s + v * take
                acc[key] = acc.get(key, 0) + w * ways
        return tuple(acc.items())

    total = k ** n
    return {s: Fraction(w, total) for s, w in go(0, n, keep)}


def parse(expr):
    """Parse expression into list of (sign, term_dict)."""
    if re.search(r"[\w%]\s+[\w%]", expr):
        raise DiceError(f"whitespace inside a term or missing operator: {expr!r}")
    src = re.sub(r"\s+", "", expr)
    if not src:
        raise DiceError("empty expression")
    pos, sign, terms = 0, 1, []
    if src[0] in "+-":
        sign = -1 if src[0] == "-" else 1
        pos = 1
    while True:
        m = TERM_RE.match(src, pos)
        if not m or m.end() == pos:
            raise DiceError(f"bad term at position {pos}: {src[pos:] or '<end>'!r}")
        terms.append((sign, m))
        pos = m.end()
        if pos == len(src):
            return terms
        if src[pos] not in "+-":
            raise DiceError(f"expected + or - at position {pos}: {src[pos:]!r}")
        sign = -1 if src[pos] == "-" else 1
        pos += 1


def distribution(expr):
    dist = {0: Fraction(1)}
    for sign, m in parse(expr):
        if m.group("const"):
            d = {int(m.group("const")): Fraction(1)}
        else:
            n = int(m.group("n") or 1)
            if n < 1 or n > 1000:
                raise DiceError("dice count must be 1..1000")
            faces = die_faces(m.group("sides"))
            if m.group("kd"):
                d = keep_dist(n, faces, m.group("kd").lower(), int(m.group("m")))
            else:
                d = sum_dist(n, faces)
        dist = convolve(dist, d if sign > 0 else negate(d))
    return dict(sorted(dist.items()))


def stats(dist):
    mean = sum(k * p for k, p in dist.items())
    var = sum((k - mean) ** 2 * p for k, p in dist.items())
    mode = max(dist.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    cum, median = Fraction(0), None
    for k, p in dist.items():
        cum += p
        if cum >= Fraction(1, 2):
            median = k
            break
    return {"min": min(dist), "max": max(dist), "mean": mean,
            "variance": var, "stdev": float(var) ** 0.5,
            "mode": mode, "median": median}


def prob(dist, op, target):
    ops = {">=": lambda k: k >= target, ">": lambda k: k > target,
           "<=": lambda k: k <= target, "<": lambda k: k < target,
           "=": lambda k: k == target}
    return sum((p for k, p in dist.items() if ops[op](k)), Fraction(0))


def histogram(dist, width=40):
    top = max(dist.values())
    lines = []
    kw = max(len(str(k)) for k in dist)
    for k, p in dist.items():
        bar = "#" * max(1 if p else 0, round(float(p / top) * width))
        lines.append(f"{k:>{kw}} {float(p) * 100:6.2f}% {bar}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Exact dice probability calculator")
    ap.add_argument("expr", help="dice expression, e.g. 4d6dl1 or 2d20kh1+5")
    ap.add_argument("-p", "--prob", metavar="OPN",
                    help="probability query, e.g. '>=15', '<3', '=7'")
    ap.add_argument("--no-hist", action="store_true", help="hide histogram")
    ap.add_argument("--json", action="store_true", help="JSON output")
    a = ap.parse_args(argv)
    try:
        dist = distribution(a.expr)
        q = None
        if a.prob:
            qm = re.fullmatch(r"\s*(>=|<=|>|<|=)\s*(-?\d+)\s*", a.prob)
            if not qm:
                raise DiceError(f"bad --prob query: {a.prob!r}")
            q = (qm.group(1), int(qm.group(2)), prob(dist, qm.group(1), int(qm.group(2))))
    except DiceError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    st = stats(dist)
    if a.json:
        out = {"expr": a.expr,
               "stats": {k: (str(v) if isinstance(v, Fraction) else v) for k, v in st.items()},
               "distribution": {str(k): str(v) for k, v in dist.items()}}
        if q:
            out["query"] = {"op": q[0], "target": q[1], "p": str(q[2]), "float": float(q[2])}
        print(json.dumps(out, indent=2))
        return 0
    print(f"{a.expr}: range {st['min']}..{st['max']}, mean {float(st['mean']):.4f} "
          f"({st['mean']}), stdev {st['stdev']:.4f}, median {st['median']}, mode {st['mode']}")
    if q:
        print(f"P(X {q[0]} {q[1]}) = {q[2]} = {float(q[2]) * 100:.4f}%")
    if not a.no_hist:
        print(histogram(dist))
    return 0


if __name__ == "__main__":
    sys.exit(main())
