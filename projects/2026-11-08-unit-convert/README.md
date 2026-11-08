# unit-convert

Exact unit converter with dimensional analysis. Standard library only (Python 3).

- Conversions use `fractions.Fraction`, so factors like 1 mi = 5280 ft or 1 gal = 3.785411784 L are exact.
- Compound units: `km/h`, `kg*m/s^2`, `N/m^2`, `m^3`, leading `/s`.
- Dimensional check: `km` to `kg` fails. `km/h` to `m` fails. Equivalent compounds pass (`1 J` = `1 N*m`).
- Temperatures (`C`, `F`, `K`) are affine. They convert through kelvin and only to each other.
- `--exact` prints the fraction, `--json` prints machine output, exit code 1 on error, 2 on bad usage.

## Usage

```
$ python unit_convert.py '5 km/h' m/s
5 km/h = 1.38888888889 m/s

$ python unit_convert.py --exact '5 km/h' m/s
5 km/h = 25/18 m/s

$ python unit_convert.py '100 C' F
100 C = 212 F

$ python unit_convert.py --json '1 mi' ft
{
  "value": "1",
  "from": "mi",
  "to": "ft",
  "result": 5280.0,
  "exact": "5280"
}

$ python unit_convert.py '1 gal' L --exact
1 gal = 473176473/125000000 L

$ python unit_convert.py '1 kg*m/s^2' N
1 kg*m/s^2 = 1 N

$ python unit_convert.py '60 mi/h' km/h
60 mi/h = 96.56064 km/h

$ python unit_convert.py '1 km' kg
error: incompatible units: 'km' and 'kg'
[exit 1]
```

Run `python unit_convert.py --list` to see all units.

## Tests

```
$ python -m unittest
```

Runs 26 tests covering unit parsing, exact factors, compound and derived units, temperatures, error cases, and CLI output and exit codes.

Files:
- `unit_convert.py`: converter and CLI
- `test_unit_convert.py`: unittest suite
