#!/usr/bin/env python
"""Nonogram (Picross / Griddler) solver.

Strategy:
  1. Line solving: for each row/column, a memoized DP decides which cells
     can be filled and which can be empty across *all* placements of the
     clue blocks that agree with what is already known. Cells that admit
     only one value get fixed.
  2. Propagation: rows and columns are re-solved until nothing changes.
  3. Search: if cells remain unknown, pick one, guess filled/empty, and
     recurse (propagating after every guess). Up to `limit` solutions are
     collected so uniqueness can be reported.

Puzzle file format (blank lines and '#' comments ignored):

    rows
    3
    1 1
    0          <- empty line clue
    cols
    2
    ...
"""
import argparse
import json
import sys

UNKNOWN, EMPTY, FILLED = -1, 0, 1


class PuzzleError(ValueError):
    pass


def parse_puzzle(text):
    rows, cols, section = [], [], None
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        low = line.lower().rstrip(":")
        if low in ("rows", "cols", "columns"):
            section = rows if low == "rows" else cols
            continue
        if section is None:
            raise PuzzleError(f"line {lineno}: clue before 'rows'/'cols' header")
        try:
            nums = [int(t) for t in line.replace(",", " ").split()]
        except ValueError:
            raise PuzzleError(f"line {lineno}: bad clue {line!r}") from None
        if any(n < 0 for n in nums):
            raise PuzzleError(f"line {lineno}: negative clue")
        section.append([n for n in nums if n > 0])
    if not rows or not cols:
        raise PuzzleError("puzzle needs both 'rows' and 'cols' sections")
    for name, clues, size in (("row", rows, len(cols)), ("col", cols, len(rows))):
        for i, c in enumerate(clues):
            if sum(c) + max(len(c) - 1, 0) > size:
                raise PuzzleError(f"{name} {i + 1} clue {c} does not fit in {size} cells")
    if sum(map(sum, rows)) != sum(map(sum, cols)):
        raise PuzzleError("row clues and column clues fill a different number of cells")
    return rows, cols


def solve_line(clues, cells):
    """Return refined copy of `cells`, or None if no placement fits."""
    n, k = len(cells), len(clues)
    # next_empty[i]: first index >= i whose cell is EMPTY (n if none)
    next_empty = [n] * (n + 1)
    for i in range(n - 1, -1, -1):
        next_empty[i] = i if cells[i] == EMPTY else next_empty[i + 1]
    # no_fill_from[i]: True if no FILLED cell in cells[i:]
    no_fill_from = [True] * (n + 1)
    for i in range(n - 1, -1, -1):
        no_fill_from[i] = no_fill_from[i + 1] and cells[i] != FILLED

    memo = {}

    def fits(i, j):
        key = (i, j)
        if key in memo:
            return memo[key]
        if j == k:
            ok = no_fill_from[min(i, n)]
        elif i >= n:
            ok = False
        else:
            ok = cells[i] != FILLED and fits(i + 1, j)
            if not ok and can_place(i, j):
                ok = fits(min(i + clues[j] + 1, n), j + 1)
        memo[key] = ok
        return ok

    def can_place(i, j):
        end = i + clues[j]
        return end <= n and next_empty[i] >= end and (end == n or cells[end] != FILLED)

    if not fits(0, 0):
        return None

    can_fill, can_empty = [False] * n, [False] * n
    seen, stack = set(), [(0, 0)]
    while stack:
        i, j = stack.pop()
        if (i, j) in seen:
            continue
        seen.add((i, j))
        if j == k:
            for x in range(i, n):
                can_empty[x] = True
            continue
        if cells[i] != FILLED and fits(i + 1, j):
            can_empty[i] = True
            stack.append((i + 1, j))
        if can_place(i, j):
            nxt = min(i + clues[j] + 1, n)
            if fits(nxt, j + 1):
                end = i + clues[j]
                for x in range(i, end):
                    can_fill[x] = True
                if end < n:
                    can_empty[end] = True
                stack.append((nxt, j + 1))

    out = []
    for f, e in zip(can_fill, can_empty):
        out.append(UNKNOWN if f and e else FILLED if f else EMPTY)
    return out


def propagate(grid, rows, cols):
    """Line-solve until fixpoint. Mutates grid. Returns False on contradiction."""
    h, w = len(rows), len(cols)
    dirty_r, dirty_c = set(range(h)), set(range(w))
    while dirty_r or dirty_c:
        for r in sorted(dirty_r):
            new = solve_line(rows[r], grid[r])
            if new is None:
                return False
            for c in range(w):
                if new[c] != grid[r][c]:
                    grid[r][c] = new[c]
                    dirty_c.add(c)
        dirty_r.clear()
        for c in sorted(dirty_c):
            col = [grid[r][c] for r in range(h)]
            new = solve_line(cols[c], col)
            if new is None:
                return False
            for r in range(h):
                if new[r] != col[r]:
                    grid[r][c] = new[r]
                    dirty_r.add(r)
        dirty_c.clear()
    return True


def solve(rows, cols, limit=2):
    """Return (solutions, guesses). Stops after `limit` solutions."""
    stats = {"guesses": 0}
    solutions = []

    def rec(grid):
        if not propagate(grid, rows, cols):
            return
        for r, row in enumerate(grid):
            for c, v in enumerate(row):
                if v == UNKNOWN:
                    for val in (FILLED, EMPTY):
                        if len(solutions) >= limit:
                            return
                        stats["guesses"] += 1
                        g = [list(x) for x in grid]
                        g[r][c] = val
                        rec(g)
                    return
        solutions.append(grid)

    rec([[UNKNOWN] * len(cols) for _ in rows])
    return solutions, stats["guesses"]


def render(grid, fill="#", empty="."):
    return "\n".join(" ".join(fill if v == FILLED else empty for v in row) for row in grid)


def main(argv=None):
    p = argparse.ArgumentParser(description="Solve nonogram puzzles.")
    p.add_argument("puzzle", help="puzzle file, or - for stdin")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--limit", type=int, default=2, help="max solutions to find (default 2)")
    p.add_argument("--fill", default="#", help="char for filled cells")
    p.add_argument("--empty", default=".", help="char for empty cells")
    a = p.parse_args(argv)
    try:
        if a.puzzle == "-":
            text = sys.stdin.read()
        else:
            with open(a.puzzle, encoding="utf-8") as f:
                text = f.read()
        rows, cols = parse_puzzle(text)
    except (OSError, PuzzleError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    sols, guesses = solve(rows, cols, max(a.limit, 1))
    status = "none" if not sols else "unique" if len(sols) == 1 else "multiple"
    if a.json:
        print(json.dumps({
            "status": status,
            "width": len(cols), "height": len(rows),
            "guesses": guesses,
            "solutions": [[[v for v in row] for row in s] for s in sols],
        }))
    else:
        if not sols:
            print("no solution")
        for i, s in enumerate(sols):
            if len(sols) > 1:
                print(f"solution {i + 1}:")
            print(render(s, a.fill, a.empty))
        print(f"status: {status} ({len(cols)}x{len(rows)}, {guesses} guesses)", file=sys.stderr)
    return {"unique": 0, "none": 1, "multiple": 3}[status]


if __name__ == "__main__":
    sys.exit(main())
