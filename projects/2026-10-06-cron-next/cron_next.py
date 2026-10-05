#!/usr/bin/env python
"""cron_next: parse standard 5-field cron expressions and list upcoming run times.

Fields: minute hour day-of-month month day-of-week
Supports: *  numbers  ranges (a-b)  lists (a,b,c)  steps (*/n, a-b/n, a/n)
          month names (jan-dec), weekday names (sun-sat), 7 == Sunday,
          and macros @yearly @annually @monthly @weekly @daily @midnight @hourly.

Day matching follows Vixie cron: if BOTH day-of-month and day-of-week are
restricted (not '*'), a day matches when EITHER field matches.
"""
import argparse
import sys
from datetime import datetime, timedelta

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec"]
DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]

MACROS = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}

# (name, low, high, names-for-aliases, alias-offset)
FIELDS = [
    ("minute", 0, 59, None, 0),
    ("hour", 0, 23, None, 0),
    ("day-of-month", 1, 31, None, 0),
    ("month", 1, 12, MONTHS, 1),
    ("day-of-week", 0, 7, DAYS, 0),
]


class CronError(ValueError):
    pass


def _value(tok, name, lo, hi, names, offset):
    t = tok.lower()
    if names and t in names:
        return names.index(t) + offset
    if not t.isdigit():
        raise CronError(f"{name}: invalid value {tok!r}")
    v = int(t)
    if not lo <= v <= hi:
        raise CronError(f"{name}: {v} out of range {lo}-{hi}")
    return v


def parse_field(text, name, lo, hi, names=None, offset=0):
    """Return the sorted set of integers a single cron field allows."""
    result = set()
    for part in text.split(","):
        if not part:
            raise CronError(f"{name}: empty list element in {text!r}")
        step, orig = 1, part
        if "/" in part:
            part, step_s = part.split("/", 1)
            if not step_s.isdigit() or int(step_s) == 0:
                raise CronError(f"{name}: invalid step {step_s!r}")
            step = int(step_s)
        if part == "*":
            start, end = lo, hi
        elif "-" in part:
            a, b = part.split("-", 1)
            start = _value(a, name, lo, hi, names, offset)
            end = _value(b, name, lo, hi, names, offset)
            if start > end:
                raise CronError(f"{name}: range {start}-{end} is backwards")
        else:
            start = _value(part, name, lo, hi, names, offset)
            # "a/n" means a, a+n, ... up to the max
            end = hi if "/" in orig else start
        result.update(range(start, end + 1, step))
    return result


class Cron:
    def __init__(self, expr):
        self.expr = expr.strip()
        text = MACROS.get(self.expr.lower(), self.expr)
        parts = text.split()
        if len(parts) != 5:
            raise CronError(f"expected 5 fields, got {len(parts)}: {expr!r}")
        sets = [parse_field(p, *spec) for p, spec in zip(parts, FIELDS)]
        self.minutes, self.hours, self.doms, self.months, dows = sets
        self.dows = {d % 7 for d in dows}  # 7 -> Sunday (0)
        self.dom_star = parts[2].startswith("*")
        self.dow_star = parts[4].startswith("*")

    def _day_ok(self, d):
        dom_ok = d.day in self.doms
        dow_ok = (d.isoweekday() % 7) in self.dows  # Mon=1..Sun=0
        if self.dom_star and self.dow_star:
            return True
        if self.dom_star:
            return dow_ok
        if self.dow_star:
            return dom_ok
        return dom_ok or dow_ok

    def matches(self, dt):
        return (dt.minute in self.minutes and dt.hour in self.hours
                and dt.month in self.months and self._day_ok(dt))

    def next_after(self, dt):
        """First matching time strictly after dt (second precision dropped)."""
        t = dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
        limit = t.year + 30  # e.g. Feb 29 schedules need up to 8 years
        while t.year <= limit:
            if t.month not in self.months:
                y, m = (t.year + 1, 1) if t.month == 12 else (t.year, t.month + 1)
                t = t.replace(year=y, month=m, day=1, hour=0, minute=0)
                continue
            if not self._day_ok(t):
                t = t.replace(hour=0, minute=0) + timedelta(days=1)
                continue
            if t.hour not in self.hours:
                t = t.replace(minute=0) + timedelta(hours=1)
                continue
            if t.minute not in self.minutes:
                t += timedelta(minutes=1)
                continue
            return t
        raise CronError(f"no run time found within 30 years for {self.expr!r}")

    def upcoming(self, start, count):
        out, t = [], start
        for _ in range(count):
            t = self.next_after(t)
            out.append(t)
        return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Show the next run times of a cron expression.")
    ap.add_argument("expr", help='cron expression, e.g. "*/15 9-17 * * mon-fri"')
    ap.add_argument("-n", "--count", type=int, default=5, help="how many runs to show (default 5)")
    ap.add_argument("--from", dest="start", help="start time 'YYYY-MM-DD HH:MM' (default: now)")
    args = ap.parse_args(argv)
    try:
        cron = Cron(args.expr)
        start = datetime.strptime(args.start, "%Y-%m-%d %H:%M") if args.start else datetime.now()
        for t in cron.upcoming(start, args.count):
            print(t.strftime("%Y-%m-%d %H:%M  %a"))
    except (CronError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
