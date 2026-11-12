import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr

import log_cluster as lc


class TemplateTests(unittest.TestCase):
    def test_masks_numbers(self):
        self.assertEqual(lc.template_of("took 42 ms"), "took <NUM> ms")

    def test_masks_ip_with_port(self):
        self.assertEqual(lc.template_of("conn from 10.0.0.5:8080 ok"), "conn from <IP> ok")

    def test_masks_uuid_before_numbers(self):
        t = lc.template_of("req 3f2504e0-4f89-11d3-9a0c-0305e82c3301 done")
        self.assertEqual(t, "req <UUID> done")

    def test_masks_iso_timestamp(self):
        t = lc.template_of("2026-11-12T08:30:15.123Z INFO start")
        self.assertEqual(t, "<TS> INFO start")

    def test_masks_space_separated_timestamp(self):
        self.assertEqual(lc.template_of("2026-11-12 08:30:15 WARN x"), "<TS> WARN x")

    def test_masks_time_only(self):
        self.assertEqual(lc.template_of("10:01:02 tick"), "<TIME> tick")

    def test_masks_hex(self):
        self.assertEqual(lc.template_of("ptr 0xDEADbeef set"), "ptr <HEX> set")

    def test_masks_quoted_strings(self):
        self.assertEqual(lc.template_of('user "alice smith" logged in'), "user <STR> logged in")

    def test_decimal_is_one_number(self):
        self.assertEqual(lc.template_of("load 0.75 avg"), "load <NUM> avg")

    def test_collapses_whitespace(self):
        self.assertEqual(lc.template_of("a   \t b\r"), "a b")

    def test_no_variables_unchanged(self):
        self.assertEqual(lc.template_of("server ready"), "server ready")

    def test_digits_inside_word_not_masked(self):
        # "v2" and "abc123" are identifiers; \b keeps them intact.
        self.assertEqual(lc.template_of("abc123 v2 start"), "abc123 v2 start")


class ClusterTests(unittest.TestCase):
    def test_groups_by_template(self):
        lines = ["user 1 login\n", "user 2 login\n", "user 3 logout\n"]
        g = lc.cluster(lines)
        self.assertEqual(list(g), ["user <NUM> login", "user <NUM> logout"])
        self.assertEqual(g["user <NUM> login"]["count"], 2)

    def test_examples_keep_original_line_numbers(self):
        g = lc.cluster(["a 1\n", "b\n", "a 2\n"])
        self.assertEqual(g["a <NUM>"]["examples"], [(1, "a 1"), (3, "a 2")])

    def test_blank_lines_skipped_but_numbered(self):
        g = lc.cluster(["x 1\n", "\n", "   \n", "x 2\n"])
        self.assertEqual(g["x <NUM>"]["count"], 2)
        self.assertEqual(g["x <NUM>"]["examples"][1][0], 4)

    def test_no_trailing_newline(self):
        g = lc.cluster(["only 7"])
        self.assertEqual(g["only <NUM>"]["count"], 1)

    def test_empty_input(self):
        self.assertEqual(len(lc.cluster([])), 0)


class RankTests(unittest.TestCase):
    def setUp(self):
        self.g = lc.cluster(["b 1\n", "a 1\n", "a 2\n", "c\n", "a 3\n", "b 2\n"])

    def test_sorted_by_count_then_template(self):
        items = lc.rank(self.g)
        self.assertEqual([t for t, _ in items], ["a <NUM>", "b <NUM>", "c"])

    def test_min_filter(self):
        items = lc.rank(self.g, min_count=2)
        self.assertEqual([t for t, _ in items], ["a <NUM>", "b <NUM>"])

    def test_top_limit(self):
        items = lc.rank(self.g, top=1)
        self.assertEqual([t for t, _ in items], ["a <NUM>"])


class ReportTests(unittest.TestCase):
    def test_json_shares_sum_to_about_100(self):
        g = lc.cluster(["x 1\n", "x 2\n", "y\n", "y\n"])
        items = lc.rank(g)
        rep = lc.build_report(g, items, 1)
        self.assertEqual(rep["total_lines"], 4)
        self.assertEqual(rep["clusters"], 2)
        self.assertEqual(sum(c["count"] for c in rep["clusters_detail"]), 4)
        self.assertAlmostEqual(sum(c["share"] for c in rep["clusters_detail"]), 100.0, places=1)
        json.dumps(rep)  # must be serializable

    def test_render_empty(self):
        self.assertEqual(lc.render_table(0, [], 1), "no log lines\n")

    def test_shorten_long_template(self):
        self.assertEqual(lc._shorten("a" * 10, 5), "aa...")


class CliTests(unittest.TestCase):
    def _write(self, text):
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".log")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_table_output(self):
        path = self._write("GET /a 200\nGET /b 200\nPOST /a 500\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = lc.main([path])
        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIn("3 lines, 3 clusters shown", out)
        self.assertIn("GET /a <NUM>", out)
        self.assertIn("POST /a <NUM>", out)

    def test_json_output(self):
        path = self._write("a 1\na 2\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(lc.main([path, "--json"]), 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["clusters_detail"][0]["count"], 2)

    def test_missing_file_exit_1(self):
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            self.assertEqual(lc.main(["does-not-exist.log"]), 1)
        self.assertIn("cannot read", err.getvalue())

    def test_bad_args_exit_2(self):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            lc.main(["x", "--top", "0"])
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
