#!/usr/bin/env python
"""para-wrap: optimal (minimum-raggedness) paragraph wrapping.

Greedy wrapping (what textwrap and most editors do) packs as many words as
fit on each line. It is fast but can leave one very short line followed by
long ones. The optimal wrapper uses dynamic programming to pick break points
that minimise the total "badness" of the paragraph:

    badness(line) = (width - line_length) ** 2      for every line but the last
    badness(last) = 0                               (a short last line is fine)

Squaring the slack punishes one big gap more than several small ones, so the
right margin comes out even. This is the core idea behind Knuth-Plass (TeX),
without hyphenation or stretchable glue.

DP: best[i] = minimal cost of laying out words[i:]. For each i we try every
j > i such that words[i:j] fit on one line; best[i] = min(cost(i, j) + best[j]).
Since a line holds at most ~width/2 words, this is O(n * width).
"""
import argparse
import json
import sys

__all__ = ["greedy_breaks", "optimal_breaks", "lines_from_breaks",
           "raggedness", "align", "wrap_text"]


def _line_len(lengths, i, j):
    """Length of words[i:j] joined by single spaces."""
    return sum(lengths[i:j]) + (j - i - 1)


def greedy_breaks(words, width):
    """Return break indices (end of each line, exclusive) using first-fit."""
    breaks, cur = [], 0
    for idx, w in enumerate(words):
        if idx == 0:
            cur = len(w)
            continue
        if cur + 1 + len(w) <= width:
            cur += 1 + len(w)
        else:
            breaks.append(idx)
            cur = len(w)
    if words:
        breaks.append(len(words))
    return breaks


def optimal_breaks(words, width):
    """Return break indices minimising the sum of squared trailing slack.

    A word longer than `width` is placed alone on its own line (cost 0 slack
    beyond what it overflows; it cannot be helped).
    """
    n = len(words)
    if n == 0:
        return []
    lengths = [len(w) for w in words]
    INF = float("inf")
    best = [INF] * (n + 1)
    nxt = [n] * (n + 1)
    best[n] = 0
    for i in range(n - 1, -1, -1):
        length = -1
        for j in range(i + 1, n + 1):
            length += lengths[j - 1] + 1
            if length > width and j > i + 1:
                break  # adding more words only makes it longer
            if j == n:
                cost = 0  # last line is free
            else:
                cost = max(0, width - length) ** 2
            total = cost + best[j]
            if total < best[i]:
                best[i], nxt[i] = total, j
            if length > width:
                break  # single overlong word: only option, stop here
    breaks, i = [], 0
    while i < n:
        i = nxt[i]
        breaks.append(i)
    return breaks


def lines_from_breaks(words, breaks):
    lines, start = [], 0
    for end in breaks:
        lines.append(words[start:end])
        start = end
    return lines


def raggedness(lines, width):
    """Sum of squared slack over all lines except the last (lower is better)."""
    total = 0
    for ws in lines[:-1]:
        total += max(0, width - len(" ".join(ws))) ** 2
    return total


def align(ws, width, mode, last=False):
    text = " ".join(ws)
    if mode == "left" or (mode == "justify" and (last or len(ws) == 1)):
        return text
    if mode == "right":
        return text.rjust(width)
    if mode == "center":
        return text.center(width).rstrip()
    # justify: spread extra spaces across gaps, leftmost gaps get one more
    gaps = len(ws) - 1
    spaces = width - sum(len(w) for w in ws)
    if spaces < gaps:
        return text
    base, extra = divmod(spaces, gaps)
    out = []
    for k, w in enumerate(ws[:-1]):
        out.append(w + " " * (base + (1 if k < extra else 0)))
    out.append(ws[-1])
    return "".join(out)


def split_paragraphs(text):
    paras, cur = [], []
    for line in text.splitlines():
        if line.strip():
            cur.extend(line.split())
        elif cur:
            paras.append(cur)
            cur = []
    if cur:
        paras.append(cur)
    return paras


def wrap_text(text, width=72, method="optimal", mode="left"):
    """Wrap every paragraph (blank-line separated) of `text`.

    Returns (wrapped_string, total_raggedness).
    """
    if width < 1:
        raise ValueError("width must be >= 1")
    fn = optimal_breaks if method == "optimal" else greedy_breaks
    blocks, score = [], 0
    for words in split_paragraphs(text):
        lines = lines_from_breaks(words, fn(words, width))
        score += raggedness(lines, width)
        blocks.append("\n".join(
            align(ws, width, mode, last=(k == len(lines) - 1))
            for k, ws in enumerate(lines)))
    return "\n\n".join(blocks), score


def _ruler(width):
    return "-" * width + "|"


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="para_wrap.py",
        description="Optimal (minimum-raggedness) paragraph wrapper.")
    p.add_argument("file", nargs="?", help="input file (default: stdin)")
    p.add_argument("-w", "--width", type=int, default=72)
    p.add_argument("-m", "--method", choices=["optimal", "greedy"],
                   default="optimal")
    p.add_argument("-a", "--align", choices=["left", "right", "center", "justify"],
                   default="left")
    p.add_argument("--compare", action="store_true",
                   help="show greedy vs optimal side by side with scores")
    p.add_argument("--json", action="store_true", help="emit JSON")
    args = p.parse_args(argv)
    if args.width < 1:
        p.error("width must be >= 1")

    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()

    if args.compare:
        g, gs = wrap_text(text, args.width, "greedy", args.align)
        o, os_ = wrap_text(text, args.width, "optimal", args.align)
        if args.json:
            print(json.dumps({"width": args.width,
                              "greedy": {"text": g, "raggedness": gs},
                              "optimal": {"text": o, "raggedness": os_}},
                             indent=2))
            return 0
        for name, body, score in (("greedy", g, gs), ("optimal", o, os_)):
            print(f"== {name} (raggedness {score}) ==")
            print(_ruler(args.width))
            print(body)
            print()
        if gs:
            pct = 100 * (gs - os_) / gs
            print(f"optimal is {pct:.1f}% less ragged")
        return 0

    out, score = wrap_text(text, args.width, args.method, args.align)
    if args.json:
        print(json.dumps({"width": args.width, "method": args.method,
                          "raggedness": score, "text": out}, indent=2))
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
