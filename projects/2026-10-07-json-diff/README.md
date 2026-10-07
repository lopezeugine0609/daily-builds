# json-diff

Structural diff of two JSON documents. Instead of a line diff, it reports
each difference as a JSON path (`$.db.host`, `$.features[1]`) with the old and
new values. Useful for comparing configs, API responses, or fixture files.

- Keys are compared regardless of order (output sorted by key).
- Arrays are compared index by index.
- Type changes (e.g. `8080` vs `"8080"`) are reported as one change, not recursed.
- `--ignore <path>` skips a path and its subtree (repeatable).
- `--epsilon <n>` treats numbers within `n` as equal.
- `--json` emits a machine-readable array of `{op, path, from, to}`.
- Exit code: `0` identical, `1` differences, `2` error (like `diff`).

Node.js standard library only, no npm install.

## Usage

```
node json-diff.js <a.json> <b.json> [--json] [--ignore <path>]... [--epsilon <n>]
```

Use `-` as a filename to read from stdin.

### Example (real output, using `examples/`)

```
$ node json-diff.js examples/old.json examples/new.json
~ $.db.host: "localhost" -> "db.internal"
- $.db.pool: 10
+ $.db.ssl: true
~ $.db.timeout: 2.5 -> 2.5000001
~ $.features[1]: "metrics" -> "tracing"
- $.features[2]: "cache"
~ $.meta.updated: "2026-10-01" -> "2026-10-07"
~ $.port: 8080 -> "8080"
~ $.version: "1.4.0" -> "1.5.0"

1 added, 2 removed, 6 changed
```

Ignore volatile metadata and float noise:

```
$ node json-diff.js examples/old.json examples/new.json --ignore '$.meta' --epsilon 0.001
~ $.db.host: "localhost" -> "db.internal"
- $.db.pool: 10
+ $.db.ssl: true
~ $.features[1]: "metrics" -> "tracing"
- $.features[2]: "cache"
~ $.port: 8080 -> "8080"
~ $.version: "1.4.0" -> "1.5.0"

1 added, 2 removed, 4 changed
```

JSON output:

```
$ node json-diff.js examples/old.json examples/new.json --json --ignore '$.meta' --ignore '$.features' --ignore '$.db'
[
  {
    "op": "change",
    "path": "$.port",
    "from": 8080,
    "to": "8080"
  },
  {
    "op": "change",
    "path": "$.version",
    "from": "1.4.0",
    "to": "1.5.0"
  }
]
```

### As a library

```js
const { diff } = require('./json-diff.js');
diff({ a: 1 }, { a: 2, b: 3 });
// [ { op: 'change', path: '$.a', from: 1, to: 2 }, { op: 'add', path: '$.b', to: 3 } ]
```

## Tests

```
node --test
```

11 tests, all passing.
