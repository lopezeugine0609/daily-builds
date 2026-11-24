import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from fractions import Fraction as F

import dice_prob as dp


class TestDistribution(unittest.TestCase):
    def test_single_die(self):
        d = dp.distribution("d6")
        self.assertEqual(d, {i: F(1, 6) for i in range(1, 7)})

    def test_2d6(self):
        d = dp.distribution("2d6")
        self.assertEqual(d[7], F(6, 36))
        self.assertEqual(d[2], F(1, 36))
        self.assertEqual(sum(d.values()), 1)

    def test_constants_and_subtraction(self):
        d = dp.distribution("1d4-1d4+3")
        self.assertEqual(min(d), 0)
        self.assertEqual(max(d), 6)
        self.assertEqual(d[3], F(4, 16))

    def test_advantage(self):
        d = dp.distribution("2d20kh1")
        self.assertEqual(d[20], F(39, 400))
        self.assertEqual(d[1], F(1, 400))
        self.assertEqual(dp.stats(d)["mean"], F(5530, 400))

    def test_disadvantage(self):
        d = dp.distribution("2d20kl1")
        self.assertEqual(d[1], F(39, 400))

    def test_4d6_drop_lowest(self):
        d = dp.distribution("4d6dl1")
        self.assertEqual(d[18], F(21, 1296))
        self.assertEqual(d[3], F(1, 1296))
        self.assertEqual(dp.stats(d)["mean"], F(15869, 1296))

    def test_dp_matches_enumeration(self):
        for n, s, mode, m in [(4, 6, "kh", 3), (3, 8, "kl", 2), (5, 4, "dh", 2), (4, 5, "dl", 1)]:
            faces = list(range(1, s + 1))
            enum = dp.keep_dist(n, faces, mode, m)
            keep = m if mode.startswith("k") else n - m
            high = mode in ("kh", "dl")
            dpd = dp._keep_dp(n, tuple(faces), keep, high)
            self.assertEqual(enum, dpd, (n, s, mode, m))

    def test_large_keep_uses_dp(self):
        d = dp.distribution("10d20kh3")
        self.assertEqual(sum(d.values()), 1)
        self.assertEqual(max(d), 60)

    def test_fudge_and_percentile(self):
        d = dp.distribution("4dF")
        self.assertEqual(d[0], F(19, 81))
        self.assertEqual(len(dp.distribution("d%")), 100)

    def test_big_sum(self):
        d = dp.distribution("100d6")
        self.assertEqual(dp.stats(d)["mean"], 350)
        self.assertEqual(sum(d.values()), 1)

    def test_errors(self):
        for bad in ["", "3x6", "2d6+", "2d6kh3", "0d6", "d0", "2d6 5"]:
            with self.assertRaises(dp.DiceError, msg=bad):
                dp.distribution(bad)


class TestStatsAndQuery(unittest.TestCase):
    def test_stats_3d6(self):
        st = dp.stats(dp.distribution("3d6"))
        self.assertEqual(st["mean"], F(21, 2))
        self.assertEqual(st["variance"], F(35, 4))
        self.assertEqual(st["median"], 10)

    def test_prob(self):
        d = dp.distribution("2d6")
        self.assertEqual(dp.prob(d, ">=", 10), F(6, 36))
        self.assertEqual(dp.prob(d, "<", 3), F(1, 36))
        self.assertEqual(dp.prob(d, "=", 7), F(1, 6))
        self.assertEqual(dp.prob(d, ">", 12), 0)


class TestCLI(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = dp.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_text(self):
        code, out, _ = self.run_cli("2d6", "-p", ">=10")
        self.assertEqual(code, 0)
        self.assertIn("P(X >= 10) = 1/6", out)
        self.assertIn("7  16.67%", out)

    def test_json(self):
        code, out, _ = self.run_cli("d4", "--json", "-p", "=2")
        data = json.loads(out)
        self.assertEqual(data["query"]["p"], "1/4")
        self.assertEqual(data["stats"]["mean"], "5/2")

    def test_error_exit(self):
        code, _, err = self.run_cli("2q6")
        self.assertEqual(code, 2)
        self.assertIn("error:", err)
        code, _, _ = self.run_cli("2d6", "-p", "~5")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
