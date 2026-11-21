import io
import random
import unittest
from contextlib import redirect_stdout

from skiplist import SkipList, main


class TestSkipList(unittest.TestCase):
    def test_basic_mapping(self):
        sl = SkipList(seed=0)
        self.assertEqual(len(sl), 0)
        sl[5] = "a"
        sl[1] = "b"
        sl[3] = "c"
        self.assertEqual(list(sl), [1, 3, 5])
        self.assertEqual(sl[3], "c")
        self.assertIn(5, sl)
        self.assertNotIn(4, sl)
        sl[3] = "z"
        self.assertEqual(len(sl), 3)
        self.assertEqual(sl[3], "z")
        with self.assertRaises(KeyError):
            sl[4]
        self.assertEqual(sl.get(4, "d"), "d")

    def test_delete_and_pop(self):
        sl = SkipList({k: k * 10 for k in range(10)}, seed=1)
        del sl[4]
        self.assertNotIn(4, sl)
        self.assertEqual(sl.pop(9), 90)
        self.assertEqual(sl.pop(9, None), None)
        with self.assertRaises(KeyError):
            del sl[100]
        self.assertEqual(list(sl), [0, 1, 2, 3, 5, 6, 7, 8])
        sl.check()

    def test_rank_at_range(self):
        sl = SkipList([(k, str(k)) for k in range(0, 100, 10)], seed=2)
        self.assertEqual(sl.rank(0), 0)
        self.assertEqual(sl.rank(35), 4)
        self.assertEqual(sl.rank(1000), 10)
        self.assertEqual(sl.at(0), (0, "0"))
        self.assertEqual(sl.at(-1), (90, "90"))
        with self.assertRaises(IndexError):
            sl.at(10)
        self.assertEqual([k for k, _ in sl.range(25, 60)], [30, 40, 50])
        self.assertEqual([k for k, _ in sl.range(hi=20)], [0, 10])
        self.assertEqual([k for k, _ in sl.range(80)], [80, 90])

    def test_floor_ceiling(self):
        sl = SkipList([(k, None) for k in (10, 20, 30)], seed=3)
        self.assertEqual(sl.floor(25), 20)
        self.assertEqual(sl.floor(20), 20)
        self.assertIsNone(sl.floor(5))
        self.assertEqual(sl.ceiling(25), 30)
        self.assertIsNone(sl.ceiling(31))

    def test_randomized_against_dict(self):
        rng = random.Random(42)
        sl, ref = SkipList(seed=7), {}
        for step in range(3000):
            k = rng.randrange(300)
            if rng.random() < 0.6:
                sl[k] = step
                ref[k] = step
            elif k in ref:
                del sl[k]
                del ref[k]
            if step % 250 == 0:
                sl.check()
        sl.check()
        keys = sorted(ref)
        self.assertEqual(list(sl), keys)
        self.assertEqual(dict(sl.items()), ref)
        for i, k in enumerate(keys):
            self.assertEqual(sl.at(i)[0], k)
            self.assertEqual(sl.rank(k), i)

    def test_strings_and_bad_p(self):
        sl = SkipList([("pear", 1), ("apple", 2), ("fig", 3)])
        self.assertEqual(list(sl), ["apple", "fig", "pear"])
        with self.assertRaises(ValueError):
            SkipList(p=1)

    def test_delete_all_shrinks_levels(self):
        sl = SkipList([(k, k) for k in range(64)], seed=5)
        for k in range(64):
            del sl[k]
        self.assertEqual(len(sl), 0)
        self.assertEqual(sl._level, 1)
        sl[1] = 1
        sl.check()

    def test_cli(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["--seed", "1", "3", "1", "2", "3"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("3 unique keys", out)
        self.assertIn("counts: 1=1, 2=1, 3=2", out)
        self.assertIn("median: 2", out)


if __name__ == "__main__":
    unittest.main()
