# semver-tool

A dependency-free [Semantic Versioning 2.0.0](https://semver.org) helper in Python: parse and validate versions, compare and sort them with correct precedence rules, bump them, and check them against npm-style ranges.

## Features

- Strict SemVer 2.0.0 parsing (rejects leading zeros, empty identifiers, etc.), optional `v` prefix
- Correct precedence: `1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0`; build metadata ignored
- Bump `major` / `minor` / `patch` / `prerelease` (with optional `--pre-id` such as `beta`, `rc`)
- npm-style ranges:
  - exact `1.2.3`, comparators `>=1.2.0 <2.0.0`
  - caret `^1.2.3`, `^0.2.3`, `^0.0.3`; tilde `~1.2.3`, `~1`
  - wildcards `*`, `1.x`, `1.2.*`, `>1.2`
  - hyphen ranges `1.2.3 - 2.3.4`; alternatives `^1 || ^3`
  - npm's prerelease rule: a prerelease only matches if a comparator in the same set has the same `major.minor.patch` and its own prerelease tag

## Usage

```
$ python semver.py valid v2.1.0-rc.1+sha.abc
2.1.0-rc.1+sha.abc

$ python semver.py compare 1.0.0 1.0.0-rc.1
1

$ python semver.py sort 1.10.0 1.2.0 1.0.0-beta.11 1.0.0-beta.2 1.0.0
1.0.0-beta.2
1.0.0-beta.11
1.0.0
1.2.0
1.10.0

$ python semver.py bump minor 1.4.7
1.5.0

$ python semver.py bump prerelease 1.4.7 --pre-id beta
1.4.8-beta.0

$ python semver.py bump prerelease 1.5.0-beta.0
1.5.0-beta.1

$ python semver.py satisfies ^1.2.0 1.1.9 1.2.0 1.8.3 2.0.0
1.2.0
1.8.3

$ python semver.py satisfies --max ~1.2.0 1.2.0 1.2.10 1.3.0 1.2.9
1.2.10

$ python semver.py satisfies "1.2.3 - 2.0" 1.2.2 1.5.0 2.0.9 2.1.0
1.5.0
2.0.9

$ python semver.py valid 1.2
error: invalid semver: '1.2'
```

Exit codes: `0` success, `1` no version satisfied the range, `2` invalid input.

### As a library

```python
from semver import Version, Range

Version.parse("1.0.0-rc.1") < Version.parse("1.0.0")          # True
Range("^1.2 || ~3.4").satisfied_by("3.4.9")                    # True
Range(">=1.0.0 <2").max_satisfying(["1.0.0", "1.9.3", "2.0.0"])  # Version('1.9.3')
```

## How ranges work

Every range is desugared into a union (`||`) of comparator sets (ANDed `op version` pairs). For example `^0.2.3` becomes `>=0.2.3 <0.3.0-0`. The `-0` upper bound is the lowest possible prerelease, so `0.3.0-beta` stays out of the range.

## Tests

```
python -m unittest -v
```

20 tests cover parsing, the spec's precedence chain, bumping, every range form, and the CLI.
