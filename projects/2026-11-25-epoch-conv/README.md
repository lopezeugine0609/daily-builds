# epoch-conv

Timestamp converter for developers. Convert Unix epoch values (s / ms / µs / ns), ISO 8601 strings and relative expressions into each other. Print the duration between two times. It stores time internally as BigInt nanoseconds, so ns inputs round-trip with no float loss. Node standard library only.

## Features

- Auto-detects the unit of bare epoch integers by magnitude (`<1e11` s, `<1e14` ms, `<1e17` µs, else ns), or force it with `--unit`.
- Fractional epochs (`1700000000.5`) and negative (pre-1970) times.
- ISO 8601: date-only, `T` or space separator, fractions up to 9 digits, `Z` / `+08:00` / `-0500` offsets. Rejects impossible dates (`2023-02-30`).
- Relative inputs: `now`, `now-1h30m`, `+2d`. Units: `ns us ms s m h d w`.
- `--tz +08:00` adds a local rendering at that offset.
- `--diff A B` prints `B - A` as `59d 12h`.
- `--json` output. Exit codes: `0` ok, `1` parse error, `2` usage error.

## Usage

```
node epoch.js [options] <time> [time ...]
node epoch.js --diff <from> <to>
```

Real output (the `relative` lines depend on when you run it; this run was 2026-11-25):

```
$ node epoch.js --tz +08:00 1700000000 1700000000123456789 2026-11-25T09:00:00+08:00
1700000000
  utc      2023-11-14T22:13:20Z
  local    2023-11-15T06:13:20+08:00
  s        1700000000
  ms       1700000000000
  ns       1700000000000000000
  relative 3 years ago
1700000000123456789
  utc      2023-11-14T22:13:20.123456789Z
  local    2023-11-15T06:13:20.123456789+08:00
  s        1700000000
  ms       1700000000123
  ns       1700000000123456789
  relative 3 years ago
2026-11-25T09:00:00+08:00
  utc      2026-11-25T01:00:00Z
  local    2026-11-25T09:00:00+08:00
  s        1795568400
  ms       1795568400000
  ns       1795568400000000000
  relative 8 hours ago

$ node epoch.js --diff 2026-01-01 2026-03-01T12:00Z
59d 12h  (5140800 s, 5140800000000000 ns)

$ node epoch.js --json --unit ms 0
[
  {
    "input": "0",
    "s": "0",
    "ms": "0",
    "us": "0",
    "ns": "0",
    "utc": "1970-01-01T00:00:00Z",
    "relative": "56 years ago"
  }
]

$ node epoch.js 2023-02-30; echo "exit $?"
error: invalid date: 2023-02-30
exit 1
```

## As a module

```js
const { parseTime, formatIso, convert, diff } = require('./epoch.js');
formatIso(parseTime('1700000000'), 480); // '2023-11-15T06:13:20+08:00'
```

## Tests

```
node --test
```

9 tests: unit detection, fractions, ISO offsets, invalid input, relative input, ISO formatting of negative and sub-second times, durations, diff, and CLI exit codes.
