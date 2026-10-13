import io
import unittest
from contextlib import redirect_stdout

from semver import Range, Version, main


def V(s):
    return Version.parse(s)


class TestParse(unittest.TestCase):
    def test_roundtrip(self):
        for s in ["1.2.3", "0.0.0", "1.0.0-alpha.1", "1.0.0+build.5", "2.1.0-rc.1+sha.abc"]:
            self.assertEqual(str(V(s)), s)

    def test_v_prefix(self):
        self.assertEqual(str(V("v1.2.3")), "1.2.3")

    def test_invalid(self):
        for s in ["1.2", "01.2.3", "1.2.3-", "1.2.3-01", "a.b.c", ""]:
            with self.assertRaises(ValueError, msg=s):
                V(s)


class TestOrdering(unittest.TestCase):
    def test_spec_precedence_chain(self):
        chain = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta",
                 "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]
        vs = [V(s) for s in chain]
        self.assertEqual(sorted(reversed(vs)), vs)
        for a, b in zip(vs, vs[1:]):
            self.assertLess(a, b)

    def test_build_ignored(self):
        self.assertEqual(V("1.0.0+a"), V("1.0.0+b"))

    def test_numeric_not_lexical(self):
        self.assertLess(V("1.9.0"), V("1.10.0"))


class TestBump(unittest.TestCase):
    def test_parts(self):
        self.assertEqual(str(V("1.2.3").bump("major")), "2.0.0")
        self.assertEqual(str(V("1.2.3").bump("minor")), "1.3.0")
        self.assertEqual(str(V("1.2.3-beta").bump("patch")), "1.2.4")

    def test_prerelease(self):
        self.assertEqual(str(V("1.2.3").bump("prerelease")), "1.2.4-0")
        self.assertEqual(str(V("1.2.3").bump("prerelease", "beta")), "1.2.4-beta.0")
        self.assertEqual(str(V("1.2.4-beta.0").bump("prerelease", "beta")), "1.2.4-beta.1")
        self.assertEqual(str(V("1.2.4-beta.3").bump("prerelease", "rc")), "1.2.4-rc.0")
        self.assertEqual(str(V("1.2.4-alpha").bump("prerelease")), "1.2.4-alpha.0")


class TestRange(unittest.TestCase):
    def check(self, rng, yes, no):
        r = Range(rng)
        for v in yes:
            self.assertTrue(r.satisfied_by(v), f"{v} should satisfy {rng}")
        for v in no:
            self.assertFalse(r.satisfied_by(v), f"{v} should NOT satisfy {rng}")

    def test_caret(self):
        self.check("^1.2.3", ["1.2.3", "1.9.9"], ["1.2.2", "2.0.0", "2.0.0-0"])
        self.check("^0.2.3", ["0.2.3", "0.2.9"], ["0.3.0"])
        self.check("^0.0.3", ["0.0.3"], ["0.0.4"])
        self.check("^1.x", ["1.0.0", "1.5.0"], ["2.0.0"])

    def test_tilde(self):
        self.check("~1.2.3", ["1.2.3", "1.2.99"], ["1.3.0"])
        self.check("~1", ["1.0.0", "1.9.0"], ["2.0.0"])

    def test_comparators_and_space(self):
        self.check(">=1.2.0 <2.0.0", ["1.2.0", "1.99.0"], ["1.1.9", "2.0.0"])
        self.check(">= 1.2.0", ["1.2.0"], ["1.1.0"])

    def test_wildcards(self):
        self.check("*", ["0.0.1", "99.0.0"], ["1.0.0-beta"])
        self.check("1.2.x", ["1.2.0", "1.2.9"], ["1.3.0"])
        self.check(">1.2", ["1.3.0"], ["1.2.9"])
        self.check("<=1.2", ["1.2.9"], ["1.3.0"])

    def test_hyphen(self):
        self.check("1.2.3 - 2.3.4", ["1.2.3", "2.3.4"], ["2.3.5", "1.2.2"])
        self.check("1.2 - 2.3", ["1.2.0", "2.3.9"], ["2.4.0"])

    def test_or(self):
        self.check("^1.0.0 || ^3.0.0", ["1.5.0", "3.1.0"], ["2.0.0"])

    def test_prerelease_rule(self):
        self.check(">=1.2.3-alpha.1", ["1.2.3-alpha.7", "1.2.3", "1.3.0"], ["1.3.0-beta"])

    def test_max_satisfying(self):
        r = Range("~1.2.0")
        self.assertEqual(str(r.max_satisfying(["1.2.0", "1.2.10", "1.3.0", "1.2.9"])), "1.2.10")
        self.assertIsNone(Range("^5").max_satisfying(["1.0.0"]))

    def test_bad_range(self):
        with self.assertRaises(ValueError):
            Range("^banana")


class TestCLI(unittest.TestCase):
    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(args))
        return code, buf.getvalue().split()

    def test_sort(self):
        code, out = self.run_cli("sort", "1.10.0", "1.2.0", "1.2.0-rc.1")
        self.assertEqual((code, out), (0, ["1.2.0-rc.1", "1.2.0", "1.10.0"]))

    def test_compare(self):
        self.assertEqual(self.run_cli("compare", "1.0.0", "1.0.0-rc.1"), (0, ["1"]))

    def test_satisfies_none(self):
        self.assertEqual(self.run_cli("satisfies", "^2", "1.0.0")[0], 1)


if __name__ == "__main__":
    unittest.main()
