#!/usr/bin/env python
"""log-cluster: group log lines into templates by masking variable tokens.

Each line is rewritten into a template where UUIDs, IPs, timestamps, hex
literals, quoted strings and numbers become placeholders. Lines with the same
template are one cluster. Output is ranked by count, with example lines.
Standard library only.
"""
import argparse
import json
import re
import sys
from collections import OrderedDict

# Order matters: more specific patterns run first so later ones do not eat them.
MASKS = [
    (re.compile(r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b"), "<UUID>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"), "<TS>"),
    (re.compile(r"\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b"), "<TIME>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b(?::\d+)?"), "<IP>"),
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<HEX>"),
    (re.compile(r'"[^"\n]*"'), "<STR>"),
    (re.compile(r"\b\d+(?:\.\d+)?\b"), "<NUM>"),
]
_WS = re.compile(r"\s+")


def template_of(line):
    """Return the masked template for one log line."""
    text = line.rstrip("\n")
    for pattern, token in MASKS:
        text = pattern.sub(token, text)
    return _WS.sub(" ", text).strip()


def cluster(lines):
    """Group non-blank lines by template.

    Returns an OrderedDict: template -> {"count": int, "examples": [(lineno, text)]}.
    Clusters are ordered by first appearance; use rank() to sort by count.
    """
    groups = OrderedDict()
    for lineno, raw in enumerate(lines, start=1):
        text = raw.rstrip("\n")
        if not text.strip():
            continue
        key = template_of(text)
        entry = groups.setdefault(key, {"count": 0, "examples": []})
        entry["count"] += 1
        entry["examples"].append((lineno, text))
    return groups


def rank(groups, min_count=1, top=None):
    """Sort clusters by count desc, then template asc, and apply filters."""
    items = [(t, g) for t, g in groups.items() if g["count"] >= min_count]
    items.sort(key=lambda kv: (-kv[1]["count"], kv[0]))
    return items[:top] if top is not None else items


def _shorten(text, width):
    return text if len(text) <= width else text[: width - 3] + "..."


def render_table(total, items, examples):
    if total == 0:
        return "no log lines\n"
    out = [f"{total} lines, {len(items)} clusters shown"]
    out.append(f"{'count':>7} {'share':>7}  template")
    for template, g in items:
        share = 100.0 * g["count"] / total
        out.append(f"{g['count']:>7} {share:>6.1f}%  {_shorten(template, 100)}")
        for lineno, text in g["examples"][:examples]:
            out.append(f"{'':>17}L{lineno}: {_shorten(text, 100)}")
    return "\n".join(out) + "\n"


def build_report(groups, items, examples):
    total = sum(g["count"] for g in groups.values())
    return {
        "total_lines": total,
        "clusters": len(groups),
        "shown": len(items),
        "clusters_detail": [
            {
                "template": t,
                "count": g["count"],
                "share": round(100.0 * g["count"] / total, 2) if total else 0.0,
                "examples": [{"line": n, "text": s} for n, s in g["examples"][:examples]],
            }
            for t, g in items
        ],
    }


def read_lines(path):
    if path == "-":
        return sys.stdin.read().splitlines(keepends=True)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.readlines()


def main(argv=None):
    p = argparse.ArgumentParser(prog="log-cluster", description=(__doc__ or "").split("\n")[0])
    p.add_argument("file", help="log file, or - for stdin")
    p.add_argument("--top", type=int, default=20, help="show at most N clusters (default 20)")
    p.add_argument("--min", type=int, default=1, dest="min_count", help="hide clusters smaller than N")
    p.add_argument("--examples", type=int, default=1, help="example lines per cluster (default 1)")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args(argv)
    if args.top < 1 or args.min_count < 1 or args.examples < 0:
        p.error("--top and --min must be >= 1, --examples >= 0")
    try:
        lines = read_lines(args.file)
    except OSError as exc:
        print(f"log-cluster: cannot read {args.file}: {exc.strerror}", file=sys.stderr)
        return 1
    groups = cluster(lines)
    items = rank(groups, args.min_count, args.top)
    if args.json:
        json.dump(build_report(groups, items, args.examples), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        total = sum(g["count"] for g in groups.values())
        sys.stdout.write(render_table(total, items, args.examples))
    return 0


if __name__ == "__main__":
    sys.exit(main())
