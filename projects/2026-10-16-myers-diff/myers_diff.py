#!/usr/bin/env python
"""Myers O(ND) line diff with unified-format output.

Implements Eugene Myers' 1986 greedy algorithm ("An O(ND) Difference
Algorithm and Its Variations") to find a shortest edit script between two
sequences, then groups the edits into unified-diff hunks.

Standard library only. Run `python myers_diff.py --help`.
"""
import argparse
import sys

EQUAL, DELETE, INSERT = " ", "-", "+"


def shortest_edit(a, b):
    """Return the list of V-arrays (one per edit distance d) from the forward
    greedy search. V[k] is the furthest x reached on diagonal k = x - y."""
    n, m = len(a), len(b)
    maximum = n + m
    v = {1: 0}
    trace = []
    for d in range(maximum + 1):
        trace.append(dict(v))
        for k in range(-d, d + 1, 2):
            # Pick the move: down (insert) from k+1, or right (delete) from k-1.
            if k == -d or (k != d and v[k - 1] < v[k + 1]):
                x = v[k + 1]
            else:
                x = v[k - 1] + 1
            y = x - k
            # Follow the "snake": free diagonal moves over equal elements.
            while x < n and y < m and a[x] == b[y]:
                x, y = x + 1, y + 1
            v[k] = x
            if x >= n and y >= m:
                trace.append(dict(v))
                return trace
    return trace  # unreachable


def diff(a, b):
    """Return a list of (op, line) tuples where op is ' ', '-' or '+'."""
    a, b = list(a), list(b)
    trace = shortest_edit(a, b)
    x, y = len(a), len(b)
    ops = []
    # Backtrack: trace[d] holds V *before* step d, trace[-1] the final V.
    for d in range(len(trace) - 2, -1, -1):
        v = trace[d]
        k = x - y
        if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
            prev_k = k + 1
        else:
            prev_k = k - 1
        prev_x = v.get(prev_k, 0)
        prev_y = prev_x - prev_k
        while x > prev_x and y > prev_y:
            x, y = x - 1, y - 1
            ops.append((EQUAL, a[x]))
        if d > 0:
            if x == prev_x:
                ops.append((INSERT, b[prev_y]))
            else:
                ops.append((DELETE, a[prev_x]))
        x, y = prev_x, prev_y
    ops.reverse()
    return ops


def edit_distance(a, b):
    """Number of inserted + deleted lines in the shortest edit script."""
    return sum(1 for op, _ in diff(a, b) if op != EQUAL)


def _range(start, length):
    if length == 0:
        return f"{start - 1 if start else 0},0"
    return f"{start}" if length == 1 else f"{start},{length}"


def unified(a, b, from_name="a", to_name="b", context=3):
    """Return unified-diff text (empty string if inputs are equal)."""
    ops = diff(a, b)
    changes = [i for i, (op, _) in enumerate(ops) if op != EQUAL]
    if not changes:
        return ""
    # Group change indices into hunks whose context windows touch.
    groups, start, end = [], changes[0], changes[0]
    for i in changes[1:]:
        if i - end - 1 > 2 * context:  # equal lines between changes
            groups.append((start, end))
            start = i
        end = i
    groups.append((start, end))

    # Precompute line numbers (1-based) of each op in a and b.
    a_no, b_no, ai, bi = [], [], 1, 1
    for op, _ in ops:
        a_no.append(ai)
        b_no.append(bi)
        if op != INSERT:
            ai += 1
        if op != DELETE:
            bi += 1

    out = [f"--- {from_name}", f"+++ {to_name}"]
    for s, e in groups:
        lo, hi = max(0, s - context), min(len(ops), e + context + 1)
        chunk = ops[lo:hi]
        a_len = sum(1 for op, _ in chunk if op != INSERT)
        b_len = sum(1 for op, _ in chunk if op != DELETE)
        out.append(f"@@ -{_range(a_no[lo], a_len)} +{_range(b_no[lo], b_len)} @@")
        out.extend(op + line for op, line in chunk)
    return "\n".join(out) + "\n"


def _read(path):
    if path == "-":
        return sys.stdin.read().splitlines()
    with open(path, encoding="utf-8") as fh:
        return fh.read().splitlines()


def main(argv=None):
    p = argparse.ArgumentParser(description="Myers O(ND) line diff (unified format).")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("-U", "--context", type=int, default=3, help="context lines (default 3)")
    p.add_argument("--stat", action="store_true", help="print only +/- counts and edit distance")
    p.add_argument("--color", action="store_true", help="ANSI-color the output")
    args = p.parse_args(argv)

    a, b = _read(args.old), _read(args.new)
    if args.stat:
        ops = diff(a, b)
        ins = sum(op == INSERT for op, _ in ops)
        dels = sum(op == DELETE for op, _ in ops)
        print(f"{ins} insertion(s)(+), {dels} deletion(s)(-), edit distance {ins + dels}")
        return 1 if ins or dels else 0

    text = unified(a, b, args.old, args.new, args.context)
    if args.color:
        colors = {"+": "\033[32m", "-": "\033[31m", "@": "\033[36m"}
        text = "".join(
            colors.get(ln[:1], "") + ln + ("\033[0m" if ln[:1] in colors else "") + "\n"
            for ln in text.splitlines()
        )
    sys.stdout.write(text)
    return 1 if text else 0


if __name__ == "__main__":
    sys.exit(main())
