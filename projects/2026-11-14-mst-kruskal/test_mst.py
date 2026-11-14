import contextlib
import io
import json
import os
import random
import tempfile
import unittest
from fractions import Fraction

import mst

SAMPLE = os.path.join(os.path.dirname(__file__), "sample.txt")


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = mst.main(argv)
    return code, buf.getvalue()


def write_tmp(text):
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class ParseTests(unittest.TestCase):
    def test_comments_commas_blank_lines(self):
        edges = mst.parse_edges("# hi\n\nA,B,2  # trailing\nB C 3\n")
        self.assertEqual(edges, [("A", "B", Fraction(2)), ("B", "C", Fraction(3))])

    def test_bad_field_count(self):
        with self.assertRaisesRegex(mst.GraphError, "line 1"):
            mst.parse_edges("A B\n")

    def test_bad_weight(self):
        with self.assertRaisesRegex(mst.GraphError, "not a finite number"):
            mst.parse_edges("A B nan\n")
        with self.assertRaises(mst.GraphError):
            mst.parse_edges("A B 1/0\n")

    def test_exact_fraction_weights(self):
        edges = mst.parse_edges("A B 1/3\nB C 0.1\n")
        self.assertEqual(edges[0][2], Fraction(1, 3))
        self.assertEqual(edges[1][2], Fraction(1, 10))


class AlgorithmTests(unittest.TestCase):
    def setUp(self):
        with open(SAMPLE, encoding="utf-8") as f:
            self.edges = mst.parse_edges(f.read())

    def test_kruskal_sample(self):
        res = mst.solve(self.edges, "kruskal")
        self.assertEqual(res["total"], 39)
        self.assertEqual(len(res["tree"]), 6)
        self.assertEqual(res["components"], 1)

    def test_prim_sample_matches_kruskal(self):
        self.assertEqual(mst.solve(self.edges, "prim")["total"], 39)

    def test_self_loop_ignored(self):
        edges = mst.parse_edges("A A 0\nA B 4\n")
        for algo in ("kruskal", "prim"):
            res = mst.solve(edges, algo)
            self.assertEqual(res["tree"], [("A", "B", Fraction(4))])

    def test_disconnected_forest(self):
        edges = mst.parse_edges("A B 1\nC D 2\nC E 3\n")
        res = mst.solve(edges, "kruskal")
        self.assertEqual(res["components"], 2)
        self.assertEqual(res["total"], 6)

    def test_random_graphs_agree_and_are_trees(self):
        rng = random.Random(1234)
        for _ in range(200):
            n = rng.randint(2, 12)
            nodes = [f"n{i}" for i in range(n)]
            edges = []
            for i in range(1, n):  # random spanning tree guarantees connectivity
                edges.append((nodes[rng.randrange(i)], nodes[i], Fraction(rng.randint(-5, 20))))
            for _ in range(rng.randint(0, 3 * n)):
                u, v = rng.sample(nodes, 2)
                edges.append((u, v, Fraction(rng.randint(-5, 20))))
            k = mst.solve(edges, "kruskal")
            p = mst.solve(edges, "prim")
            self.assertEqual(k["total"], p["total"])
            self.assertEqual(len(k["tree"]), n - 1)
            self.assertEqual(len(p["tree"]), n - 1)
            self.assertEqual(k["components"], 1)


class CliTests(unittest.TestCase):
    def test_sample_text_output(self):
        code, out = run([SAMPLE])
        self.assertEqual(code, 0)
        self.assertIn("total weight: 39", out)
        self.assertIn("kruskal: 7 nodes, 6 edges, 1 component(s)", out)

    def test_verify_passes(self):
        code, out = run([SAMPLE, "--verify", "--algo", "prim"])
        self.assertEqual(code, 0)
        self.assertIn("verify: kruskal and prim agree", out)

    def test_json_output(self):
        code, out = run([SAMPLE, "--json", "--verify"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["total_weight"], 39)
        self.assertTrue(data["verified"])
        self.assertEqual(len(data["tree"]), 6)

    def test_disconnected_exit_code(self):
        path = write_tmp("A B 1\nC D 2\n")
        try:
            self.assertEqual(run([path])[0], mst.EXIT_DISCONNECTED)
            code, out = run([path, "--forest"])
            self.assertEqual(code, 0)
            self.assertIn("2 component(s)", out)
        finally:
            os.remove(path)

    def test_missing_file_and_empty_input(self):
        self.assertEqual(run([os.path.join(tempfile.gettempdir(), "no-such-mst-file.txt")])[0], mst.EXIT_INPUT)
        path = write_tmp("# nothing\n")
        try:
            self.assertEqual(run([path])[0], mst.EXIT_INPUT)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
