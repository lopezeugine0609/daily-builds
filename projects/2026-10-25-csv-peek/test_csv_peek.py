import contextlib
import io
import json
import os
import tempfile
import unittest

import csv_peek as cp


class ClassifyTests(unittest.TestCase):
    def test_cells(self):
        self.assertEqual(cp.classify("42"), "int")
        self.assertEqual(cp.classify("-3.5"), "float")
        self.assertEqual(cp.classify("1e3"), "float")
        self.assertEqual(cp.classify("yes"), "bool")
        self.assertEqual(cp.classify("2026-10-25"), "date")
        self.assertEqual(cp.classify("hello"), "string")
        self.assertEqual(cp.classify("1_000"), "string")
        self.assertEqual(cp.classify("nan"), "string")
        self.assertEqual(cp.classify("inf"), "string")

    def test_merge(self):
        self.assertEqual(cp.infer_type(["1", "2.5", ""]), "float")
        self.assertEqual(cp.infer_type(["1", "x"]), "string")
        self.assertEqual(cp.infer_type(["", "NA", "null"]), "empty")
        self.assertEqual(cp.infer_type(["3", "N/A", "4"]), "int")


class ReadTests(unittest.TestCase):
    def test_sniff_semicolon(self):
        h, b, d = cp.read_csv("a;b\n1;2\n3;4\n")
        self.assertEqual(d, ";")
        self.assertEqual(h, ["a", "b"])
        self.assertEqual(b, [["1", "2"], ["3", "4"]])

    def test_ragged_rows_padded(self):
        h, b, _ = cp.read_csv("a,b\n1,2,3\n4\n", ",")
        self.assertEqual(h, ["a", "b", "col3"])
        self.assertEqual(b, [["1", "2", "3"], ["4", "", ""]])

    def test_quoted_commas(self):
        h, b, _ = cp.read_csv('name,note\nAna,"hi, there"\n', ",")
        self.assertEqual(b[0][1], "hi, there")

    def test_empty(self):
        self.assertEqual(cp.read_csv("", ","), ([], [], ","))


class ProfileTests(unittest.TestCase):
    def test_numeric_stats(self):
        h, b, _ = cp.read_csv("x,y\n1,a\n3,a\n,b\n", ",")
        px, py = cp.profile(h, b)
        self.assertEqual(px["type"], "int")
        self.assertEqual((px["min"], px["max"], px["mean"]), (1, 3, 2.0))
        self.assertEqual(px["nulls"], 1)
        self.assertEqual(py["top"], "a")
        self.assertEqual(py["top_count"], 2)
        self.assertEqual(py["distinct"], 2)


class RenderTests(unittest.TestCase):
    def test_alignment_and_clip(self):
        out = cp.render_table(["n", "s"], [["5", "abcdefgh"], ["100", "x"]], 4, ["int", "string"])
        lines = out.splitlines()
        self.assertEqual(lines[0], "n   | s")
        self.assertEqual(lines[2], "  5 | abc…")
        self.assertEqual(lines[3], "100 | x")


class CliTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", newline="") as fh:
            fh.write("id,price\n1,9.5\n2,10\n3,\n")

    def tearDown(self):
        os.remove(self.path)

    def run_cli(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cp.main(list(args))
        return code, buf.getvalue()

    def test_json(self):
        code, out = self.run_cli(self.path, "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["rows"], 3)
        self.assertEqual(data["profile"][1]["type"], "float")
        self.assertEqual(data["profile"][1]["nulls"], 1)

    def test_preview_truncation(self):
        code, out = self.run_cli(self.path, "-n", "1", "--no-stats")
        self.assertEqual(code, 0)
        self.assertIn("... 2 more rows", out)

    def test_missing_file(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cp.main(["/nonexistent/x.csv"]), 2)


if __name__ == "__main__":
    unittest.main()
