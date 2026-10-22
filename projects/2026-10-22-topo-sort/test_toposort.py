import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

import toposort as ts

SAMPLE = """
# build graph
app: lib, utils
lib: utils
tests: app
docs
"""


def run(argv, text):
    import sys
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdin
    sys.stdin = io.StringIO(text)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = ts.main(argv)
    finally:
        sys.stdin = old
    return code, out.getvalue(), err.getvalue()


class TestParse(unittest.TestCase):
    def test_parse_adds_all_nodes(self):
        g = ts.parse(SAMPLE)
        self.assertEqual(g, {"app": {"lib", "utils"}, "lib": {"utils"}, "utils": set(),
                             "tests": {"app"}, "docs": set()})

    def test_repeated_lines_merge(self):
        self.assertEqual(ts.parse("a: b\na: c")["a"], {"b", "c"})

    def test_bad_line(self):
        with self.assertRaises(ValueError):
            ts.parse("a b c")


class TestOrder(unittest.TestCase):
    def test_order_deps_first_and_lexicographic(self):
        self.assertEqual(ts.order(ts.parse(SAMPLE)), ["docs", "utils", "lib", "app", "tests"])

    def test_order_valid_for_random_dag(self):
        import random
        rng = random.Random(7)
        nodes = [f"n{i}" for i in range(60)]
        g = {n: set() for n in nodes}
        for i, n in enumerate(nodes):
            for d in rng.sample(nodes[:i], min(i, 3)):
                g[n].add(d)
        pos = {n: i for i, n in enumerate(ts.order(g))}
        for n, deps in g.items():
            for d in deps:
                self.assertLess(pos[d], pos[n])

    def test_levels(self):
        self.assertEqual(ts.levels(ts.parse(SAMPLE)),
                         [["docs", "utils"], ["lib"], ["app"], ["tests"]])

    def test_empty(self):
        self.assertEqual(ts.order({}), [])
        self.assertEqual(ts.levels({}), [])


class TestCycles(unittest.TestCase):
    def test_cycle_reported(self):
        g = ts.parse("a: b\nb: c\nc: a\nd: a")
        with self.assertRaises(ts.CycleError) as cm:
            ts.order(g)
        self.assertEqual(cm.exception.cycle, ["a", "b", "c", "a"])

    def test_self_loop(self):
        with self.assertRaises(ts.CycleError) as cm:
            ts.levels(ts.parse("x: x"))
        self.assertEqual(cm.exception.cycle, ["x", "x"])

    def test_no_cycle(self):
        self.assertIsNone(ts.find_cycle(ts.parse(SAMPLE)))


class TestClosure(unittest.TestCase):
    def test_closure(self):
        sub = ts.closure(ts.parse(SAMPLE), ["lib"])
        self.assertEqual(set(sub), {"lib", "utils"})

    def test_unknown_target(self):
        with self.assertRaises(KeyError):
            ts.closure(ts.parse(SAMPLE), ["nope"])


class TestCLI(unittest.TestCase):
    def test_flat(self):
        code, out, _ = run([], SAMPLE)
        self.assertEqual((code, out), (0, "docs\nutils\nlib\napp\ntests\n"))

    def test_levels_json_reverse(self):
        code, out, _ = run(["-l", "--json", "--reverse"], SAMPLE)
        self.assertEqual(out.strip(), '[["tests"], ["app"], ["lib"], ["docs", "utils"]]')

    def test_target(self):
        code, out, _ = run(["-t", "app"], SAMPLE)
        self.assertEqual(out, "utils\nlib\napp\n")

    def test_cycle_exit_1(self):
        code, out, err = run([], "a: b\nb: a")
        self.assertEqual(code, 1)
        self.assertIn("a -> b -> a", err)

    def test_bad_input_exit_2(self):
        code, _, err = run(["-t", "zzz"], SAMPLE)
        self.assertEqual(code, 2)
        self.assertIn("unknown node(s): zzz", err)


if __name__ == "__main__":
    unittest.main()
