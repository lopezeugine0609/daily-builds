import contextlib
import io
import itertools
import os
import random
import unittest

import nonogram as ng
from nonogram import EMPTY, FILLED, UNKNOWN

HERE = os.path.dirname(os.path.abspath(__file__))


def clues_of(line):
    return [len(list(g)) for v, g in itertools.groupby(line) if v == FILLED]


def clues_for(grid):
    return [clues_of(r) for r in grid], [clues_of(c) for c in zip(*grid)]


def brute_line(clues, cells):
    """Reference line solver: enumerate every 0/1 line."""
    ok = [p for p in itertools.product((EMPTY, FILLED), repeat=len(cells))
          if clues_of(p) == clues and all(c == UNKNOWN or c == v for c, v in zip(cells, p))]
    if not ok:
        return None
    return [col[0] if len(set(col)) == 1 else UNKNOWN for col in zip(*ok)]


class LineSolverTest(unittest.TestCase):
    def test_overlap(self):
        self.assertEqual(ng.solve_line([4], [UNKNOWN] * 5),
                         [UNKNOWN, FILLED, FILLED, FILLED, UNKNOWN])

    def test_full_and_empty(self):
        self.assertEqual(ng.solve_line([2, 1], [UNKNOWN] * 4), [FILLED, FILLED, EMPTY, FILLED])
        self.assertEqual(ng.solve_line([], [UNKNOWN] * 3), [EMPTY] * 3)

    def test_contradiction(self):
        self.assertIsNone(ng.solve_line([], [UNKNOWN, FILLED]))
        self.assertIsNone(ng.solve_line([3], [UNKNOWN, EMPTY, UNKNOWN, UNKNOWN]))

    def test_matches_brute_force(self):
        rnd = random.Random(7)
        for _ in range(400):
            n = rnd.randint(1, 9)
            sol = [rnd.choice((EMPTY, FILLED)) for _ in range(n)]
            cells = [v if rnd.random() < 0.3 else UNKNOWN for v in sol]
            clues = clues_of(sol)
            if rnd.random() < 0.2:  # sometimes inconsistent clues
                clues = clues_of([rnd.choice((EMPTY, FILLED)) for _ in range(n)])
            self.assertEqual(ng.solve_line(clues, cells), brute_line(clues, cells),
                             (clues, cells))


class SolverTest(unittest.TestCase):
    def test_heart_unique_no_guesses(self):
        with open(os.path.join(HERE, "examples", "heart.txt")) as f:
            rows, cols = ng.parse_puzzle(f.read())
        sols, guesses = ng.solve(rows, cols)
        self.assertEqual(len(sols), 1)
        self.assertEqual(guesses, 0)
        self.assertEqual(ng.render(sols[0]).splitlines()[0], ". # # . # # .")

    def test_tricky_needs_search(self):
        with open(os.path.join(HERE, "examples", "tricky.txt")) as f:
            rows, cols = ng.parse_puzzle(f.read())
        sols, guesses = ng.solve(rows, cols)
        self.assertEqual(len(sols), 1)
        self.assertGreater(guesses, 0)
        self.assertEqual(clues_for(sols[0]), (rows, cols))

    def test_ambiguous(self):
        sols, _ = ng.solve([[1], [1]], [[1], [1]], limit=5)
        self.assertEqual(len(sols), 2)

    def test_no_solution(self):
        sols, _ = ng.solve([[2], [0]], [[1], [0]])
        self.assertEqual(sols, [])

    def test_random_grids_roundtrip(self):
        rnd = random.Random(42)
        for _ in range(60):
            h, w = rnd.randint(1, 8), rnd.randint(1, 8)
            grid = [[rnd.choice((EMPTY, FILLED)) for _ in range(w)] for _ in range(h)]
            rows, cols = clues_for(grid)
            sols, _ = ng.solve(rows, cols, limit=3)
            self.assertTrue(sols)
            for s in sols:  # every solution must satisfy all clues
                self.assertEqual(clues_for(s), (rows, cols))
            if len(sols) == 1:
                self.assertEqual(sols[0], grid)


class ParseAndCliTest(unittest.TestCase):
    def test_parse(self):
        rows, cols = ng.parse_puzzle("# c\nrows:\n1, 1\n0\ncolumns\n1\n0\n1\n")
        self.assertEqual(rows, [[1, 1], []])
        self.assertEqual(cols, [[1], [], [1]])

    def test_parse_errors(self):
        for bad in ("1\nrows\n1\ncols\n1", "rows\nx\ncols\n1", "rows\n3\ncols\n1\n1",
                    "rows\n1\ncols\n0", "rows\n1"):
            with self.assertRaises(ng.PuzzleError):
                ng.parse_puzzle(bad)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ng.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_cli_exit_codes(self):
        ex = os.path.join(HERE, "examples")
        self.assertEqual(self.run_cli(os.path.join(ex, "heart.txt"))[0], 0)
        self.assertEqual(self.run_cli(os.path.join(ex, "ambiguous.txt"))[0], 3)
        self.assertEqual(self.run_cli("does-not-exist.txt")[0], 2)

    def test_cli_json(self):
        import json
        code, out, _ = self.run_cli(os.path.join(HERE, "examples", "heart.txt"), "--json")
        data = json.loads(out)
        self.assertEqual((code, data["status"], data["width"]), (0, "unique", 7))


if __name__ == "__main__":
    unittest.main()
