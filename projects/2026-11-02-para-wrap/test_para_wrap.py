import io
import itertools
import json
import unittest
from contextlib import redirect_stdout

from para_wrap import (align, greedy_breaks, lines_from_breaks, main,
                       optimal_breaks, raggedness, wrap_text)


def brute_force_best(words, width):
    """Try every set of break points; return minimal raggedness."""
    n = len(words)
    best = None
    for mask in range(1 << (n - 1)):
        breaks = [i + 1 for i in range(n - 1) if mask >> i & 1] + [n]
        lines = lines_from_breaks(words, breaks)
        if any(len(" ".join(l)) > width and len(l) > 1 for l in lines):
            continue
        score = raggedness(lines, width)
        if best is None or score < best:
            best = score
    return best


class TestBreaks(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(greedy_breaks([], 10), [])
        self.assertEqual(optimal_breaks([], 10), [])

    def test_classic_example_beats_greedy(self):
        words = "aaa bb cc ddddd".split()
        g = lines_from_breaks(words, greedy_breaks(words, 6))
        o = lines_from_breaks(words, optimal_breaks(words, 6))
        self.assertEqual([" ".join(l) for l in g], ["aaa bb", "cc", "ddddd"])
        self.assertEqual([" ".join(l) for l in o], ["aaa", "bb cc", "ddddd"])
        self.assertEqual(raggedness(g, 6), 16)
        self.assertEqual(raggedness(o, 6), 10)

    def test_lines_never_exceed_width(self):
        words = ("the quick brown fox jumps over the lazy dog " * 5).split()
        for width in range(5, 40):
            for fn in (greedy_breaks, optimal_breaks):
                for l in lines_from_breaks(words, fn(words, width)):
                    self.assertLessEqual(len(" ".join(l)), width)

    def test_overlong_word_alone(self):
        words = ["a", "supercalifragilistic", "b"]
        lines = lines_from_breaks(words, optimal_breaks(words, 5))
        self.assertIn(["supercalifragilistic"], lines)
        self.assertEqual(sum(len(l) for l in lines), 3)

    def test_matches_brute_force(self):
        vocab = ["a", "bb", "ccc", "dddd", "eeeee", "ff"]
        for n in range(1, 8):
            for combo in itertools.islice(itertools.product(vocab, repeat=n), 40):
                words = list(combo)
                for width in (5, 7, 10):
                    o = lines_from_breaks(words, optimal_breaks(words, width))
                    self.assertEqual(raggedness(o, width),
                                     brute_force_best(words, width),
                                     (words, width))

    def test_optimal_never_worse_than_greedy(self):
        words = ("Lorem ipsum dolor sit amet consectetur adipiscing elit sed do "
                 "eiusmod tempor incididunt ut labore et dolore magna aliqua").split()
        for width in range(12, 50):
            g = lines_from_breaks(words, greedy_breaks(words, width))
            o = lines_from_breaks(words, optimal_breaks(words, width))
            self.assertLessEqual(raggedness(o, width), raggedness(g, width))


class TestAlign(unittest.TestCase):
    def test_justify(self):
        self.assertEqual(align(["a", "b", "c"], 9, "justify"), "a   b   c")
        self.assertEqual(align(["a", "b", "c"], 8, "justify"), "a   b  c")
        self.assertEqual(len(align(["ab", "cd", "e"], 10, "justify")), 10)

    def test_justify_last_and_single(self):
        self.assertEqual(align(["a", "b"], 9, "justify", last=True), "a b")
        self.assertEqual(align(["word"], 9, "justify"), "word")

    def test_right_center(self):
        self.assertEqual(align(["ab"], 6, "right"), "    ab")
        self.assertEqual(align(["ab"], 6, "center"), "  ab")


class TestWrapText(unittest.TestCase):
    def test_paragraphs_preserved(self):
        out, _ = wrap_text("one two\nthree\n\n\nfour five", 20)
        self.assertEqual(out, "one two three\n\nfour five")

    def test_bad_width(self):
        with self.assertRaises(ValueError):
            wrap_text("x", 0)


class TestCLI(unittest.TestCase):
    def run_cli(self, argv, stdin):
        import sys
        old = sys.stdin
        sys.stdin = io.StringIO(stdin)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                code = main(argv)
        finally:
            sys.stdin = old
        return code, buf.getvalue()

    def test_json(self):
        code, out = self.run_cli(["-w", "6", "--json"], "aaa bb cc ddddd")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["text"], "aaa\nbb cc\nddddd")
        self.assertEqual(data["raggedness"], 10)

    def test_compare(self):
        code, out = self.run_cli(["-w", "6", "--compare"], "aaa bb cc ddddd")
        self.assertIn("greedy (raggedness 16)", out)
        self.assertIn("optimal (raggedness 10)", out)
        self.assertIn("37.5% less ragged", out)


if __name__ == "__main__":
    unittest.main()
