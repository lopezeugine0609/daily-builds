import io
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime

from cron_next import Cron, CronError, parse_field, main


class ParseFieldTests(unittest.TestCase):
    def test_star_step(self):
        self.assertEqual(parse_field("*/15", "m", 0, 59), {0, 15, 30, 45})

    def test_range_list(self):
        self.assertEqual(parse_field("1-3,10", "m", 0, 59), {1, 2, 3, 10})

    def test_range_step(self):
        self.assertEqual(parse_field("10-20/5", "m", 0, 59), {10, 15, 20})

    def test_start_step(self):
        self.assertEqual(parse_field("50/5", "m", 0, 59), {50, 55})

    def test_names(self):
        c = Cron("0 0 * jan-mar mon-fri")
        self.assertEqual(c.months, {1, 2, 3})
        self.assertEqual(c.dows, {1, 2, 3, 4, 5})

    def test_seven_is_sunday(self):
        self.assertEqual(Cron("0 0 * * 7").dows, {0})

    def test_errors(self):
        for bad in ["* * * *", "60 * * * *", "* * 0 * *", "*/0 * * * *",
                    "5-1 * * * *", "* * * foo *", "1,,2 * * * *"]:
            with self.subTest(bad=bad):
                with self.assertRaises(CronError):
                    Cron(bad)


class NextTests(unittest.TestCase):
    def test_every_15(self):
        c = Cron("*/15 * * * *")
        got = c.upcoming(datetime(2026, 1, 1, 10, 7), 3)
        self.assertEqual(got, [datetime(2026, 1, 1, 10, 15),
                               datetime(2026, 1, 1, 10, 30),
                               datetime(2026, 1, 1, 10, 45)])

    def test_strictly_after(self):
        c = Cron("0 * * * *")
        self.assertEqual(c.next_after(datetime(2026, 1, 1, 10, 0)),
                         datetime(2026, 1, 1, 11, 0))

    def test_weekdays_skip_weekend(self):
        # 2026-10-09 is a Friday
        c = Cron("30 9 * * mon-fri")
        self.assertEqual(c.next_after(datetime(2026, 10, 9, 10, 0)),
                         datetime(2026, 10, 12, 9, 30))

    def test_month_rollover_and_year(self):
        c = Cron("@yearly")
        self.assertEqual(c.next_after(datetime(2026, 6, 1)), datetime(2027, 1, 1, 0, 0))

    def test_leap_day(self):
        c = Cron("0 12 29 2 *")
        self.assertEqual(c.next_after(datetime(2026, 3, 1)), datetime(2028, 2, 29, 12, 0))

    def test_dom_or_dow(self):
        # 1st of month OR any Monday (Vixie semantics)
        c = Cron("0 0 1 * mon")
        got = c.upcoming(datetime(2026, 10, 6), 3)
        self.assertEqual(got, [datetime(2026, 10, 12), datetime(2026, 10, 19),
                               datetime(2026, 10, 26)])
        self.assertEqual(c.next_after(datetime(2026, 10, 26, 1)), datetime(2026, 11, 1))

    def test_impossible(self):
        with self.assertRaises(CronError):
            Cron("0 0 31 2 *").next_after(datetime(2026, 1, 1))

    def test_matches(self):
        c = Cron("*/5 9-17 * * *")
        self.assertTrue(c.matches(datetime(2026, 1, 1, 9, 55)))
        self.assertFalse(c.matches(datetime(2026, 1, 1, 18, 0)))


class CliTests(unittest.TestCase):
    def test_output(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(["@daily", "-n", "2", "--from", "2026-10-06 08:00"])
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue().splitlines(),
                         ["2026-10-07 00:00  Wed", "2026-10-08 00:00  Thu"])

    def test_bad_expr(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["bad"]), 2)


if __name__ == "__main__":
    unittest.main()
