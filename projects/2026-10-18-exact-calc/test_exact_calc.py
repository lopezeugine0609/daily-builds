import io
import unittest
from contextlib import redirect_stdout, redirect_stderr
from fractions import Fraction as F

from exact_calc import CalcError, Calculator, evaluate, fmt, main, to_rpn, tokenize


class TestEvaluate(unittest.TestCase):
    def test_exact_decimal(self):
        self.assertEqual(evaluate("0.1 + 0.2"), F(3, 10))

    def test_precedence(self):
        self.assertEqual(evaluate("2 + 3 * 4"), 14)
        self.assertEqual(evaluate("(2 + 3) * 4"), 20)
        self.assertEqual(evaluate("10 - 4 - 3"), 3)
        self.assertEqual(evaluate("100 / 10 / 5"), 2)

    def test_power_right_assoc(self):
        self.assertEqual(evaluate("2 ^ 3 ^ 2"), 512)
        self.assertEqual(evaluate("2 ** 10"), 1024)

    def test_unary(self):
        self.assertEqual(evaluate("-2 ^ 2"), -4)
        self.assertEqual(evaluate("(-2) ^ 2"), 4)
        self.assertEqual(evaluate("3 - -2"), 5)
        self.assertEqual(evaluate("-(1 + 2) * 3"), -9)
        self.assertEqual(evaluate("2 * -3"), -6)
        self.assertEqual(evaluate("+5"), 5)

    def test_fractions(self):
        self.assertEqual(evaluate("1/3 + 1/6"), F(1, 2))
        self.assertEqual(evaluate("2 ^ -2"), F(1, 4))
        self.assertEqual(evaluate("7 // 2"), 3)
        self.assertEqual(evaluate("-7 // 2"), -4)
        self.assertEqual(evaluate("7 % 3"), 1)
        self.assertEqual(evaluate("1e-3 * 1000"), 1)
        self.assertEqual(evaluate(".5 * 4"), 2)

    def test_functions(self):
        self.assertEqual(evaluate("max(1, 7/2, 3)"), F(7, 2))
        self.assertEqual(evaluate("min(4, -1)"), -1)
        self.assertEqual(evaluate("gcd(12, 18, 30)"), 6)
        self.assertEqual(evaluate("lcm(4, 6)"), 12)
        self.assertEqual(evaluate("sqrt(9/16)"), F(3, 4))
        self.assertEqual(evaluate("abs(-5/2) + floor(7/2) + ceil(1/3)"), F(13, 2))
        self.assertEqual(evaluate("max(1 + 2, 2 * 2) ^ 2"), 16)
        self.assertEqual(evaluate("(9/4) ^ 0.5"), F(3, 2))

    def test_errors(self):
        for expr, msg in [
            ("1 / 0", "division by zero"),
            ("(1 + 2", "unbalanced '('"),
            ("1 + 2)", "unbalanced ')'"),
            ("1 +", "incomplete"),
            ("* 2", "missing left operand"),
            ("sqrt(2)", "irrational"),
            ("sqrt(1, 2)", "takes 1"),
            ("gcd(1/2, 2)", "integers"),
            ("y + 1", "unknown variable"),
            ("2 $ 3", "unexpected character"),
            ("2 ^ (1/3)", "non-integer exponent"),
            ("()", "empty parentheses"),
            ("max()", "empty function argument"),
            ("1, 2", "comma outside"),
        ]:
            with self.subTest(expr=expr):
                with self.assertRaises(CalcError) as cm:
                    evaluate(expr)
                self.assertIn(msg, str(cm.exception))


class TestRpn(unittest.TestCase):
    def test_rpn_shape(self):
        rpn = to_rpn(tokenize("3 + 4 * 2"))
        self.assertEqual([t[1] if len(t) > 1 else t[0] for t in rpn], [3, 4, 2, "*", "+"])

    def test_function_argc(self):
        rpn = to_rpn(tokenize("max(1, 2, 3)"))
        self.assertEqual(rpn[-1], ("call", "max", 3))


class TestCalculator(unittest.TestCase):
    def test_variables_and_last(self):
        c = Calculator()
        self.assertEqual(c.run("x = 3/4"), F(3, 4))
        self.assertEqual(c.run("x * 4"), 3)
        self.assertEqual(c.run("_ + 1"), 4)
        with self.assertRaises(CalcError):
            c.run("max = 3")


class TestFormat(unittest.TestCase):
    def test_fmt(self):
        self.assertEqual(fmt(F(4)), "4")
        self.assertEqual(fmt(F(1, 3)), "1/3 ≈ 0.333333333333")
        self.assertEqual(fmt(F(-2, 3), 4), "-0.6667")
        self.assertEqual(fmt(F(1, 8), 2), "0.12")  # banker's rounding of 12.5
        self.assertEqual(fmt(F(5, 2), 0), "2")


class TestCli(unittest.TestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_cli_ok(self):
        code, out, _ = self.run_cli(["-d", "3", "1/3 + 1/3"])
        self.assertEqual((code, out.strip()), (0, "0.667"))

    def test_cli_error_exit(self):
        code, _, err = self.run_cli(["1/0"])
        self.assertEqual(code, 1)
        self.assertIn("division by zero", err)


if __name__ == "__main__":
    unittest.main()
