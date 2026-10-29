import io
import json
import os
import random
import string
import tempfile
import unittest
from contextlib import redirect_stdout

from bktree import BKTree, levenshtein, main

WORDS = ["book", "books", "cake", "boo", "boon", "cook", "cape", "cart",
         "hook", "look", "take", "bake", "brook"]


class TestLevenshtein(unittest.TestCase):
    def test_known(self):
        self.assertEqual(levenshtein("kitten", "sitting"), 3)
        self.assertEqual(levenshtein("flaw", "lawn"), 2)
        self.assertEqual(levenshtein("", "abc"), 3)
        self.assertEqual(levenshtein("abc", ""), 3)
        self.assertEqual(levenshtein("same", "same"), 0)

    def test_symmetric(self):
        self.assertEqual(levenshtein("abcdef", "azced"), levenshtein("azced", "abcdef"))

    def test_limit_early_exit(self):
        self.assertEqual(levenshtein("a", "abcdefgh", limit=2), 3)
        self.assertEqual(levenshtein("kitten", "sitting", limit=1), 2)
        self.assertEqual(levenshtein("kitten", "sitting", limit=3), 3)


class TestBKTree(unittest.TestCase):
    def setUp(self):
        self.tree = BKTree(WORDS)

    def test_size_and_dupes(self):
        self.assertEqual(len(self.tree), len(WORDS))
        self.assertFalse(self.tree.add("book"))
        self.assertEqual(len(self.tree), len(WORDS))

    def test_contains(self):
        self.assertIn("cake", self.tree)
        self.assertNotIn("caek", self.tree)

    def test_search_exact_radius(self):
        # "boon" is distance 2 (k->o, insert n), so it is excluded
        self.assertEqual(self.tree.search("bok", 1), [(1, "boo"), (1, "book")])
        self.assertEqual(self.tree.search("bok", 2)[:3],
                         [(1, "boo"), (1, "book"), (2, "bake")])

    def test_empty_tree(self):
        t = BKTree()
        self.assertEqual(t.search("x", 3), [])
        self.assertEqual(t.closest("x"), [])
        self.assertEqual(t.depth(), 0)

    def test_negative_radius(self):
        with self.assertRaises(ValueError):
            self.tree.search("x", -1)

    def test_closest(self):
        self.assertEqual(self.tree.closest("cakes", 1), [(1, "cake")])
        self.assertEqual(len(self.tree.closest("zzzzzzzz", 3)), 3)

    def test_matches_brute_force(self):
        rnd = random.Random(42)
        words = {"".join(rnd.choice("abcde") for _ in range(rnd.randint(1, 7)))
                 for _ in range(400)}
        tree = BKTree(words)
        for _ in range(60):
            q = "".join(rnd.choice("abcdef") for _ in range(rnd.randint(0, 8)))
            for d in range(4):
                want = sorted((levenshtein(q, w), w) for w in words
                              if levenshtein(q, w) <= d)
                self.assertEqual(tree.search(q, d), want, (q, d))

    def test_pruning_happens(self):
        rnd = random.Random(1)
        words = {"".join(rnd.choice(string.ascii_lowercase)
                         for _ in range(rnd.randint(2, 14)))
                 for _ in range(5000)}
        tree = BKTree(words)
        st = {}
        tree.search("abcdefgh", 1, st)
        self.assertLess(st["visited"], len(tree) // 4)


class TestCLI(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("# comment\n" + "\n".join(WORDS + ["Book"]) + "\n")

    def tearDown(self):
        os.remove(self.path)

    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main([self.path, *args])
        return code, buf.getvalue()

    def test_text(self):
        code, out = self.run_cli("cake", "cak", "-d", "1", "-n", "3")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(),
                         ["cake: ok", "cak: ? -> cake (1)"])

    def test_no_match_exit_code(self):
        code, out = self.run_cli("xyzzy", "-d", "1")
        self.assertEqual(code, 1)
        self.assertIn("xyzzy: no match", out)

    def test_json_and_ignore_case(self):
        code, out = self.run_cli("BOOK", "-i", "-d", "0", "--json")
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["words"], len(WORDS))  # "Book" folded into "book"
        self.assertTrue(data["results"][0]["exact"])

    def test_missing_file(self):
        code = main([self.path + ".nope", "x"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
