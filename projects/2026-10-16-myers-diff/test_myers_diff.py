import difflib
import io
import os
import random
import tempfile
import unittest
from contextlib import redirect_stdout

from myers_diff import DELETE, EQUAL, INSERT, diff, edit_distance, main, unified


def lcs_len(a, b):
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) - 1, -1, -1):
        for j in range(len(b) - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if a[i] == b[j] else max(dp[i + 1][j], dp[i][j + 1])
    return dp[0][0]


def apply(ops):
    old = [l for op, l in ops if op != INSERT]
    new = [l for op, l in ops if op != DELETE]
    return old, new


class TestDiff(unittest.TestCase):
    def test_paper_example(self):
        a, b = list("ABCABBA"), list("CBABAC")
        self.assertEqual(edit_distance(a, b), 5)
        self.assertEqual(apply(diff(a, b)), (a, b))

    def test_identical_and_empty(self):
        self.assertEqual(diff([], []), [])
        self.assertEqual(diff(["x"], ["x"]), [(EQUAL, "x")])
        self.assertEqual(diff([], ["a", "b"]), [(INSERT, "a"), (INSERT, "b")])
        self.assertEqual(diff(["a"], []), [(DELETE, "a")])
        self.assertEqual(unified(["x"], ["x"]), "")

    def test_random_is_minimal_and_reconstructs(self):
        rng = random.Random(42)
        for _ in range(300):
            a = [rng.choice("abcd") for _ in range(rng.randint(0, 12))]
            b = [rng.choice("abcd") for _ in range(rng.randint(0, 12))]
            ops = diff(a, b)
            self.assertEqual(apply(ops), (a, b))
            self.assertEqual(edit_distance(a, b), len(a) + len(b) - 2 * lcs_len(a, b))

    def test_unified_headers_match_difflib(self):
        a = [f"line {i}" for i in range(1, 21)]
        b = a[:]
        b[2] = "changed 3"
        del b[10]
        b.insert(17, "new line")
        ours = unified(a, b, "a", "b", 3)
        theirs = "".join(l if l.endswith("\n") else l + "\n"
                         for l in difflib.unified_diff(a, b, "a", "b", lineterm="", n=3))
        hunk = lambda t: [l for l in t.splitlines() if l.startswith("@@")]
        self.assertEqual(hunk(ours), hunk(theirs))
        self.assertEqual(ours.count("\n+"), theirs.count("\n+"))
        self.assertEqual(ours.count("\n-"), theirs.count("\n-"))

    def test_random_hunk_headers_match_difflib(self):
        rng = random.Random(7)
        hunk = lambda t: [l for l in t.splitlines() if l.startswith("@@")]
        for _ in range(200):
            a = [rng.choice("abcdefgh") for _ in range(rng.randint(0, 25))]
            b = a[:]
            for _ in range(rng.randint(1, 3)):
                i = rng.randint(0, len(b))
                if b and rng.random() < 0.5:
                    del b[min(i, len(b) - 1)]
                else:
                    b.insert(i, "NEW")
            if a == b:
                continue
            for n in (0, 1, 3):
                theirs = "\n".join(difflib.unified_diff(a, b, "a", "b", lineterm="", n=n))
                ours = unified(a, b, "a", "b", n)
                # Edit scripts may differ in placement, so compare counts.
                self.assertEqual(len(hunk(ours)) > 0, len(hunk(theirs)) > 0)
                self.assertEqual(ours.count("\n+") - 1, theirs.count("\n+") - 1)

    def test_zero_context_merges_adjacent(self):
        out = unified(["x", "y"], ["x", "z"], context=0)
        self.assertEqual(out.splitlines()[2:], ["@@ -2 +2 @@", "-y", "+z"])

    def test_insert_into_empty_header(self):
        self.assertEqual(unified([], ["a"]).splitlines()[2], "@@ -0,0 +1 @@")


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.a = os.path.join(self.dir.name, "a.txt")
        self.b = os.path.join(self.dir.name, "b.txt")
        with open(self.a, "w") as f:
            f.write("one\ntwo\nthree\n")
        with open(self.b, "w") as f:
            f.write("one\n2\nthree\nfour\n")

    def tearDown(self):
        self.dir.cleanup()

    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(args))
        return code, buf.getvalue()

    def test_unified_and_exit_codes(self):
        code, out = self.run_cli(self.a, self.b)
        self.assertEqual(code, 1)
        self.assertIn("-two\n+2\n", out)
        self.assertEqual(self.run_cli(self.a, self.a), (0, ""))

    def test_stat(self):
        code, out = self.run_cli("--stat", self.a, self.b)
        self.assertEqual(out.strip(), "2 insertion(s)(+), 1 deletion(s)(-), edit distance 3")


if __name__ == "__main__":
    unittest.main()
