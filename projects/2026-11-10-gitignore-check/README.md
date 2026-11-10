# gitignore-check

Offline `.gitignore` evaluator in plain Node.js (no dependencies). Answers "would git ignore this path?" and says which rule decided it. Also lists the topmost ignored entries in a repo, without touching git.

## How it works

- Rules are parsed line by line: comments, blanks, `\#`/`\!` escapes, trailing-space trimming (unless escaped), CRLF and BOM.
- A pattern with no `/` (apart from a trailing one) matches the basename at any depth. A pattern with a middle `/` is anchored to the root. `/x` is always anchored.
- `*` and `?` never cross `/`. `**/` matches any depth, `/**` matches contents, `a/**/b` matches zero or more directories.
- `dir/` patterns only match directories.
- **Last matching rule wins**, so `!` negations work when they come later.
- Git's parent rule: a file inside an ignored directory stays ignored. A later `!` cannot re-include it. Every ancestor is checked first.

## Usage

```
usage: gitignore-check.js [--root DIR] [--file F] [--json] (--walk | PATH...)
  PATH...   check each path (relative to --root); trailing / or an existing dir = directory
            exit 0 = all kept, 1 = at least one ignored, 2 = usage/IO error
  --walk    list topmost ignored entries under root (never descends into them, skips .git)
            exit 0 on success
  --file F  ignore file, relative to root (default: .gitignore)
  --json    machine-readable output
```

Example repo:

```
$ cat .gitignore
# deps
node_modules/
*.log
!keep.log
/build
```

Check paths:

```
$ node gitignore-check.js src/app.js debug.log keep.log src/build/out.js
kept     src/app.js
IGNORED  debug.log  (.gitignore:3 '*.log')
kept     keep.log  (.gitignore:4 '!keep.log')
kept     src/build/out.js
$ echo $?
1
```

Walk the whole tree (topmost ignored entries only):

```
$ node gitignore-check.js --walk
IGNORED  debug.log  (.gitignore:3 '*.log')
IGNORED  node_modules/  (.gitignore:2 'node_modules/')
```

JSON:

```
$ node gitignore-check.js --json --root . debug.log
[
  {
    "path": "debug.log",
    "ignored": true,
    "via": null,
    "rule": {
      "source": ".gitignore",
      "line": 3,
      "pattern": "*.log"
    }
  }
]
```

Exit codes: `0` all kept (or `--walk` succeeded), `1` at least one path ignored, `2` usage or IO error (bad option, missing file, path outside `--root`).

## Tests

Uses `node:test`. Covers parsing, escapes, anchoring, `**`, dir-only rules, negation order, the parent-directory rule, character classes, the walker (on a temp tree), and CLI exit codes and JSON shape.

```
$ node --test
ℹ tests 18
ℹ suites 0
ℹ pass 18
ℹ fail 0
```

Run with `node --test` from this folder.

## Limits

- Matches what git does for the common syntax. It does not read global excludes (`core.excludesFile`) or `.git/info/exclude`.
- `--walk` does not descend into ignored directories, so an ignored directory is reported once.
- The `--file` flag reads one ignore file. Nested `.gitignore` files are not merged.
