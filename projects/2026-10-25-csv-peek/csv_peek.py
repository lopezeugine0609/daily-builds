#!/usr/bin/env python
"""csv-peek: preview a CSV as an aligned table and profile its columns.

Standard library only. Sniffs the delimiter, infers per-column types
(int, float, bool, date, string), and reports null counts, distinct counts,
min/max/mean for numeric columns, and the most common value.
"""
import argparse
import csv
import io
import json
import statistics
import sys
from collections import Counter
from datetime import date

NULLS = {"", "na", "n/a", "null", "none", "nan", "-"}
BOOLS = {"true", "false", "yes", "no", "t", "f", "y", "n"}


def is_null(v):
    return v.strip().lower() in NULLS


def classify(v):
    """Return the narrowest type name for a single non-null cell."""
    s = v.strip()
    if "_" not in s:  # int()/float() accept "1_000"; CSV data should not
        try:
            int(s)
            return "int"
        except ValueError:
            pass
        try:
            f = float(s)
            if f == f and abs(f) != float("inf"):
                return "float"
        except ValueError:
            pass
    if s.lower() in BOOLS:
        return "bool"
    try:
        date.fromisoformat(s)
        return "date"
    except ValueError:
        pass
    return "string"


def infer_type(values):
    """Merge per-cell types: int+float -> float; anything mixed -> string."""
    kinds = {classify(v) for v in values if not is_null(v)}
    if not kinds:
        return "empty"
    if len(kinds) == 1:
        return kinds.pop()
    if kinds <= {"int", "float"}:
        return "float"
    return "string"


def read_csv(text, delimiter=None):
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    rows = [r for r in rows if r]
    if not rows:
        return [], [], delimiter
    header, body = rows[0], rows[1:]
    width = max(len(header), *(len(r) for r in body)) if body else len(header)
    header = header + [f"col{i + 1}" for i in range(len(header), width)]
    body = [r + [""] * (width - len(r)) for r in body]
    return header, body, delimiter


def profile(header, body):
    out = []
    for i, name in enumerate(header):
        col = [r[i] for r in body]
        present = [v.strip() for v in col if not is_null(v)]
        kind = infer_type(col)
        info = {
            "column": name,
            "type": kind,
            "nulls": len(col) - len(present),
            "distinct": len(set(present)),
        }
        if kind in ("int", "float"):
            nums = [float(v) for v in present]
            cast = int if kind == "int" else float
            info["min"] = cast(min(nums))
            info["max"] = cast(max(nums))
            info["mean"] = round(statistics.fmean(nums), 4)
        elif kind == "date" or kind == "string":
            if present:
                info["min"] = min(present)
                info["max"] = max(present)
        if present:
            val, n = Counter(present).most_common(1)[0]
            info["top"] = val
            info["top_count"] = n
        out.append(info)
    return out


def clip(s, n):
    return s if len(s) <= n else s[: max(n - 1, 0)] + "…"


def render_table(header, rows, max_width=24, types=None):
    numeric = {i for i, t in enumerate(types or []) if t in ("int", "float")}
    cells = [[clip(c, max_width) for c in header]] + [
        [clip(c, max_width) for c in r] for r in rows
    ]
    widths = [max(len(r[i]) for r in cells) for i in range(len(header))]

    def line(r):
        parts = []
        for i, c in enumerate(r):
            parts.append(c.rjust(widths[i]) if i in numeric and r is not cells[0] else c.ljust(widths[i]))
        return " | ".join(parts).rstrip()

    sep = "-+-".join("-" * w for w in widths)
    return "\n".join([line(cells[0]), sep] + [line(r) for r in cells[1:]])


def render_profile(prof):
    keys = ["column", "type", "nulls", "distinct", "min", "max", "mean", "top"]
    header = keys
    rows = []
    for p in prof:
        row = []
        for k in keys:
            v = p.get(k, "")
            if k == "top" and "top" in p:
                v = f"{p['top']} (x{p['top_count']})"
            row.append(str(v))
        rows.append(row)
    return render_table(header, rows, max_width=20)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Preview and profile a CSV file.")
    ap.add_argument("file", help="CSV path, or - for stdin")
    ap.add_argument("-n", "--rows", type=int, default=10, help="preview rows (default 10, 0 = none)")
    ap.add_argument("-d", "--delimiter", help="force delimiter (default: sniff)")
    ap.add_argument("-w", "--width", type=int, default=24, help="max cell width (default 24)")
    ap.add_argument("--no-stats", action="store_true", help="skip column profile")
    ap.add_argument("--json", action="store_true", help="emit profile as JSON")
    args = ap.parse_args(argv)

    try:
        if args.file == "-":
            text = sys.stdin.read()
        else:
            with open(args.file, newline="", encoding="utf-8-sig") as fh:
                text = fh.read()
    except OSError as e:
        print(f"csv-peek: {e}", file=sys.stderr)
        return 2

    delim = args.delimiter
    if delim == "\\t":
        delim = "\t"
    header, body, used = read_csv(text, delim)
    if not header:
        print("csv-peek: no data", file=sys.stderr)
        return 1
    prof = profile(header, body)

    if args.json:
        print(json.dumps({"rows": len(body), "columns": len(header),
                          "delimiter": used, "profile": prof}, indent=2))
        return 0

    print(f"{len(body)} rows x {len(header)} columns, delimiter {used!r}\n")
    if args.rows > 0:
        print(render_table(header, body[: args.rows], args.width, [p["type"] for p in prof]))
        if len(body) > args.rows:
            print(f"... {len(body) - args.rows} more rows")
        print()
    if not args.no_stats:
        print(render_profile(prof))
    return 0


if __name__ == "__main__":
    sys.exit(main())
