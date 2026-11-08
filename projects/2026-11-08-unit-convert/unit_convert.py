#!/usr/bin/env python3
"""Exact unit converter with dimensional analysis. Standard library only.

Units are stored as (factor to SI base, dimension exponents). Factors are
Fractions, so conversions are exact. Compound units (km/h, kg*m^2/s^2) are
parsed by multiplying factors and adding dimension exponents. Temperatures
are affine, so they are converted through kelvin instead.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from fractions import Fraction

__all__ = ["UnitError", "UNITS", "TEMP_UNITS", "parse_unit", "parse_quantity",
           "convert", "Result", "main"]


class UnitError(ValueError):
    """Bad quantity, unknown unit, or incompatible dimensions."""


# Dimension tuple = exponents of (length, mass, time).
_LEN, _MASS, _TIME = (1, 0, 0), (0, 1, 0), (0, 0, 1)

UNITS: dict[str, tuple[Fraction, tuple[int, int, int]]] = {
    # length
    "m": (Fraction(1), _LEN),
    "km": (Fraction(1000), _LEN),
    "cm": (Fraction(1, 100), _LEN),
    "mm": (Fraction(1, 1000), _LEN),
    "in": (Fraction(254, 10000), _LEN),
    "ft": (Fraction(3048, 10000), _LEN),
    "yd": (Fraction(9144, 10000), _LEN),
    "mi": (Fraction(1609344, 1000), _LEN),
    "nmi": (Fraction(1852), _LEN),
    # area
    "ha": (Fraction(10000), (2, 0, 0)),
    # volume
    "L": (Fraction(1, 1000), (3, 0, 0)),
    "gal": (Fraction(231) * Fraction(254, 10000) ** 3, (3, 0, 0)),  # US gallon
    # mass
    "kg": (Fraction(1), _MASS),
    "g": (Fraction(1, 1000), _MASS),
    "mg": (Fraction(1, 1000000), _MASS),
    "t": (Fraction(1000), _MASS),
    "lb": (Fraction(45359237, 100000000), _MASS),
    "oz": (Fraction(28349523125, 10**12), _MASS),
    # time
    "s": (Fraction(1), _TIME),
    "ms": (Fraction(1, 1000), _TIME),
    "min": (Fraction(60), _TIME),
    "h": (Fraction(3600), _TIME),
    "d": (Fraction(86400), _TIME),
    "wk": (Fraction(604800), _TIME),
    # derived SI
    "Hz": (Fraction(1), (0, 0, -1)),
    "N": (Fraction(1), (1, 1, -2)),
    "J": (Fraction(1), (2, 1, -2)),
    "W": (Fraction(1), (2, 1, -3)),
    "Pa": (Fraction(1), (-1, 1, -2)),
}

TEMP_UNITS = ("C", "F", "K")

_TOKEN = re.compile(r"\*|/|\^|[A-Za-zµ]+|-?\d+|\S")
_NAME = re.compile(r"[A-Za-zµ]+")
_INT = re.compile(r"-?\d+")
_QTY = re.compile(r"\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*(.+?)\s*")


def parse_unit(expr: str) -> tuple[Fraction, tuple[int, int, int]]:
    """Return (factor to SI, dimensions) for expressions like 'km/h' or 'kg*m^2/s^2'."""
    toks = _TOKEN.findall(expr)
    if not toks:
        raise UnitError("empty unit")
    factor = Fraction(1)
    dims = [0, 0, 0]
    i, sign = 0, 1
    if toks[0] == "/":  # leading '/' means reciprocal, e.g. '/s'
        sign, i = -1, 1
    while True:
        if i >= len(toks) or not _NAME.fullmatch(toks[i]):
            raise UnitError(f"expected unit name in {expr!r}")
        name = toks[i]
        if name not in UNITS:
            raise UnitError(f"unknown unit {name!r}")
        i += 1
        exp = 1
        if i < len(toks) and toks[i] == "^":
            if i + 1 >= len(toks) or not _INT.fullmatch(toks[i + 1]):
                raise UnitError(f"bad exponent in {expr!r}")
            exp = int(toks[i + 1])
            i += 2
        f, d = UNITS[name]
        factor *= f ** (sign * exp)
        for k in range(3):
            dims[k] += sign * exp * d[k]
        if i >= len(toks):
            break
        if toks[i] not in ("*", "/"):
            raise UnitError(f"expected '*' or '/' in {expr!r}")
        sign = 1 if toks[i] == "*" else -1
        i += 1
    return factor, tuple(dims)


def parse_quantity(text: str) -> tuple[Fraction, str]:
    """Split '5 km/h' into (Fraction(5), 'km/h'). Decimals and exponents are exact."""
    m = _QTY.fullmatch(text)
    if not m:
        raise UnitError(f'expected "<number> <unit>", got {text!r}')
    return Fraction(m.group(1)), m.group(2)


def _to_kelvin(v: Fraction, u: str) -> Fraction:
    if u == "C":
        return v + Fraction(27315, 100)
    if u == "F":
        return (v + Fraction(45967, 100)) * Fraction(5, 9)
    return v


def _from_kelvin(k: Fraction, u: str) -> Fraction:
    if u == "C":
        return k - Fraction(27315, 100)
    if u == "F":
        return k * Fraction(9, 5) - Fraction(45967, 100)
    return k


@dataclass(frozen=True)
class Result:
    value: Fraction
    from_unit: str
    result: Fraction
    to_unit: str


def convert(quantity: str, to_unit: str) -> Result:
    value, from_unit = parse_quantity(quantity)
    to_unit = to_unit.strip()
    if from_unit in TEMP_UNITS or to_unit in TEMP_UNITS:
        if from_unit not in TEMP_UNITS or to_unit not in TEMP_UNITS:
            raise UnitError("temperatures convert only to temperatures")
        return Result(value, from_unit, _from_kelvin(_to_kelvin(value, from_unit), to_unit), to_unit)
    f1, d1 = parse_unit(from_unit)
    f2, d2 = parse_unit(to_unit)
    if d1 != d2:
        raise UnitError(f"incompatible units: {from_unit!r} and {to_unit!r}")
    return Result(value, from_unit, value * f1 / f2, to_unit)


def _fmt(x: Fraction, exact: bool) -> str:
    if exact:
        return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"
    return f"{float(x):.12g}"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="unit-convert",
        description="Exact unit conversion with dimensional checks. Example: unit-convert '5 km/h' m/s",
    )
    p.add_argument("quantity", nargs="?", help='quantity with unit, e.g. "5 km/h"')
    p.add_argument("to", nargs="?", help="target unit, e.g. m/s")
    p.add_argument("--exact", action="store_true", help="print exact fraction instead of decimal")
    p.add_argument("--json", action="store_true", help="print JSON")
    p.add_argument("--list", action="store_true", help="list known units and exit")
    a = p.parse_args(argv)

    if a.list:
        print("length/area/volume/mass/time/derived:", " ".join(sorted(UNITS)))
        print("temperature:", " ".join(TEMP_UNITS))
        return 0
    if a.quantity is None or a.to is None:
        p.error("need a quantity and a target unit (or --list)")
    try:
        r = convert(a.quantity, a.to)
    except UnitError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if a.json:
        out = {
            "value": str(r.value),
            "from": r.from_unit,
            "to": r.to_unit,
            "result": float(r.result),
            "exact": _fmt(r.result, True),
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"{_fmt(r.value, a.exact)} {r.from_unit} = {_fmt(r.result, a.exact)} {r.to_unit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
