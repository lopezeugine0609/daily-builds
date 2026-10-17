# env-check

Lint a dotenv (`.env`) file and compare it with an example template (`.env.example`). It catches config drift before deploy. Node.js only, no npm dependencies.

## What it checks

- **syntax**: line has no `=`, quote not closed, or text after a closing quote
- **invalid-key**: key does not match `[A-Za-z_][A-Za-z0-9_]*`
- **spacing**: whitespace around the key or after `=` (`A = b`)
- **duplicate**: key defined more than once (later value silently wins in most loaders)
- **empty**: key has an empty value (turn off with `--allow-empty`)
- **missing**: key is in the template but not in the env file
- **extra**: key is in the env file but not in the template (turn off with `--allow-extra`)

Parser supports `#` comments, an `export ` prefix, single-quoted literal values, and double-quoted values with escapes (`\n \t \" \\ \$`). Double-quoted values can span several lines, for example PEM keys. It also handles unquoted values with an inline ` # comment`, CRLF line endings and a UTF-8 BOM.

Exit codes: `0` clean, `1` problems found, `2` usage or I/O error. You can use it as a CI gate or pre-commit hook.

## Usage

```
node env-check.js [options] [ENV_FILE]

  -e, --example FILE   template file (default: .env.example if it exists)
  --no-example         skip template comparison
  --allow-empty        do not flag empty values
  --allow-extra        do not flag keys missing from the example
  --json               print problems as JSON
```

`ENV_FILE` defaults to `.env`.

## Examples (real output, using files in `examples/`)

```
$ node env-check.js examples/dev.env -e examples/template.env
examples/dev.env:3: [empty] empty value for "API_KEY"
examples/dev.env:5: [duplicate] duplicate key "PORT" (first defined on line 4)
examples/dev.env:6: [extra] extra key "DEBUG" not in example
examples/template.env:4: [missing] missing key "LOG_LEVEL" (declared in example)
4 problems
$ echo $?
1
```

```
$ node env-check.js examples/dev.env -e examples/template.env --allow-empty --allow-extra --json
[
  {
    "file": "env",
    "line": 5,
    "kind": "duplicate",
    "key": "PORT",
    "message": "duplicate key \"PORT\" (first defined on line 4)"
  },
  {
    "file": "example",
    "line": 4,
    "kind": "missing",
    "key": "LOG_LEVEL",
    "message": "missing key \"LOG_LEVEL\" (declared in example)"
  }
]
```

```
$ node env-check.js examples/prod.env -e examples/template.env
examples/prod.env: OK (matches examples/template.env)
```

## Library use

```js
const { parse, check } = require('./env-check.js');
parse('A="x\\ny"\n').entries;      // [{ key: 'A', value: 'x\ny', line: 1 }]
check(envText, exampleText, { allowEmpty: true });  // [{ file, line, kind, key, message }]
```

## Tests

```
node --test
```

The suite has 9 tests covering parsing, quoting, multi-line values, CRLF/BOM, every problem kind, option flags, and CLI exit codes.
