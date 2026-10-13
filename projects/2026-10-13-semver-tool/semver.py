#!/usr/bin/env python
"""semver.py - parse, compare, bump, and range-match Semantic Versions (SemVer 2.0.0).

Supports npm-style ranges: exact (1.2.3), comparators (>=1.2.0 <2.0.0),
caret (^1.2.3), tilde (~1.2.3), wildcards (1.x, 1.2.*, *), hyphen ranges
(1.2.3 - 2.3.4) and alternatives joined by ||.

Standard library only.
"""
import argparse
import re
import sys
from functools import total_ordering

_SEMVER_RE = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


@total_ordering
class Version:
    """An immutable SemVer 2.0.0 version. Build metadata is ignored for ordering."""

    __slots__ = ("major", "minor", "patch", "prerelease", "build")

    def __init__(self, major, minor, patch, prerelease=(), build=()):
        self.major, self.minor, self.patch = int(major), int(minor), int(patch)
        self.prerelease = tuple(prerelease)
        self.build = tuple(build)

    @classmethod
    def parse(cls, text):
        m = _SEMVER_RE.match(text.strip())
        if not m:
            raise ValueError(f"invalid semver: {text!r}")
        pre = tuple(m.group(4).split(".")) if m.group(4) else ()
        build = tuple(m.group(5).split(".")) if m.group(5) else ()
        return cls(m.group(1), m.group(2), m.group(3), pre, build)

    def __str__(self):
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            s += "-" + ".".join(self.prerelease)
        if self.build:
            s += "+" + ".".join(self.build)
        return s

    def __repr__(self):
        return f"Version({str(self)!r})"

    def _key(self):
        # A version without prerelease ranks higher than one with it.
        if not self.prerelease:
            pre = (1,)
        else:
            parts = []
            for ident in self.prerelease:
                # Numeric identifiers sort before alphanumeric ones.
                parts.append((0, int(ident), "") if ident.isdigit() else (1, 0, ident))
            pre = (0, tuple(parts))
        return (self.major, self.minor, self.patch, pre)

    def __eq__(self, other):
        return isinstance(other, Version) and self._key() == other._key()

    def __lt__(self, other):
        return self._key() < other._key()

    def __hash__(self):
        return hash(self._key())

    def bump(self, part, pre_id=None):
        """Return a new version bumped by part: major, minor, patch, or prerelease."""
        if part == "major":
            return Version(self.major + 1, 0, 0)
        if part == "minor":
            return Version(self.major, self.minor + 1, 0)
        if part == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        if part == "prerelease":
            if not self.prerelease:
                return Version(self.major, self.minor, self.patch + 1, (pre_id or "0",) + (("0",) if pre_id else ()))
            pre = list(self.prerelease)
            if pre_id and pre[0] != pre_id:
                return Version(self.major, self.minor, self.patch, (pre_id, "0"))
            if pre[-1].isdigit():
                pre[-1] = str(int(pre[-1]) + 1)
            else:
                pre.append("0")
            return Version(self.major, self.minor, self.patch, pre)
        raise ValueError(f"unknown bump part: {part!r}")


# ---------------------------------------------------------------- ranges

_PARTIAL_RE = re.compile(
    r"^v?(\*|x|X|0|[1-9]\d*)(?:\.(\*|x|X|0|[1-9]\d*)(?:\.(\*|x|X|0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?)?)?$"
)
_OPS = ("<=", ">=", "<", ">", "=")


def _partial(text):
    """Parse '1', '1.2', '1.x', '*', '1.2.3-beta' -> (major, minor, patch, pre); None = wildcard."""
    m = _PARTIAL_RE.match(text)
    if not m:
        raise ValueError(f"invalid version in range: {text!r}")
    nums = [None if g is None or g in "*xX" else int(g) for g in m.group(1, 2, 3)]
    # Anything after a wildcard is a wildcard too.
    for i in range(1, 3):
        if nums[i - 1] is None:
            nums[i] = None
    pre = tuple(m.group(4).split(".")) if m.group(4) else ()
    return nums[0], nums[1], nums[2], pre


def _desugar(token):
    """Turn one range token into a list of (op, Version) comparators."""
    op = next((o for o in _OPS if token.startswith(o)), "")
    body = token[len(op):]
    if body.startswith("^"):
        return _caret(*_partial(body[1:]))
    if body.startswith("~"):
        return _tilde(*_partial(body[1:].lstrip(">")))
    M, m, p, pre = _partial(body)
    if M is None:
        return [] if op in ("", "=", ">=", "<=") else [("<", Version(0, 0, 0, ("0",)))]
    if m is None or p is None:
        lo = Version(M, m or 0, 0)
        hi = Version(M + 1, 0, 0, ("0",)) if m is None else Version(M, m + 1, 0, ("0",))
        return {"": [(">=", lo), ("<", hi)], "=": [(">=", lo), ("<", hi)],
                ">=": [(">=", lo)], ">": [(">=", hi)],
                "<": [("<", lo)], "<=": [("<", hi)]}[op]
    return [(op or "=", Version(M, m, p, pre))]


def _caret(M, m, p, pre):
    if M is None:
        return []
    lo = Version(M, m or 0, p or 0, pre)
    if M > 0 or m is None:
        hi = Version(M + 1, 0, 0, ("0",))
    elif m > 0 or p is None:
        hi = Version(0, m + 1, 0, ("0",))
    else:
        hi = Version(0, 0, p + 1, ("0",))
    return [(">=", lo), ("<", hi)]


def _tilde(M, m, p, pre):
    if M is None:
        return []
    lo = Version(M, m or 0, p or 0, pre)
    hi = Version(M + 1, 0, 0, ("0",)) if m is None else Version(M, m + 1, 0, ("0",))
    return [(">=", lo), ("<", hi)]


def _hyphen(a, b):
    M, m, p, pre = _partial(a)
    lo = Version(M or 0, m or 0, p or 0, pre)
    M2, m2, p2, pre2 = _partial(b)
    if M2 is None:
        return [(">=", lo)]
    if m2 is None:
        return [(">=", lo), ("<", Version(M2 + 1, 0, 0, ("0",)))]
    if p2 is None:
        return [(">=", lo), ("<", Version(M2, m2 + 1, 0, ("0",)))]
    return [(">=", lo), ("<=", Version(M2, m2, p2, pre2))]


def _cmp(v, op, ref):
    return {"=": v == ref, "<": v < ref, "<=": v <= ref, ">": v > ref, ">=": v >= ref}[op]


class Range:
    """An npm-style version range: a union (||) of comparator sets."""

    def __init__(self, text):
        self.text = text
        self.sets = []
        for alt in text.split("||"):
            alt = re.sub(r"(<=|>=|<|>|=|\^|~)\s+", r"\1", alt.strip())
            tokens = alt.split()
            if len(tokens) == 3 and tokens[1] == "-":
                self.sets.append(_hyphen(tokens[0], tokens[2]))
                continue
            comps = []
            for tok in tokens:
                comps.extend(_desugar(tok))
            self.sets.append(comps)

    def satisfied_by(self, version):
        v = version if isinstance(version, Version) else Version.parse(version)
        for comps in self.sets:
            if not all(_cmp(v, op, ref) for op, ref in comps):
                continue
            # Prereleases match only if some comparator shares their [M, m, p] tuple.
            if v.prerelease and not any(
                ref.prerelease and (ref.major, ref.minor, ref.patch) == (v.major, v.minor, v.patch)
                for _, ref in comps
            ):
                continue
            return True
        return False

    def max_satisfying(self, versions):
        ok = [Version.parse(x) if isinstance(x, str) else x for x in versions]
        ok = [v for v in ok if self.satisfied_by(v)]
        return max(ok) if ok else None


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(prog="semver", description="SemVer 2.0.0 helper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("valid", help="print normalized version or fail")
    p.add_argument("version")
    p = sub.add_parser("compare", help="print -1, 0 or 1")
    p.add_argument("a")
    p.add_argument("b")
    p = sub.add_parser("sort", help="sort versions ascending")
    p.add_argument("versions", nargs="+")
    p.add_argument("-r", "--reverse", action="store_true")
    p = sub.add_parser("bump", help="bump major|minor|patch|prerelease")
    p.add_argument("part", choices=["major", "minor", "patch", "prerelease"])
    p.add_argument("version")
    p.add_argument("--pre-id", help="prerelease identifier, e.g. beta")
    p = sub.add_parser("satisfies", help="filter versions matching a range")
    p.add_argument("range")
    p.add_argument("versions", nargs="+")
    p.add_argument("--max", action="store_true", help="print only the highest match")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "valid":
            print(Version.parse(args.version))
        elif args.cmd == "compare":
            a, b = Version.parse(args.a), Version.parse(args.b)
            print((a > b) - (a < b))
        elif args.cmd == "sort":
            for v in sorted((Version.parse(x) for x in args.versions), reverse=args.reverse):
                print(v)
        elif args.cmd == "bump":
            print(Version.parse(args.version).bump(args.part, args.pre_id))
        elif args.cmd == "satisfies":
            r = Range(args.range)
            vs = [Version.parse(x) for x in args.versions]
            if args.max:
                best = r.max_satisfying(vs)
                if best is None:
                    return 1
                print(best)
            else:
                hits = [v for v in vs if r.satisfied_by(v)]
                for v in hits:
                    print(v)
                if not hits:
                    return 1
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
