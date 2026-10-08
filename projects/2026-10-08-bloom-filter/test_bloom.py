import contextlib
import io
import os
import random
import string
import tempfile
import unittest

from bloom import BloomFilter, main


def rand_words(n, seed):
    rng = random.Random(seed)
    return ["".join(rng.choices(string.ascii_lowercase, k=12)) for _ in range(n)]


class TestBloomFilter(unittest.TestCase):
    def test_sizing_formula(self):
        bf = BloomFilter.for_capacity(1000, 0.01)
        self.assertEqual(bf.m, 9586)
        self.assertEqual(bf.k, 7)

    def test_no_false_negatives(self):
        bf = BloomFilter.for_capacity(2000, 0.01)
        words = rand_words(2000, 1)
        for w in words:
            bf.add(w)
        self.assertTrue(all(w in bf for w in words))

    def test_false_positive_rate_near_target(self):
        bf = BloomFilter.for_capacity(5000, 0.01)
        for w in rand_words(5000, 2):
            bf.add(w)
        probes = [w.upper() for w in rand_words(20000, 3)]  # disjoint set
        fp = sum(p in bf for p in probes) / len(probes)
        self.assertLess(fp, 0.02)
        self.assertAlmostEqual(bf.estimated_fp_rate(), 0.01, delta=0.002)

    def test_empty_filter_contains_nothing(self):
        bf = BloomFilter(64, 3)
        self.assertNotIn("x", bf)
        self.assertEqual(bf.bits_set(), 0)

    def test_bytes_and_str(self):
        bf = BloomFilter(256, 4)
        bf.add(b"raw")
        self.assertIn("raw", bf)  # same UTF-8 bytes

    def test_union(self):
        a, b = BloomFilter(512, 4), BloomFilter(512, 4)
        a.add("apple")
        b.add("banana")
        u = a.union(b)
        self.assertIn("apple", u)
        self.assertIn("banana", u)
        self.assertEqual(u.count, 2)
        with self.assertRaises(ValueError):
            a.union(BloomFilter(256, 4))

    def test_roundtrip(self):
        bf = BloomFilter.for_capacity(100, 0.05)
        for w in ["a", "b", "c"]:
            bf.add(w)
        clone = BloomFilter.from_dict(bf.to_dict())
        self.assertEqual(clone.bits, bf.bits)
        self.assertEqual((clone.m, clone.k, clone.count), (bf.m, bf.k, 3))

    def test_invalid_args(self):
        for args in [(0, 1), (8, 0)]:
            with self.assertRaises(ValueError):
                BloomFilter(*args)
        with self.assertRaises(ValueError):
            BloomFilter.for_capacity(10, 1.5)


class TestCLI(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(list(argv))
        return code, out.getvalue()

    def test_build_query_info(self):
        with tempfile.TemporaryDirectory() as d:
            words = os.path.join(d, "w.txt")
            path = os.path.join(d, "f.json")
            with open(words, "w", encoding="utf-8") as f:
                f.write("alpha\nbeta\n\ngamma\n")
            code, out = self.run_cli("build", words, "-o", path)
            self.assertEqual(code, 0)
            self.assertIn("3 items", out)
            code, out = self.run_cli("query", path, "alpha", "gamma")
            self.assertEqual(code, 0)
            self.assertEqual(out.count("probably present"), 2)
            code, out = self.run_cli("info", path)
            self.assertIn("items added:     3", out)

    def test_size(self):
        code, out = self.run_cli("size", "1000", "0.01")
        self.assertIn("m=9586", out)
        self.assertIn("k=7", out)


if __name__ == "__main__":
    unittest.main()
