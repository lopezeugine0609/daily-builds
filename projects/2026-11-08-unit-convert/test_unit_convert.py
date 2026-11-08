import contextlib
import io
import unittest
from fractions import Fraction

from unit_convert import UnitError, convert, main, parse_quantity, parse_unit


class ParseUnitTests(unittest.TestCase):
    def test_simple_unit(self):
        self.assertEqual(parse_unit("km"), (Fraction(1000), (1, 0, 0)))

    def test_compound_speed(self):
        f, d = parse_unit("km/h")
        self.assertEqual(f, Fraction(5, 18))
        self.assertEqual(d, (1, 0, -1))

    def test_powers(self):
        f, d = parse_unit("km^2")
        self.assertEqual((f, d), (Fraction(10**6), (2, 0, 0)))

    def test_leading_slash_reciprocal(self):
        f, d = parse_unit("/s")
        self.assertEqual((f, d), (Fraction(1), (0, 0, -1)))

    def test_derived_newton_expansion(self):
        f, d = parse_unit("kg*m/s^2")
        self.assertEqual((f, d), (Fraction(1), (1, 1, -2)))

    def test_unknown_unit(self):
        with self.assertRaisesRegex(UnitError, "unknown unit 'parsec'"):
            parse_unit("parsec")

    def test_bad_syntax(self):
        for bad in ["", "km//h", "km*", "m^", "m^x", "m h", "3m"]:
            with self.subTest(bad=bad):
                with self.assertRaises(UnitError):
                    parse_unit(bad)


class QuantityTests(unittest.TestCase):
    def test_decimal_is_exact(self):
        self.assertEqual(parse_quantity("0.1 m"), (Fraction(1, 10), "m"))

    def test_exponent_and_sign(self):
        self.assertEqual(parse_quantity("-2.5e3 kg"), (Fraction(-2500), "kg"))

    def test_no_number(self):
        with self.assertRaises(UnitError):
            parse_quantity("km/h")


class ConvertTests(unittest.TestCase):
    def test_speed_exact(self):
        r = convert("5 km/h", "m/s")
        self.assertEqual(r.result, Fraction(25, 18))

    def test_imperial_length_exact(self):
        # 1 mi = 5280 ft exactly
        self.assertEqual(convert("1 mi", "ft").result, Fraction(5280))

    def test_pound_to_kg(self):
        self.assertEqual(convert("1 lb", "kg").result, Fraction(45359237, 100000000))

    def test_us_gallon_in_litres(self):
        # 1 US gal = 3.785411784 L exactly
        self.assertEqual(convert("1 gal", "L").result, Fraction(3785411784, 10**9))

    def test_energy_unit_equivalence(self):
        # 1 J = 1 N*m
        self.assertEqual(convert("1 J", "N*m").result, Fraction(1))

    def test_pressure_compound(self):
        # 1 Pa = 1 N/m^2
        self.assertEqual(convert("1 Pa", "N/m^2").result, Fraction(1))

    def test_incompatible_dimensions(self):
        with self.assertRaisesRegex(UnitError, "incompatible"):
            convert("1 km", "kg")

    def test_speed_vs_length_incompatible(self):
        with self.assertRaises(UnitError):
            convert("1 km/h", "m")

    def test_temperatures(self):
        self.assertEqual(convert("100 C", "F").result, Fraction(212))
        self.assertEqual(convert("32 F", "C").result, Fraction(0))
        self.assertEqual(convert("0 C", "K").result, Fraction(27315, 100))
        self.assertEqual(convert("-40 F", "C").result, Fraction(-40))

    def test_temperature_to_non_temperature_rejected(self):
        with self.assertRaises(UnitError):
            convert("1 C", "m")
        with self.assertRaises(UnitError):
            convert("1 m", "F")


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(argv)
            except SystemExit as e:  # argparse errors
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def test_text_output(self):
        code, out, _ = self.run_cli(["5 km/h", "m/s"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "5 km/h = 1.38888888889 m/s\n")

    def test_exact_output(self):
        code, out, _ = self.run_cli(["--exact", "5 km/h", "m/s"])
        self.assertEqual(out, "5 km/h = 25/18 m/s\n")

    def test_json_output(self):
        code, out, _ = self.run_cli(["--json", "1 mi", "ft"])
        self.assertEqual(code, 0)
        self.assertIn('"exact": "5280"', out)
        self.assertIn('"result": 5280.0', out)

    def test_error_exit_code(self):
        code, out, err = self.run_cli(["1 km", "kg"])
        self.assertEqual(code, 1)
        self.assertIn("incompatible", err)
        self.assertEqual(out, "")

    def test_missing_args_exit_2(self):
        code, _, _ = self.run_cli(["1 km"])
        self.assertEqual(code, 2)

    def test_list(self):
        code, out, _ = self.run_cli(["--list"])
        self.assertEqual(code, 0)
        self.assertIn("km", out)
        self.assertIn("F", out)


if __name__ == "__main__":
    unittest.main()
